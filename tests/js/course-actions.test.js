const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

test('course actions follow selection and submit current IDs without duplicates', () => {
    const dom = new JSDOM('<section class="course-selection-actions"><div class="course-selection-heading"></div><form><button class="needs-select" name="pdf" value="1">PDF</button></form></section>', {runScripts: 'outside-only'});
    const window = dom.window;
    window.eval(fs.readFileSync('sportfac/static/js/vendor/jquery-2.1.1.js', 'utf8'));
    window.eval(fs.readFileSync('sportfac/backend/static/backend/js/course-actions.js', 'utf8'));
    let ids = [];
    let change;
    const table = {
        on: (events, callback) => { change = callback; },
        rows: () => ({count: () => ids.length, nodes: () => ({each: callback => ids.forEach(id => callback({dataset: {courseid: id}}))})})
    };
    window.initializeCourseActions(table);
    const button = window.document.querySelector('button');
    const form = window.document.querySelector('form');
    assert.equal(button.disabled, true);
    ids = ['3', '7']; change();
    assert.equal(button.disabled, false);
    assert.equal(window.document.querySelector('.course-selection-heading').textContent, '2 cours sélectionnés');
    window.$(form).triggerHandler('submit');
    window.$(form).triggerHandler('submit');
    assert.deepEqual(Array.from(form.querySelectorAll('input'), input => input.value), ids);
    ids = ['7']; change();
    window.$(form).triggerHandler('submit');
    assert.deepEqual(Array.from(form.querySelectorAll('input'), input => input.value), ids);
    ids = []; change();
    const event = window.$.Event('submit');
    window.$(form).triggerHandler(event);
    assert.equal(event.isDefaultPrevented(), true);
    assert.equal(button.disabled, true);
    dom.window.close();
});
