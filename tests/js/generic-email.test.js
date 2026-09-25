const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const {JSDOM} = require('jsdom');

function setup(body, html = true, url = 'http://localhost/') {
    const dom = new JSDOM(`<form><input name="csrfmiddlewaretoken" value="test-csrf"><input type="checkbox" id="id_is_html" ${html ? 'checked' : ''}><textarea id="id_body_text" name="body_text" data-richtext="1" data-html-toggle="#id_is_html" data-upload-url="/editor/upload/" data-browse-url="/editor/browse/"></textarea></form>`, {runScripts: 'outside-only', pretendToBeVisual: true, url});
    const {window} = dom;
    window.focus = () => {};
    window.matchMedia = () => ({matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}});
    window.ResizeObserver = class {observe() {} unobserve() {} disconnect() {}};
    const textarea = window.document.getElementById('id_body_text');
    textarea.value = body;
    window.eval(fs.readFileSync('sportfac/backend/static/backend/vendor/jodit/jodit.min.js', 'utf8'));
    window.eval(fs.readFileSync('sportfac/backend/static/backend/js/generic-email.js', 'utf8'));
    return {dom, window, textarea, checkbox: window.document.getElementById('id_is_html')};
}

test('real editor displays Django variables and preserves them on submit and HTML toggle', async () => {
    const body = fs.readFileSync('sportfac/mailer/templates/mailer/defaults/montreux_practical_reminder.html', 'utf8');
    const {dom, window, textarea, checkbox} = setup(body);
    try {
        await new Promise(resolve => setTimeout(resolve, 100));
        const editable = window.document.querySelector('.jodit-wysiwyg');
        assert.ok(editable);
        for (const variable of body.match(/{{[\s\S]*?}}/g).filter(value => value !== '{{ logo_url }}')) {
            assert.ok(editable.textContent.includes(variable), `Visible variable: ${variable}`);
        }
        textarea.form.dispatchEvent(new window.Event('submit', {cancelable: true}));
        for (const variable of body.match(/{{[\s\S]*?}}/g)) assert.ok(textarea.value.includes(variable), variable);
        assert.ok(textarea.value.includes('<table'));
        checkbox.checked = false;
        checkbox.dispatchEvent(new window.Event('change'));
        assert.equal(window.document.querySelector('.jodit-wysiwyg'), null);
        assert.ok(textarea.value.includes('{{ child.first_name }}'));
        checkbox.checked = true;
        checkbox.dispatchEvent(new window.Event('change'));
        assert.ok(window.document.querySelector('.jodit-wysiwyg').textContent.includes('{{ child.first_name }}'));
    } finally { dom.window.close(); }
});

test('real uploader posts an image with CSRF and accepts the connector response', async () => {
    let received;
    const server = http.createServer((request, response) => {
        const chunks = [];
        request.on('data', chunk => chunks.push(chunk));
        request.on('end', () => {
            received = {method: request.method, url: request.url, headers: request.headers, body: Buffer.concat(chunks).toString()};
            response.setHeader('Content-Type', 'application/json');
            response.end(JSON.stringify({success: true, data: {files: ['http://localhost/media/uploads/image.png'], baseurl: '', isImages: [true]}}));
        });
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const {dom, window} = setup('<p>Image</p>', true, `http://127.0.0.1:${server.address().port}/`);
    try {
        const editor = window.Jodit.instances.id_body_text;
        const data = await editor.uploader.upload([new window.File(['image-data'], 'image.png', {type: 'image/png'})]);
        assert.equal(received.method, 'POST');
        assert.equal(received.url, '/editor/upload/');
        assert.equal(received.headers['x-csrftoken'], 'test-csrf');
        assert.ok(received.body.includes('filename="image.png"'));
        editor.o.uploader.defaultHandlerSuccess.call(editor.uploader, data);
        assert.ok(editor.value.includes('src="http://localhost/media/uploads/image.png"'));
    } finally {
        dom.window.close();
        await new Promise(resolve => server.close(resolve));
    }
});

test('plain mail is left untouched until HTML is explicitly enabled', () => {
    const {dom, window, textarea} = setup('Bonjour {{ child.first_name }}\n<texte>', false);
    assert.equal(window.document.querySelector('.jodit-wysiwyg'), null);
    textarea.form.dispatchEvent(new window.Event('submit', {cancelable: true}));
    assert.equal(textarea.value, 'Bonjour {{ child.first_name }}\n<texte>');
    dom.window.close();
});

test('submitting immediately from Source keeps the last edit and template variables', () => {
    const {dom, window, textarea} = setup('<p>{{ child.first_name }}</p>');
    try {
        const editor = window.Jodit.instances.id_body_text;
        editor.setMode(window.Jodit.MODE_SOURCE);
        const source = window.document.querySelector('.jodit-source__mirror');
        source.value = '<p>Dernière modification {{ child.last_name }}</p>';
        source.dispatchEvent(new window.Event('input', {bubbles: true}));
        textarea.form.dispatchEvent(new window.Event('submit', {cancelable: true}));
        assert.ok(textarea.value.includes('Dernière modification {{ child.last_name }}'));
    } finally { dom.window.close(); }
});
