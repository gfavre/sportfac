// Run with: node --test tests/js/datatable-url-state.test.js
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup(query) {
    const window = {location: {href: 'https://example.test/courses/' + query}};
    let replacements = 0;
    window.history = {state: {existing: true}, replaceState(state, title, url) {
        assert.equal(state.existing, true);
        window.location.href = url;
        replacements++;
    }};
    const link = {href: 'https://example.test/courses/42/update/'};
    const radios = ['both', 'announced', 'notannounced'].map(value => ({value}));
    let draw, options, api;
    const element = {
        on(event, callback) { draw = callback; },
        find() { return {each(callback) { callback.call(link); }}; },
        DataTable(config) {
            options = config;
            api = {
                search: () => options.search.search,
                order: () => options.order || [[0, 'asc']],
                column: index => ({search: () => options.searchCols[index].search}),
            };
            return api;
        },
    };
    const $ = selector => selector === '#courses' ? element : {on() {}};
    $.fn = {dataTable: {Api: function () { return api; }}};
    const document = {
        querySelector: () => ({querySelectorAll: () => Array(11)}),
        querySelectorAll: () => radios,
    };
    vm.runInNewContext(fs.readFileSync('sportfac/backend/static/backend/js/datatable-url-state.js', 'utf8'),
        {window, document, $, URL});
    window.dataTableUrlState('#courses', {paging: false}, [{
        param: 'only_js', column: 8, selector: 'input', defaultValue: 'both',
        values: {both: '', announced: 'true', notannounced: 'false'},
    }]);
    return {window, link, radios, options, draw: () => draw(null, {}), replacements: () => replacements};
}

test('reload restores search, sort and J+S; draw carries state to edit links', () => {
    const state = new URLSearchParams({q: 'ski & été', order: '[[1,"desc"]]', only_js: 'announced', other: 'kept'});
    const page = setup('?' + state);
    assert.equal(page.options.search.search, 'ski & été');
    assert.equal(JSON.stringify(page.options.order), '[[1,"desc"]]');
    assert.equal(page.options.searchCols[8].search, 'true');
    assert.equal(page.radios[1].checked, true);
    page.draw();
    assert.equal(page.replacements(), 1);
    const returned = new URLSearchParams(new URL(page.link.href).searchParams.get('list_query'));
    assert.equal(returned.get('q'), 'ski & été');
    assert.equal(returned.get('other'), 'kept');
    const reloaded = setup('?' + returned);
    assert.equal(reloaded.options.search.search, 'ski & été');
});

test('clearing filters removes stale search parameters', () => {
    const page = setup('?q=diablerets&only_js=announced');
    page.options.search.search = '';
    page.options.searchCols[8].search = '';
    page.draw();
    const params = new URL(page.window.location.href).searchParams;
    assert.equal(params.has('q'), false);
    assert.equal(params.has('only_js'), false);
});

test('malformed and out-of-range sort/filter values fall back to defaults', () => {
    for (const order of ['bad json', '{}', '[[99,"asc"]]', '[[1,"wrong"]]', '[[10,"asc"]]']) {
        const page = setup('?' + new URLSearchParams({order, only_js: 'invalid'}));
        assert.equal(page.options.order, undefined);
        assert.equal(page.radios[0].checked, true);
        assert.equal(page.options.searchCols[8].search, '');
    }
});
