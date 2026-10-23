const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');
const script = fs.readFileSync('sportfac/backend/static/backend/js/transport-assignments.js', 'utf8');
function setup(query = '') {
    const rows = Array.from({length: 120}, (_, index) => {
        const stop = index < 80 ? '73 Chailly' : '74 Clarens';
        return `<tr data-child-id="${index + 1}" data-pending="${index >= 40}" data-stops='["${stop}"]' data-cars='["${index < 40 ? '7' : 'none'}"]'>
          <td>Enfant ${String(index + 1).padStart(3, '0')}</td><td>${stop}</td><td>Car</td></tr>`;
    }).join('');
    const dom = new JSDOM(`<form id="question-form"><select name="question" id="question"><option value="1">Arrêt</option><option value="2">Départ</option></select></form>
      <script type="application/json" id="served-stops">["73 Chailly"]</script>
      <form id="transport-assignments" data-current-car="7"><div id="assignment-toolbar"><span id="selection-count"></span><div id="assignment-action-controls"></div></div>
        <button type="button" id="select-filtered"></button><button type="button" id="clear-selection"></button>
        <select name="destination" id="id_destination"><option value="">Choisir</option><option value="7">Car 7</option></select>
        <button type="submit" id="assign-selected"></button>
        <table id="assignment-children"><thead><tr><th>Enfant</th><th>Arrêt</th><th>Car</th></tr>
        <tr><th></th><th><select id="stop"><option value="">Tous</option><option value="73 Chailly">Chailly</option><option value="74 Clarens">Clarens</option><option value="__missing__">Sans réponse</option><option value="__served__">Desservis</option></select></th>
        <th><select id="car"><option value="all">Tous</option><option value="pending">À compléter</option><option value="none">Sans car</option><option value="current">Ce car</option><option value="7">7</option></select></th></tr></thead>
        <tbody>${rows}</tbody></table></form>`, {url: 'http://localhost/backend/transport/assignments/' + query, runScripts: 'outside-only'});
    for (const file of [
        'sportfac/static/js/vendor/jquery-2.1.1.js',
        'sportfac/static/js/vendor/DataTables-2020/DataTables-1.10.24/js/jquery.dataTables.min.js',
        'sportfac/static/js/vendor/DataTables-2020/Select-1.3.2/js/dataTables.select.min.js',
    ]) dom.window.eval(fs.readFileSync(file, 'utf8'));
    dom.window.eval(script);
    return dom.window;
}
function change(window, id, value) {
    const input = window.document.getElementById(id);
    input.value = value;
    input.dispatchEvent(new window.Event('change', {bubbles: true}));
}
function submit(window) {
    const form = window.document.getElementById('transport-assignments');
    form.dispatchEvent(new window.Event('submit', {cancelable: true}));
    return new window.FormData(form);
}

test('DataTables filters immediately and bulk assignment spans every filtered page', () => {
    const window = setup();
    const document = window.document;
    const table = window.$('#assignment-children').DataTable();
    assert.equal(table.page.info().pages, 3);
    assert.equal(document.getElementById('assign-selected').disabled, true);
    assert.equal(document.getElementById('assignment-action-controls').hidden, true);
    change(window, 'stop', '73 Chailly');
    assert.equal(table.rows({search: 'applied'}).count(), 80);
    document.getElementById('select-filtered').click();
    change(window, 'id_destination', '7');
    assert.equal(document.getElementById('selection-count').textContent, '80 sélectionné(s)');
    assert.equal(document.getElementById('assign-selected').disabled, false);
    assert.equal(document.getElementById('assignment-action-controls').hidden, false);
    assert.equal(document.getElementById('assignment-toolbar').classList.contains('has-selection'), true);
    table.page('next').draw('page');
    const data = submit(window);
    assert.equal(data.getAll('children').length, 80);
    assert.equal(new Set(data.getAll('children')).size, 80);
    assert.equal(data.get('destination'), '7');
    assert.match(document.querySelector('#transport-assignments').action, /stop=73\+Chailly/);
    window.close();
});

test('car filter and search narrow selection and remove hidden selected children', () => {
    const window = setup();
    const document = window.document;
    const table = window.$('#assignment-children').DataTable();
    document.getElementById('select-filtered').click();
    change(window, 'car', 'none');
    assert.equal(document.getElementById('selection-count').textContent, '80 sélectionné(s)');
    table.search('Enfant 120').draw();
    assert.equal(document.getElementById('selection-count').textContent, '1 sélectionné(s)');
    assert.equal(new URL(window.location.href).searchParams.get('q'), 'Enfant 120');
    assert.deepEqual(submit(window).getAll('children'), ['120']);
    window.close();
});

test('bulk controls select all filtered pages and clear resets state', () => {
    const window = setup();
    const document = window.document;
    const all = document.getElementById('select-filtered');
    all.click();
    assert.equal(document.getElementById('selection-count').textContent, '120 sélectionné(s)');
    document.getElementById('clear-selection').click();
    assert.equal(document.getElementById('selection-count').textContent, 'Sélectionnez les enfants à affecter');
    document.getElementById('select-filtered').click();
    document.getElementById('clear-selection').click();
    assert.equal(document.getElementById('assign-selected').disabled, true);
    assert.equal(document.getElementById('clear-selection').disabled, true);
    window.close();
});

test('served stops and current car combine without reloading', () => {
    const window = setup();
    const table = window.$('#assignment-children').DataTable();
    change(window, 'stop', '__served__');
    change(window, 'car', 'current');
    assert.equal(table.rows({search: 'applied'}).count(), 40);
    change(window, 'stop', '__missing__');
    assert.equal(table.rows({search: 'applied'}).count(), 0);
    assert.equal(window.document.getElementById('select-filtered').disabled, true);
    window.close();
});

test('Enter in table search cannot submit an assignment', () => {
    const window = setup();
    const search = window.document.querySelector('input[type="search"]');
    const event = new window.KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true});
    search.dispatchEvent(event);
    assert.equal(event.defaultPrevented, true);
    window.close();
});

test('question change reloads answers while discarding the previous stop filter', () => {
    const window = setup('?stop=73%20Chailly&car=none');
    const question = window.document.getElementById('question');
    let submitted = false;
    question.form.submit = () => { submitted = true; };
    change(window, 'question', '2');
    assert.equal(submitted, true);
    const data = new window.FormData(question.form);
    assert.equal(data.get('question'), '2');
    assert.equal(data.get('car'), 'none');
    assert.equal(data.has('stop'), false);
    window.close();
});

test('clicking rows toggles independent selections and survives pagination', () => {
    const window = setup();
    const table = window.$('#assignment-children').DataTable();
    const first = table.row(0).node();
    first.cells[1].click();
    assert.equal(first.classList.contains('selected'), true);
    assert.equal(first.getAttribute('aria-selected'), 'true');
    assert.equal(first.classList.contains('selected'), true);
    table.page('next').draw('page');
    const next = window.document.querySelector('#assignment-children tbody tr');
    next.cells[1].click();
    assert.equal(window.document.getElementById('selection-count').textContent, '2 sélectionné(s)');
    table.page('first').draw('page');
    first.cells[1].click();
    assert.equal(first.classList.contains('selected'), false);
    assert.deepEqual(submit(window).getAll('children'), [next.dataset.childId]);
    window.close();
});

test('links in a row remain usable without selecting children', () => {
    const window = setup();
    const table = window.$('#assignment-children').DataTable();
    const row = window.document.querySelector('#assignment-children tbody tr');
    assert.equal(row.querySelector('input[type="checkbox"]'), null);
    const link = window.document.createElement('a');
    link.href = '#child';
    link.textContent = 'Voir enfant';
    row.cells[0].appendChild(link);
    link.click();
    assert.equal(row.classList.contains('selected'), false);
    assert.equal(window.document.getElementById('assignment-action-controls').hidden, true);
    window.close();
});

test('focused rows support Space and Enter without submitting', () => {
    const window = setup();
    const row = window.document.querySelector('#assignment-children tbody tr');
    assert.equal(row.tabIndex, 0);
    for (const key of [' ', 'Enter']) {
        const event = new window.KeyboardEvent('keydown', {key, bubbles: true, cancelable: true});
        row.dispatchEvent(event);
        assert.equal(event.defaultPrevented, true);
    }
    assert.equal(row.classList.contains('selected'), false);
    window.close();
});

test('pending filter shows only children needing correction across all pages', () => {
    const window = setup();
    const table = window.$('#assignment-children').DataTable();
    change(window, 'car', 'pending');
    assert.equal(table.rows({search: 'applied'}).count(), 80);
    window.document.getElementById('select-filtered').click();
    const ids = submit(window).getAll('children');
    assert.equal(ids.length, 80);
    assert.equal(ids.includes('1'), false);
    assert.equal(ids.includes('120'), true);
    window.close();
});
