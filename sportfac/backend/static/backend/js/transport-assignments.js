(function () {
  'use strict';
  const form = document.getElementById('transport-assignments');
  if (!form) return;
  const stop = document.getElementById('stop');
  const car = document.getElementById('car');
  const question = document.getElementById('question');
  const served = JSON.parse(document.getElementById('served-stops').textContent);
  const button = document.getElementById('assign-selected');
  const destination = document.getElementById('id_destination');
  const params = new URL(window.location.href).searchParams;

  $.fn.dataTable.ext.search.push(function (settings, data, index) {
    if (settings.nTable.id !== 'assignment-children') return true;
    const row = settings.aoData[index].nTr;
    const stops = JSON.parse(row.dataset.stops);
    const cars = JSON.parse(row.dataset.cars);
    let matchesStop = !stop.value || stops.includes(stop.value);
    if (stop.value === '__missing__') matchesStop = !stops.length;
    if (stop.value === '__served__') matchesStop = stops.some(function (value) { return served.includes(value); });
    if (car.value === 'pending') return matchesStop && row.dataset.pending === 'true';
    const carValue = car.value === 'current' ? form.dataset.currentCar : car.value;
    return matchesStop && (carValue === 'all' || cars.includes(carValue));
  });
  const table = $('#assignment-children').DataTable({
    pageLength: 50, lengthMenu: [[25, 50, 100, -1], [25, 50, 100, 'Tous']],
    order: [[0, 'asc']], orderCellsTop: true,
    select: {style: 'multi'},
    columnDefs: [{targets: [1, 2], searchable: false}],
    search: {search: params.get('q') || '', smart: false},
    language: {
      search: 'Rechercher un enfant :', lengthMenu: '_MENU_ enfants par page',
      info: '_START_ à _END_ sur _TOTAL_ enfants', infoEmpty: 'Aucun enfant',
      infoFiltered: '(sur _MAX_)', zeroRecords: 'Aucun enfant ne correspond aux filtres.',
      emptyTable: 'Aucun enfant à placer.', paginate: {previous: 'Précédent', next: 'Suivant'}
    }
  });
  function update() {
    const count = table.rows({selected: true}).count();
    document.getElementById('selection-count').textContent = count ? count + ' sélectionné(s)' : 'Sélectionnez les enfants à affecter';
    document.getElementById('assignment-action-controls').hidden = !count;
    document.getElementById('assignment-toolbar').hidden = !count;
    document.getElementById('assignment-toolbar').classList.toggle('has-selection', !!count);
    document.getElementById('clear-selection').disabled = !count;
    document.getElementById('select-filtered').disabled = !table.rows({search: 'applied'}).count();
    button.disabled = !count || !destination.value;
    button.textContent = count ? 'Affecter (' + count + ')' : 'Affecter';
    table.rows().every(function () {
      const row = this.node();
      row.tabIndex = 0;
      row.setAttribute('aria-selected', String(row.classList.contains('selected')));
    });
  }
  function syncUrl() {
    const url = new URL(window.location.href);
    [['stop', stop.value], ['car', car.value], ['q', table.search()]].forEach(function (item) {
      if (item[1]) url.searchParams.set(item[0], item[1]);
      else url.searchParams.delete(item[0]);
    });
    window.history.replaceState(null, '', url);
  }
  table.on('user-select', function (event, dt, type, cell, originalEvent) {
    if (originalEvent.target.closest('a, button, input, select, textarea, label, [contenteditable]')) event.preventDefault();
  });
  document.getElementById('assignment-children').addEventListener('keydown', function (event) {
    if (!event.target.matches('tbody tr') || ![' ', 'Enter'].includes(event.key)) return;
    event.preventDefault();
    const row = table.row(event.target);
    if (row.node().classList.contains('selected')) row.deselect();
    else row.select();
  });
  document.getElementById('select-filtered').addEventListener('click', function () {
    table.rows({search: 'applied'}).select();
  });
  document.getElementById('clear-selection').addEventListener('click', function () { table.rows().deselect(); });
  table.on('select deselect', update);
  destination.addEventListener('change', update);
  [stop, car].forEach(function (filter) {
    filter.addEventListener('change', function () { table.draw(); });
  });
  table.on('draw', function () {
    // A changed filter must never leave hidden children selected for a move.
    table.rows({search: 'removed', selected: true}).deselect();
    update();
    syncUrl();
  });
  form.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && event.target.type === 'search') event.preventDefault();
  });
  form.addEventListener('submit', function () {
    // DataTables detaches other pages: submit explicit IDs, not just the current DOM page.
    form.querySelectorAll('input[data-selected-child]').forEach(function (input) { input.remove(); });
    table.rows({selected: true}).nodes().each(function (row) {
      const input = document.createElement('input');
      input.type = 'hidden'; input.name = 'children'; input.value = row.dataset.childId; input.dataset.selectedChild = 'true';
      form.appendChild(input);
    });
    form.action = window.location.pathname + window.location.search;
  });
  question.addEventListener('change', function () {
    const url = new URL(window.location.href);
    url.searchParams.set('question', question.value);
    url.searchParams.delete('stop');
    question.form.querySelectorAll('input[data-question-state]').forEach(function (input) { input.remove(); });
    url.searchParams.forEach(function (value, key) {
      if (key === 'question') return;
      const input = document.createElement('input');
      input.type = 'hidden'; input.name = key; input.value = value; input.dataset.questionState = 'true';
      question.form.appendChild(input);
    });
    question.form.submit();
  });
  table.rows(function (index, data, row) { return row.dataset.selected === 'true'; }).select();
  update();
}());
