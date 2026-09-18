// Real DataTables/SearchPanes integration, without a browser or a running Django server.
// npm install --prefix /tmp/sportfac-url-state-tests --no-save jsdom@26
// NODE_PATH=/tmp/sportfac-url-state-tests/node_modules node --test tests/js/*.test.js
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');
const registrationTemplate = fs.readFileSync('sportfac/backend/templates/backend/registration/list.html', 'utf8');
const searchPanesVersion = registrationTemplate.match(/sp-([\d.]+)\//)[1];

function page(query = '', serverSide = false, filters = [], registration = false) {
    const rowCount = registration ? (registration.count === undefined ? 2 : registration.count) : 80;
    const rows = Array.from({length: rowCount}, (_, i) => [String(i), i % 2 ? 'ski' : 'natation',
        '<a href="/backend/activity/42/update/">Edit</a>']);
    const dom = new JSDOM('<input type="radio" name="sport" value="both"><input type="radio" name="sport" value="ski"><input type="radio" name="sport" value="natation"><table id="courses"><thead><tr><th>ID</th><th>Sport</th><th>Actions</th></tr></thead></table>', {
        url: 'https://example.test/backend/activity/' + query, runScripts: 'outside-only',
    });
    const window = dom.window;
    for (const file of [
        'sportfac/static/js/vendor/jquery-2.1.1.js',
        'sportfac/static/js/vendor/DataTables-2020/DataTables-1.10.24/js/jquery.dataTables.js',
        'sportfac/static/js/vendor/DataTables-2020/Select-1.3.2/js/dataTables.select.js',
        process.env.SEARCH_PANES_SCRIPT || `sportfac/static/js/vendor/DataTables-2020/SearchPanes-${searchPanesVersion}/js/dataTables.searchPanes.js`,
        'sportfac/backend/static/backend/js/datatable-url-state.js',
    ]) window.eval(fs.readFileSync(file, 'utf8'));
    const requests = [];
    const options = {pageLength: 10, dom: 'Pfrtip', searchPanes: {viewTotal: true, clear: false},
        columns: [{data: 'id'}, {data: 'sport'}, {data: 'actions'}],
        columnDefs: [{targets: 1, searchPanes: {show: true}}, {targets: [0, 2], searchPanes: {show: false}}],
    };
    if (registration) {
        // Use the page's actual status-pane settings, rather than forcing show:true in the fixture.
        const config = registrationTemplate.match(/searchPanes:\s*(\{[^}]*\}),\s*targets: \['status_display'\]/)[1];
        options.columnDefs[0].searchPanes = window.eval('(' + config + ')');
    }
    const records = rows.map(row => ({id: row[0], sport: row[1], actions: row[2]}));
    if (serverSide) {
        options.serverSide = true;
        options.ajax = (data, callback) => {
            requests.push(JSON.parse(JSON.stringify(data)));
            let filtered = records;
            const selected = Object.values((data.searchPanes || {}).sport || {});
            if (selected.length) filtered = filtered.filter(row => selected.includes(row.sport));
            if (data.search.value) filtered = filtered.filter(row => row.sport.includes(data.search.value));
            setTimeout(() => callback({draw: data.draw, recordsTotal: records.length, recordsFiltered: filtered.length,
                data: filtered.slice(data.start, data.start + data.length),
                searchPanes: {options: {sport: [
                    {label: 'ski', value: 'ski', total: 40, count: 40},
                    {label: 'natation', value: 'natation', total: 40, count: 40},
                ]}},
            }), 0);
        };
        if (serverSide === 'object') {
            const respond = options.ajax;
            window.$.ajax = config => {
                respond(config.data, config.success);
                return {readyState: 4, abort() {}};
            };
            options.ajax = {url: '/api/records/', data: {extra: 'kept'}};
        }
    } else options.data = records;
    const table = window.dataTableUrlState('#courses', options, filters);
    return {window, table, requests, close: () => window.close()};
}

for (const count of [0, 2]) {
test('registration status pane stays available with ' + count + ' registrations', async () => {
    const current = page('', 'object', [], {count});
    await settle();
    const panes = current.window.$('table').not('#courses');
    assert.ok(panes.toArray().some(node => current.window.$.fn.dataTable.isDataTable(node)),
        'The status pane must be built even when the automatic uniqueness threshold would hide it');
    current.close();
});
}

test('column radio filter, clearing search and clean URLs do not inherit another tab state', async () => {
    const filter = {param: 'sport', selector: 'input[name=sport]', column: 1,
        defaultValue: 'both', values: {both: '', ski: 'ski', natation: 'natation'}};
    const first = page('?q=ski&sport=ski', false, [filter]);
    await settle();
    assert.equal(first.table.page.info().recordsDisplay, 40);
    assert.equal(first.window.document.querySelector('input[value=ski]').checked, true);
    first.table.search('').draw();
    first.window.$('input[value=both]').prop('checked', true).trigger('change');
    assert.equal(first.table.page.info().recordsDisplay, 80);
    assert.equal(new URLSearchParams(first.window.location.search).has('sport'), false);
    assert.equal(new URLSearchParams(first.window.location.search).has('q'), false);
    const clean = page();
    assert.equal(clean.table.search(), '');
    assert.equal(clean.table.page.info().recordsDisplay, 80);
    assert.equal(first.window.localStorage.length, 0);
    first.close(); clean.close();
});

test('malformed sort, page length and pane state fall back to table defaults', () => {
    for (const order of ['bad json', '{}', '[[99,"asc"]]', '[[1,"wrong"]]']) {
        const current = page('?' + new URLSearchParams({order, page: '-3', length: '999999', panes: '{bad}'}));
        assert.equal(current.table.page(), 0);
        assert.equal(current.table.page.len(), 10);
        assert.equal(current.table.order()[0][0], 0);
        current.close();
    }
});
const settle = () => new Promise(resolve => setTimeout(resolve, 160));

for (const serverSide of [false, true, 'object']) {
    test('restores URL search, ordering and pagination ' + (serverSide ? 'with Ajax ' + serverSide : 'with DOM'), async () => {
        const first = page('?q=ski&order=%5B%5B1%2C%22desc%22%5D%5D&page=2&length=10', serverSide);
        await settle();
        assert.equal(first.table.search(), 'ski');
        assert.equal(first.table.page(), 1);
        assert.equal(first.table.rows({page: 'current'}).count(), 10);
        const link = new URL(first.window.document.querySelector('#courses tbody a').href);
        assert.equal(new URL('https://example.test' + link.searchParams.get('list_return')).searchParams.get('q'), 'ski');
        first.table.search('natation').draw();
        await settle();
        const restored = page(first.window.location.search, serverSide);
        await settle();
        assert.equal(restored.table.search(), 'natation');
        assert.equal(restored.table.page(), 0);
        first.close(); restored.close();
    });
    test('SearchPanes selections survive reload and can be cleared ' + serverSide, async () => {
        const first = page('', serverSide);
        await settle();
        const panes = first.window.$('table').not('#courses');
        // The hidden panes are still DataTables; locate the pane with sport values.
        let sportsPane;
        panes.each(function () {
            const api = first.window.$(this).DataTable();
            if (api.rows().data().toArray().some(row => row.filter === 'ski')) sportsPane = api;
        });
        assert.ok(sportsPane);
        sportsPane.rows((index, row) => row.filter === 'ski').select();
        await settle();
        first.table.page(2).draw('page');
        await settle();
        const query = first.window.location.search;
        assert.ok(new URLSearchParams(query).has('panes'));
        const restored = page(query, serverSide);
        await settle();
        assert.equal(restored.table.page.info().recordsDisplay, 40);
        assert.equal(restored.table.page(), 2);
        if (serverSide) {
            const sent = new URLSearchParams(restored.window.$.param(restored.requests[0]));
            assert.equal(sent.get('searchPanes[sport][0]'), 'ski');
            if (serverSide === 'object') assert.equal(sent.get('extra'), 'kept');
        }
        const saved = JSON.parse(new URLSearchParams(restored.window.location.search).get('panes'));
        assert.ok(saved.some(pane => pane.selected.includes('ski')));
        restored.table.searchPanes.clearSelections();
        await settle();
        assert.equal(restored.table.page.info().recordsDisplay, 80);
        assert.equal(new URLSearchParams(restored.window.location.search).has('panes'), false);
        first.close(); restored.close();
    });
}

test('legacy DataTables 1.10.4 keeps role-list defaults and restores invoice filters', () => {
    const dom = new JSDOM('<select id="status"><option value="all">All</option><option value="paid">Paid</option></select>' +
        '<input id="from"><table id="legacy"><thead><tr><th>Name</th></tr></thead>' +
        '<tbody><tr><td>ski</td></tr><tr><td>natation</td></tr></tbody></table>', {
        url: 'https://example.test/backend/payroll/roles/?q=ski&status=paid&date_from=2026-09-18', runScripts: 'outside-only',
    });
    const w = dom.window;
    for (const path of ['sportfac/static/js/vendor/jquery-2.1.1.js',
        'sportfac/static/js/vendor/datatables/jquery.dataTables.min.js',
        'sportfac/backend/static/backend/js/datatable-url-state.js']) w.eval(fs.readFileSync(path, 'utf8'));
    const table = w.dataTableUrlState('#legacy', {lengthMenu: [25, 100, -1]}, [
        {param: 'status', selector: '#status', defaultValue: 'all', values: {all: '', paid: ''}},
        {param: 'date_from', selector: '#from', defaultValue: '', validate: value => /^\d{4}-\d{2}-\d{2}$/.test(value)},
    ]);
    assert.equal(table.page.len(), 25);
    assert.equal(table.rows({search: 'applied'}).data().toArray().length, 1);
    assert.equal(w.document.querySelector('#status').value, 'paid');
    assert.equal(w.document.querySelector('#from').value, '2026-09-18');
    w.$('#status').val('all').trigger('change');
    assert.equal(new URLSearchParams(w.location.search).has('status'), false);
    assert.equal(new URLSearchParams(w.location.search).get('date_from'), '2026-09-18');
    w.close();
});
