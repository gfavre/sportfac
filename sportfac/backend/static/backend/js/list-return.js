/* Carry a server-validated list URL through detail -> edit and explicit form actions. */
$(function () {
    'use strict';
    var back = JSON.parse(document.getElementById('list-return-url').textContent);
    var lists = JSON.parse(document.getElementById('list-return-paths').textContent);
    var target = new URL(back, window.location.href);
    document.querySelectorAll('.content a[href]').forEach(function (link) {
        var url = new URL(link.href, window.location.href);
        if (link.hasAttribute('data-list-back') ||
                (url.origin === target.origin && url.pathname === target.pathname)) {
            link.href = back;
        } else if (url.origin === target.origin && url.pathname.startsWith('/backend/') &&
                lists.indexOf(url.pathname) === -1 && !link.hasAttribute('download') &&
                !link.getAttribute('href').startsWith('#')) {
            url.searchParams.set('list_return', back);
            link.href = url.href;
        }
    });
    document.querySelectorAll('.content form').forEach(function (form) {
        var url = new URL(form.action || window.location.href, window.location.href);
        if (url.origin === target.origin && url.pathname === window.location.pathname) {
            url.searchParams.set('list_return', back);
            form.action = url.href;
        }
    });
});
