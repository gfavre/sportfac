const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

test('detail -> edit and explicit form action retain origin; cancel returns to it', () => {
    const back = '/backend/user/instructors?q=ski&page=2';
    const dom = new JSDOM('<div class="content">' +
        '<a id="edit" href="/backend/user/42/update/">Edit</a>' +
        '<a id="cancel" data-list-back href="/backend/user/">Cancel</a>' +
        '<a id="other-list" href="/backend/child/">Children</a>' +
        '<a id="external" href="https://example.org/">External</a>' +
        '<a id="tab" href="#tab">Tab</a>' +
        '<form action="/backend/user/42/"></form></div>' +
        '<script type="application/json" id="list-return-url"></script>' +
        '<script type="application/json" id="list-return-paths"></script>', {
        url: 'https://example.test/backend/user/42/?' + new URLSearchParams({list_return: back}), runScripts: 'outside-only',
    });
    const w = dom.window;
    w.document.getElementById('list-return-url').textContent = JSON.stringify(back);
    w.document.getElementById('list-return-paths').textContent = JSON.stringify(['/backend/child/']);
    w.$ = callback => callback();
    w.eval(fs.readFileSync('sportfac/backend/static/backend/js/list-return.js', 'utf8'));
    assert.equal(new URL(w.document.getElementById('edit').href).searchParams.get('list_return'), back);
    assert.equal(w.document.getElementById('cancel').getAttribute('href'), back);
    assert.equal(w.document.getElementById('other-list').getAttribute('href'), '/backend/child/');
    assert.equal(w.document.getElementById('external').getAttribute('href'), 'https://example.org/');
    assert.equal(w.document.getElementById('tab').getAttribute('href'), '#tab');
    assert.equal(new URL(w.document.querySelector('form').action).searchParams.get('list_return'), back);
    w.close();
});
