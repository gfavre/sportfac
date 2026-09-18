/* Dates are local calendar dates (YYYY-MM-DD), so both boundaries are inclusive. */
window.billMatchesFilters = function (bill, filters) {
    'use strict';
    return (!filters.from || bill.date >= filters.from) &&
        (!filters.to || bill.date <= filters.to) &&
        (filters.status === 'all' || filters.status === bill.status) &&
        (filters.amount === 'all' || (filters.amount === 'positive' && bill.amount > 0) ||
            (filters.amount === 'zero' && bill.amount === 0));
};
