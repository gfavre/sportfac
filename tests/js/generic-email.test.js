const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

function setup(body, html = true) {
    const dom = new JSDOM(`<form><input type="checkbox" id="id_is_html" ${html ? 'checked' : ''}><textarea id="id_body_text"></textarea></form>`, {runScripts: 'outside-only', pretendToBeVisual: true, url: 'http://localhost/'});
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
