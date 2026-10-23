function setCourseHelpVisibility(bubble, visible) {
    bubble.querySelector('small').hidden = !visible;
    bubble.querySelector('.course-help-toggle').setAttribute('aria-expanded', String(visible));
}

document.addEventListener('mouseover', function (event) {
    const button = event.target.closest('.course-action-with-help .needs-select');
    if (!button || button.disabled || button.contains(event.relatedTarget)) return;
    const activeBubble = button.closest('.course-action-with-help').querySelector('.course-action-help');
    document.querySelectorAll('.course-action-help').forEach(function (bubble) {
        setCourseHelpVisibility(bubble, bubble === activeBubble);
    });
});

document.addEventListener('mouseout', function (event) {
    const action = event.target.closest('.course-action-with-help');
    if (!action || action.contains(event.relatedTarget)) return;
    setCourseHelpVisibility(action.querySelector('.course-action-help'), false);
});

document.addEventListener('click', function (event) {
    const toggle = event.target.closest('.course-help-toggle');
    document.querySelectorAll('.course-action-help').forEach(function (bubble) {
        const button = bubble.querySelector('.course-help-toggle');
        const panel = bubble.querySelector('small');
        if (button === toggle) {
            panel.hidden = !panel.hidden;
        } else if (!bubble.contains(event.target)) {
            panel.hidden = true;
        }
        setCourseHelpVisibility(bubble, !panel.hidden);
    });
});

window.initializeCourseActions = function (table) {
    document.querySelectorAll('a[data-course-target]').forEach(function (link) {
        link.addEventListener('click', function (event) {
            const row = table.row(link.getAttribute('href')).node();
            if (!row) return;
            event.preventDefault();
            // A visibility filter may have removed the changed course from the table.
            if (!table.rows({search: 'applied'}).nodes().toArray().includes(row)) {
                if (table.searchPanes) table.searchPanes.clearSelections();
                table.search('').columns().search('');
                table.draw();
            }
            row.setAttribute('tabindex', '-1');
            row.focus({preventScroll: true});
            row.scrollIntoView({behavior: 'smooth', block: 'center'});
        });
    });
    const toolbar = document.querySelector('.course-selection-actions');
    if (!toolbar) return;
    function updateSelection() {
        const count = table.rows({selected: true}).count();
        toolbar.querySelector('.course-selection-heading').textContent = count
            ? count + (count === 1 ? ' cours sélectionné' : ' cours sélectionnés')
            : 'Sélectionnez des cours dans le tableau';
        toolbar.querySelectorAll('.needs-select').forEach(function (button) { button.disabled = count === 0; });
        toolbar.querySelector('[data-deselect]').disabled = count === 0;
        toolbar.querySelector('[data-select-filtered]').disabled = table.rows({search: 'applied'}).count() === 0;
    }
    toolbar.querySelector('[data-select-filtered]').addEventListener('click', function () {
        table.rows({search: 'applied'}).select();
    });
    toolbar.querySelector('[data-deselect]').addEventListener('click', function () { table.rows().deselect(); });
    table.on('select deselect draw', updateSelection);
    updateSelection();
    $(toolbar).find('form').on('submit', function (event) {
        if (!table.rows({selected: true}).count()) { event.preventDefault(); return; }
        const form = this;
        if (form.classList.contains('visibility')) {
            const action = new URL(form.action, window.location.href);
            action.searchParams.set('list_return', window.location.pathname + window.location.search);
            form.action = action.href;
        }
        form.querySelectorAll('input[name="c"]').forEach(function (input) { input.remove(); });
        table.rows({selected: true}).nodes().each(function (row) {
            const input = document.createElement('input');
            input.type = 'hidden'; input.name = 'c'; input.value = row.dataset.courseid;
            form.appendChild(input);
        });
    });
};
