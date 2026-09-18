const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const window = {};
vm.runInNewContext(fs.readFileSync('sportfac/backend/static/backend/js/bill-list-filters.js', 'utf8'), {window});
const matches = window.billMatchesFilters;
const bill = {date: '2026-09-18', status: 'paid', amount: 15.5};
const all = {from: '', to: '', status: 'all', amount: 'all'};

test('date range includes the entire last calendar day and can be widened or cleared', () => {
    assert.equal(matches(bill, {...all, from: '2026-09-18', to: '2026-09-18'}), true);
    assert.equal(matches(bill, {...all, to: '2026-09-17'}), false);
    assert.equal(matches(bill, {...all, to: '2026-09-19'}), true);
    assert.equal(matches(bill, all), true);
});

test('payment status and amount combine with dates', () => {
    assert.equal(matches(bill, {...all, status: 'paid', amount: 'positive'}), true);
    assert.equal(matches(bill, {...all, status: 'waiting'}), false);
    assert.equal(matches(bill, {...all, amount: 'zero'}), false);
    assert.equal(matches({...bill, amount: 0}, {...all, amount: 'zero'}), true);
    assert.equal(matches({...bill, amount: -15}, {...all, amount: 'positive'}), false);
});
