const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

const source = fs.readFileSync('sportfac/backend/static/backend/js/appointments-list.js', 'utf8');

async function setup(t, late = false) {
    const dom = new JSDOM(`
      <form method="get" class="appointments-filters">
        <select name="date"><option value="all">All</option><option value="2026-11-20">20</option></select>
        <input name="q" type="search">
        <input name="empty" type="hidden" value="0">
        <input name="empty" type="checkbox" value="1" checked>
        <button type="submit">Search</button>
      </form>
      <p id="appointments-filter-status" hidden data-loading="Loading" data-error="Failed"></p>
      <div id="appointment-results">Original</div>
      <div id="appointment-modal"><div class="modal-content"></div></div>`, {
        url: 'https://example.test/hiver/backend/site/appointments/list?page=3', runScripts: 'outside-only',
    });
    t.after(() => dom.window.close());
    const w = dom.window;
    w.$ = () => ({on() {}});
    const requests = [];
    w.fetch = async url => {
        requests.push(new URL(url));
        return {ok: true, text: async () => '<div id="appointment-results">Camille</div>'};
    };
    if (late) await new Promise(resolve => w.addEventListener('load', resolve, {once: true}));
    w.eval(source);
    if (!late) await new Promise(resolve => w.document.addEventListener('DOMContentLoaded', resolve, {once: true}));
    return {w, requests, form: w.document.querySelector('form')};
}

for (const late of [false, true]) {
    test(`typing searches existing appointments when script loads ${late ? 'after' : 'before'} DOMContentLoaded`, async t => {
        const {w, requests, form} = await setup(t, late);
        form.elements.q.value = 'Camille Exemple';
        form.elements.q.dispatchEvent(new w.Event('input'));
        await new Promise(resolve => setTimeout(resolve, 420));
        assert.equal(requests.length, 1);
        assert.equal(requests[0].pathname, '/hiver/backend/site/appointments/list');
        assert.equal(requests[0].searchParams.get('q'), 'Camille Exemple');
        assert.equal(requests[0].searchParams.get('empty'), '1');
        assert.equal(requests[0].searchParams.has('page'), false);
        assert.equal(w.document.getElementById('appointment-results').textContent, 'Camille');
        assert.equal(w.document.getElementById('appointments-filter-status').hidden, true);
    });
}

test('explicit submit keeps native GET navigation and cancels pending live search', async t => {
    const {w, requests, form} = await setup(t);
    form.elements.q.value = 'Camille';
    form.elements.q.dispatchEvent(new w.Event('input'));
    const submit = new w.Event('submit', {bubbles: true, cancelable: true});
    form.dispatchEvent(submit);
    assert.equal(submit.defaultPrevented, false);
    const data = new w.FormData(form);
    assert.equal(data.get('q'), 'Camille');
    assert.equal(data.getAll('empty').at(-1), '1');
    await new Promise(resolve => setTimeout(resolve, 420));
    assert.equal(requests.length, 0);
});

test('failed live search keeps results and displays an error', async t => {
    const {w, form} = await setup(t);
    w.fetch = async () => { throw new Error('offline'); };
    form.elements.q.value = 'Camille';
    form.elements.q.dispatchEvent(new w.Event('input'));
    await new Promise(resolve => setTimeout(resolve, 420));
    assert.equal(w.document.getElementById('appointment-results').textContent, 'Original');
    const status = w.document.getElementById('appointments-filter-status');
    assert.equal(status.hidden, false);
    assert.equal(status.textContent, 'Failed');
});
