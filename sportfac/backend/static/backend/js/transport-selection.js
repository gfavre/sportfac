window.initializeTransportSelection = function (table) {
    const form = document.getElementById('transport-sheets-form');
    if (!form) return;
    const toolbar = form.closest('.selection-actions');
    const selected = new Set();
    const list = document.getElementById('list-table');
    const submit = form.querySelector('button[type="submit"]');
    const deselect = toolbar.querySelector('[data-deselect-transports]');
    function update() {
        const count = selected.size;
        toolbar.querySelector('[data-transport-selection-count]').textContent = count
            ? count + (count === 1 ? ' car sélectionné' : ' cars sélectionnés')
            : 'Sélectionnez les cars dans le tableau';
        submit.disabled = count === 0;
        deselect.disabled = count === 0;
        table.rows().nodes().each(function (row) {
            const checkbox = row.querySelector('.transport-select');
            checkbox.checked = selected.has(checkbox.value);
            row.classList.toggle('selected', checkbox.checked);
        });
    }
    list.addEventListener('change', function (event) {
        if (!event.target.matches('.transport-select')) return;
        if (event.target.checked) selected.add(event.target.value);
        else selected.delete(event.target.value);
        update();
    });
    list.addEventListener('click', function (event) {
        if (event.target.closest('a, button, input, label, select, textarea')) return;
        const row = event.target.closest('tbody tr');
        if (!row) return;
        const checkbox = row.querySelector('.transport-select');
        if (!checkbox) return;
        if (selected.has(checkbox.value)) selected.delete(checkbox.value);
        else selected.add(checkbox.value);
        update();
    });
    toolbar.querySelector('[data-select-transports]').addEventListener('click', function () {
        table.rows({search: 'applied'}).nodes().each(function (row) {
            selected.add(row.querySelector('.transport-select').value);
        });
        update();
    });
    deselect.addEventListener('click', function () { selected.clear(); update(); });
    table.on('draw', update);
    form.addEventListener('submit', function (event) {
        if (!selected.size) { event.preventDefault(); return; }
        form.querySelectorAll('input[name="t"]').forEach(function (input) { input.remove(); });
        selected.forEach(function (id) {
            const input = document.createElement('input');
            input.type = 'hidden'; input.name = 't'; input.value = id;
            form.appendChild(input);
        });
    });
    update();
};
