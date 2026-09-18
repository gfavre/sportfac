/* Opt-in URL state for client-side DataTables. Load before initializing the table. */
window.dataTableUrlState = function (selector, options, filters) {
    'use strict';
    filters = filters || [];
    var params = new URL(window.location.href).searchParams;
    var count = document.querySelector(selector).querySelectorAll('thead th').length;
    options.search = {search: params.get('q') || ''};
    try {
        var order = JSON.parse(params.get('order'));
        if (Array.isArray(order) && order.length && order.every(function (entry) {
            return Array.isArray(entry) && entry.length === 2 &&
                Number.isInteger(entry[0]) && entry[0] >= 0 && entry[0] < count - 1 &&
                (entry[1] === 'asc' || entry[1] === 'desc');
        })) options.order = order;
    } catch (error) { /* Ignore malformed URL state. */ }

    options.searchCols = Array.from({length: count}, function () { return null; });
    filters.forEach(function (filter) {
        var value = params.get(filter.param);
        if (!Object.prototype.hasOwnProperty.call(filter.values, value)) value = filter.defaultValue;
        options.searchCols[filter.column] = {search: filter.values[value]};
        document.querySelectorAll(filter.selector).forEach(function (input) {
            input.checked = input.value === value;
        });
    });

    var element = $(selector);
    // Bind before construction: the language file can make initialization asynchronous.
    element.on('draw.dt', function (event, settings) {
        var table = new $.fn.dataTable.Api(settings);
        var url = new URL(window.location.href);
        if (table.search()) url.searchParams.set('q', table.search());
        else url.searchParams.delete('q');
        url.searchParams.set('order', JSON.stringify(table.order()));
        filters.forEach(function (filter) {
            var value = Object.keys(filter.values).find(function (key) {
                return filter.values[key] === table.column(filter.column).search();
            });
            if (value && value !== filter.defaultValue) url.searchParams.set(filter.param, value);
            else url.searchParams.delete(filter.param);
        });
        window.history.replaceState(window.history.state, '', url.href);
        element.find('a[data-list-return]').each(function () {
            var target = new URL(this.href, window.location.href);
            target.searchParams.set('list_query', url.searchParams.toString());
            this.href = target.href;
        });
    });
    var table = element.DataTable(options);
    filters.forEach(function (filter) {
        $(filter.selector).on('change', function () {
            table.column(filter.column).search(filter.values[this.value]).draw();
        });
    });
    return table;
};
