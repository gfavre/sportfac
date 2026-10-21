(function () {
    'use strict';
    window.registrationListTable = function (selector, options) {
        // Retire the old status pane selections; they could keep the list on canceled rows.
        var url = new URL(window.location.href);
        if (url.searchParams.has('panes')) {
            url.searchParams.delete('panes');
            url.searchParams.delete('page');
            window.history.replaceState(window.history.state, '', url.href);
        }
        var previousData = options.ajax.data;
        options.ajax.data = function (data, settings) {
            var extra = typeof previousData === 'function' ? previousData(data, settings) : previousData;
            Object.assign(data, extra || {});
            data.status = document.querySelector('#registration-status-filter').value;
        };
        return window.dataTableUrlState(selector, options, [{
            param: 'status', selector: '#registration-status-filter', defaultValue: 'active',
            values: {active: '', all: '', canceled: '', waiting: '', valid: '', confirmed: ''}
        }]);
    };
}());
