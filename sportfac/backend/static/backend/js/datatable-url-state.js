/* Opt-in URL state for DataTables, including server-side tables and SearchPanes.
 * No local/session storage: each tab and each bookmarked URL has its own state.
 */
(function () {
    'use strict';
    function parse(value, fallback) {
        try { return JSON.parse(value) || fallback; } catch (error) { return fallback; }
    }
    function validOrder(order, count) {
        return Array.isArray(order) && order.every(function (entry) {
            return Array.isArray(entry) && entry.length === 2 &&
                Number.isInteger(entry[0]) && entry[0] >= 0 && entry[0] < count &&
                (entry[1] === 'asc' || entry[1] === 'desc');
        });
    }
    function setParam(url, key, value) {
        if (value === '' || value === null || value === undefined) url.searchParams.delete(key);
        else url.searchParams.set(key, value);
    }
    function restoreFilters(filters) {
        var params = new URL(window.location.href).searchParams;
        filters.forEach(function (filter) {
            var value = params.get(filter.param);
            var valid = filter.validate ? filter.validate(value) :
                Object.prototype.hasOwnProperty.call(filter.values, value);
            if (!valid) value = filter.defaultValue;
            document.querySelectorAll(filter.selector).forEach(function (input) {
                if (input.type === 'radio') input.checked = input.value === value;
                else input.value = value;
            });
        });
    }
    function filterValue(filter) {
        var input = document.querySelector(filter.selector + (filter.column !== undefined ? ':checked' : ''));
        return input ? input.value : filter.defaultValue;
    }
    function compactPanes(panes, count) {
        if (!Array.isArray(panes)) return [];
        return panes.filter(function (pane) {
            return pane && Number.isInteger(pane.id) && pane.id >= 0 && pane.id < count &&
                Array.isArray(pane.selected) && pane.selected.every(function (value) {
                    return typeof value === 'string';
                });
        }).map(function (pane) {
            return {id: pane.id, selected: pane.selected,
                searchTerm: typeof pane.searchTerm === 'string' ? pane.searchTerm : '',
                order: validOrder(pane.order, 2) ? pane.order : [[0, 'asc']]};
        });
    }
    function decorateLinks(element) {
        var current = new URL(window.location.href);
        current.searchParams.delete('list_return');
        element.find('a[href]').each(function () {
            var target = new URL(this.href, current.href);
            // Downloads, telephone links, external links and JS buttons are not return paths.
            if (target.origin !== current.origin || !target.pathname.startsWith('/backend/') ||
                    target.pathname === current.pathname || this.hasAttribute('download') ||
                    this.getAttribute('href').startsWith('#')) return;
            target.searchParams.delete('list_query');
            target.searchParams.set('list_return', current.pathname + current.search);
            this.href = target.href;
        });
    }
    window.dataTableUrlState = function (selector, options, filters) {
        filters = filters || [];
        restoreFilters(filters);
        var params = new URL(window.location.href).searchParams;
        var count = document.querySelector(selector).querySelectorAll('thead th').length;
        var order = parse(params.get('order'), null);
        if (validOrder(order, count)) options.order = order;
        options.search = Object.assign({}, options.search, {search: params.get('q') || ''});
        options.searchCols = options.searchCols || Array.from({length: count}, function () { return null; });
        filters.forEach(function (filter) {
            if (filter.column !== undefined) {
                options.searchCols[filter.column] = {search: filter.values[filterValue(filter)]};
            }
        });
        var length = Number(params.get('length'));
        var menu = options.lengthMenu || [10, 25, 50, 100];
        var lengths = Array.isArray(menu[0]) ? menu[0] : menu;
        if (lengths.indexOf(length) !== -1) options.pageLength = length;
        var pageLength = options.pageLength || lengths[0];
        var page = Number(params.get('page'));
        var start = Number.isSafeInteger(page) && page > 0 && pageLength > 0 ? (page - 1) * pageLength : 0;
        if (!Number.isSafeInteger(start)) start = 0;
        options.displayStart = start;
        var panes = compactPanes(parse(params.get('panes'), []), count);
        // SearchPanes 1.2 restores its UI only after the first Ajax response.
        // Seed that request too, otherwise the selected panes display unfiltered rows.
        if (options.serverSide && panes.length) {
            var seedRequest = function (data) {
                if (data.draw !== 1) return;
                data.searchPanes = data.searchPanes || {};
                panes.forEach(function (pane) {
                    var column = options.columns[pane.id];
                    // The API expects indexed keys ([0]), not jQuery's array keys ([]).
                    if (column && pane.selected.length) data.searchPanes[column.data] = Object.assign({}, pane.selected);
                });
            };
            if (typeof options.ajax === 'function') {
                var ajax = options.ajax;
                options.ajax = function (data, callback, settings) {
                    seedRequest(data);
                    return ajax.call(this, data, callback, settings);
                };
            } else {
                if (typeof options.ajax === 'string') options.ajax = {url: options.ajax};
                var ajaxData = options.ajax.data;
                options.ajax.data = function (data, settings) {
                    var extra = typeof ajaxData === 'function' ? ajaxData.call(this, data, settings) : ajaxData;
                    Object.assign(data, extra || {});
                    seedRequest(data);
                };
            }
        }
        var element = $(selector);
        var ready = false;
        // Use the native state lifecycle so SearchPanes restores its selections too.
        // The callbacks deliberately replace DataTables' browser-storage defaults.
        options.stateSave = true;
        options.searchPanes = options.searchPanes || {};
        options.searchPanes.dtOpts = Object.assign({}, options.searchPanes.dtOpts, {
            stateSave: false,
            stateLoadCallback: function () { return null; },
            stateSaveCallback: function () {}
        });
        options.stateLoadCallback = function (settings) {
            var search = function (value) { return {search: value || '', smart: true, regex: false, caseInsensitive: true}; };
            var state = {
                time: Date.now(), start: start, length: pageLength,
                order: options.order || [[0, 'asc']], search: search(options.search.search),
                columns: settings.aoColumns.map(function (column, index) {
                    return {visible: column.bVisible,
                        search: search(options.searchCols[index] && options.searchCols[index].search)};
                })
            };
            if (panes.length) state.searchPanes = {panes: panes};
            return state;
        };
        options.stateSaveCallback = function (settings, state) {
            // SearchPanes saves intermediate states while constructing its panes.
            if (!ready || !state.search) return;
            var url = new URL(window.location.href);
            setParam(url, 'q', state.search.search);
            setParam(url, 'order', JSON.stringify(state.order));
            if (options.paging !== false) {
                setParam(url, 'page', state.length > 0 && state.start > 0 ? Math.floor(state.start / state.length) + 1 : '');
                setParam(url, 'length', state.length);
            }
            var savedPanes = compactPanes(state.searchPanes && state.searchPanes.panes, count);
            var hasPanes = savedPanes.some(function (pane) { return pane.selected.length || pane.searchTerm; });
            setParam(url, 'panes', hasPanes ? JSON.stringify(savedPanes) : '');
            filters.forEach(function (filter) {
                var value = filterValue(filter);
                setParam(url, filter.param, value === filter.defaultValue ? '' : value);
            });
            window.history.replaceState(window.history.state, '', url.href);
            decorateLinks(element);
        };
        element.on('init.dt', function (event, settings) {
            if (settings.nTable !== document.querySelector(selector)) return;
            ready = true;
            new $.fn.dataTable.Api(settings).state.save();
        });
        element.on('draw.dt', function (event, settings) {
            if (settings.nTable === document.querySelector(selector)) decorateLinks(element);
        });
        var table = element.DataTable(options);
        filters.forEach(function (filter) {
            $(filter.selector).on('change', function () {
                if (filter.column !== undefined) table.column(filter.column).search(filter.values[this.value]);
                table.draw();
            });
        });
        return table;
    };
    window.dataTableUrlState.restoreFilters = restoreFilters;
}());
