const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

const template = fs.readFileSync('sportfac/backend/templates/backend/registration/generate-bibs.html', 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/{% translate "([^"]*)" %}/g, '$1');
const url = '/backend/registrations/transport/generate-bibs/';
function row(id, car = '') {
    return `<tr data-child="${id}" data-cars="${car || 'none'}" data-pending="${car ? '' : 'pending'}">
      <td><input class="select-child" type="checkbox"></td><td>Enfant ${String(id).padStart(3, '0')}</td><td>
      <select class="bib-transport" name="child_${id}"><option value=""></option><option value="3" ${car ? 'selected' : ''}>3</option></select>
      <small class="assignment-status" role="status"></small></td><td></td><td></td></tr>`;
}
function markup(rows = row(1)) {
    return `<div id="bib-summary">0 / 1</div>
      <select id="filter-car"><option value=""></option><option value="none">Sans car</option><option value="3">3</option></select>
      <select id="filter-state"><option value="all">Tous</option><option value="pending">À compléter</option></select>
      <form id="assign-bib-transports" action="${url}">
        <input name="action" value="assign"><input name="csrfmiddlewaretoken" value="token">
        <select id="bulk-transport"><option value=""></option><option value="3">3</option></select>
        <table id="bib-children"><thead><tr><th><input id="select-all-children" type="checkbox"></th>
        <th>Enfant</th><th>Car</th><th>État</th><th>Inscriptions</th></tr></thead><tbody>${rows}</tbody></table>
      </form><button id="generate-bibs" disabled></button>`;
}
function setup(rows, query = '') {
    const dom = new JSDOM(markup(rows), {url: `http://localhost${url}${query}`, runScripts: 'outside-only'});
    for (const file of [
        'sportfac/static/js/vendor/jquery-2.1.1.js',
        'sportfac/static/js/vendor/DataTables-2020/DataTables-1.10.24/js/jquery.dataTables.min.js',
        'sportfac/backend/static/backend/js/datatable-url-state.js',
    ]) dom.window.eval(fs.readFileSync(file, 'utf8'));
    return dom;
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test('autosave uses the URL attribute and shows a temporary green status in the changed row', async () => {
    assert.match(template, /action="{% url 'backend:transport-generate-bibs' %}"/);
    const dom = setup(undefined, '?state=all');
    const {window} = dom;
    const timers = [];
    window.setTimeout = (callback, delay) => { timers.push({callback, delay}); return timers.length; };
    const form = window.document.querySelector('form');
    Object.defineProperty(form, 'action', {value: form.querySelector('[name=action]')});
    let calls = 0;
    window.fetch = async (target, options) => {
        calls++;
        assert.equal(target, url);
        assert.equal(options.body.get('action'), 'assign');
        assert.equal(options.body.get('child_1'), '3');
        assert.equal(options.body.get('csrfmiddlewaretoken'), 'token');
        return {ok: true, headers: {get: () => 'true'}, text: async () => markup(row(1, '3')).replace('0 / 1', '1 / 1')};
    };
    window.eval(script);
    const select = form.querySelector('.bib-transport');
    select.value = '3';
    select.dispatchEvent(new window.Event('change', {bubbles: true}));
    await settle();
    assert.equal(calls, 1);
    const status = form.querySelector('.bib-transport').closest('td').querySelector('.assignment-status');
    assert.equal(status.textContent, '✓ Enregistré');
    assert.ok(status.classList.contains('text-success'));
    timers.find(timer => timer.delay === 3000).callback();
    assert.equal(status.textContent, '');
    assert.equal(window.document.getElementById('bib-summary').textContent, '1 / 1');
    dom.window.close();
});

test('400 children: autosave preserves page and search; bulk selection covers only the visible page', async () => {
    const dom = setup(Array.from({length: 400}, (_, i) => row(i + 1)).join(''), '?q=Enfant&page=2&state=all');
    const {window} = dom;
    const requests = [];
    window.fetch = async (target, options) => {
        const names = [...options.body.keys()].filter(name => name.startsWith('child_'));
        requests.push(names);
        return {ok: true, headers: {get: () => 'true'}, text: async () => markup(names.map(name => row(Number(name.slice(6)), '3')).join(''))};
    };
    window.eval(script);
    const table = window.$('#bib-children').DataTable();
    assert.equal(table.page.info().pages, 8);
    assert.equal(table.page(), 1);
    const select = window.document.querySelector('.bib-transport');
    assert.equal(select.name, 'child_51');
    select.value = '3';
    select.dispatchEvent(new window.Event('change', {bubbles: true}));
    await settle();
    assert.equal(table.page(), 1);
    assert.equal(table.search(), 'Enfant');
    assert.equal(table.rows().count(), 400);
    const all = window.document.getElementById('select-all-children');
    all.checked = true;
    all.dispatchEvent(new window.Event('change', {bubbles: true}));
    const bulk = window.document.getElementById('bulk-transport');
    bulk.value = '3';
    bulk.dispatchEvent(new window.Event('change', {bubbles: true}));
    await settle();
    assert.equal(requests[1].length, 50);
    assert.deepEqual(requests[1], Array.from({length: 50}, (_, i) => `child_${i + 51}`));
    const filter = window.document.getElementById('filter-car');
    filter.value = 'none';
    window.$(filter).trigger('change');
    assert.equal(table.rows({search: 'applied'}).count(), 350);
    assert.equal(window.document.querySelectorAll('.select-child:checked').length, 0);
    assert.equal(new URL(window.location.href).searchParams.get('car'), 'none');
    dom.window.close();
});

test('default view shows only children needing action, with an explicit all-children option', async () => {
    const dom = setup(row(1) + row(2, '3'));
    const {window} = dom;
    window.fetch = async () => ({ok: true, headers: {get: () => 'true'}, text: async () => markup(row(1, '3'))});
    window.eval(script);
    const table = window.$('#bib-children').DataTable();
    const filter = window.document.getElementById('filter-state');
    assert.equal(filter.value, 'pending');
    assert.equal(table.rows({search: 'applied'}).count(), 1);
    const select = window.document.querySelector('.bib-transport');
    assert.equal(select.name, 'child_1');
    select.value = '3';
    select.dispatchEvent(new window.Event('change', {bubbles: true}));
    await settle();
    assert.equal(table.rows({search: 'applied'}).count(), 0);
    filter.value = 'all';
    window.$(filter).trigger('change');
    assert.equal(table.rows({search: 'applied'}).count(), 2);
    assert.equal(new URL(window.location.href).searchParams.get('state'), 'all');
    dom.window.close();
});
