(function () {
    'use strict';
    function enhancePhones(root) {
        root.querySelectorAll('input.form-control').forEach(function (input) {
            const name = (input.name || '').split('-').pop();
            if (!['text', 'tel'].includes(input.type)) return;
            if (input.type !== 'tel' && !['private_phone', 'private_phone2', 'private_phone3', 'phone', 'phone_number', 'emergency_number'].includes(name)) return;
            if (input.closest('.phone-input')) return;
            input.type = 'tel';
            if (!input.placeholder) input.placeholder = '079 123 45 67';
            const wrapper = document.createElement('div');
            wrapper.className = 'phone-input';
            const icon = document.createElement('i');
            icon.className = 'icon-phone';
            icon.setAttribute('aria-hidden', 'true');
            input.before(wrapper);
            wrapper.append(icon, input);
        });
    }
    document.addEventListener('DOMContentLoaded', function () {
        const content = document.querySelector('.content');
        if (!content) return;
        enhancePhones(content);
        new MutationObserver(function (changes) {
            if (changes.some(change => change.addedNodes.length)) enhancePhones(content);
        }).observe(content, {childList: true, subtree: true});
    });
})();
