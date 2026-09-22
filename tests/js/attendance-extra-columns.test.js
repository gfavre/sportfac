const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

function setup(value) {
    const template = fs.readFileSync('sportfac/absences/templates/absences/widgets/extra-columns.html', 'utf8')
        .replace(/\{%[\s\S]*?%\}/g, '')
        .replace(/\{\{ widget.name \}\}/g, 'raw_value')
        .replace(/\{\{ widget.value\|default:"\[\]" \}\}/g, '')
        .replace(/\{\{ question \}\}/g, 'Magic Pass');
    const dom = new JSDOM(`<form>${template}</form>`, {runScripts: 'outside-only'});
    const document = dom.window.document;
    document.querySelector('textarea').value = JSON.stringify(value);
    dom.window.eval(fs.readFileSync('sportfac/static/js/attendance-extra-columns.js', 'utf8'));
    document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
    return {dom, document, value: () => JSON.parse(document.querySelector('textarea').value)};
}

test('legacy values survive editing and are saved as structured JSON', () => {
    const {dom, document, value} = setup({Abo: 'Magic Pass'});
    document.querySelector('[data-add-mapping]').click();
    document.querySelector('[data-stored]').value = 'True';
    document.querySelector('[data-displayed]').value = 'M';
    document.querySelector('[data-displayed]').dispatchEvent(new dom.window.Event('input', {bubbles: true}));
    assert.deepEqual(value(), [{question: 'Magic Pass', label: 'Abo', values: {True: 'M'}}]);
    document.querySelector('[data-remove-mapping]').click();
    assert.deepEqual(value()[0].values, {});
    dom.window.close();
});

test('missing questions, ordering and removals preserve configured columns', () => {
    const {dom, document, value} = setup([
        {label: 'Ancien', question: 'Old question', values: {'False': ''}},
        {label: 'Abo', question: 'Magic Pass', values: {}}
    ]);
    assert.equal(document.querySelector('[data-question]').value, 'Old question');
    document.querySelector('[data-down]').click();
    assert.equal(value()[0].label, 'Abo');
    document.querySelector('[data-remove-column]').click();
    assert.deepEqual(value(), [{label: 'Ancien', question: 'Old question', values: {'False': ''}}]);
    document.querySelector('[data-add-column]').click();
    assert.equal(value().length, 2);
    dom.window.close();
});
