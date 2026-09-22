window.initializeCourseActions = function (table) {
    const toolbar = document.querySelector('.course-selection-actions');
    if (!toolbar) return;
    function updateSelection() {
        const count = table.rows({selected: true}).count();
        toolbar.querySelector('.course-selection-heading').textContent = count
            ? count + (count === 1 ? ' cours sélectionné' : ' cours sélectionnés')
            : 'Sélectionnez des cours dans le tableau';
        toolbar.querySelectorAll('.needs-select').forEach(function (button) { button.disabled = count === 0; });
    }
    table.on('select deselect', updateSelection);
    updateSelection();
    $(toolbar).find('form').on('submit', function (event) {
        if (!table.rows({selected: true}).count()) { event.preventDefault(); return; }
        const form = this;
        form.querySelectorAll('input[name="c"]').forEach(function (input) { input.remove(); });
        table.rows({selected: true}).nodes().each(function (row) {
            const input = document.createElement('input');
            input.type = 'hidden'; input.name = 'c'; input.value = row.dataset.courseid;
            form.appendChild(input);
        });
    });
};
