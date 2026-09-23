(function () {
  'use strict';
  var form = document.querySelector('[data-diploma-create]');
  if (!form) return;
  var courses = form.querySelector('[name="courses"]');
  var status = form.querySelector('[data-level-status]');
  var submit = form.querySelector('[type="submit"]');
  var revision = 0;
  async function refreshLevels() {
    var current = ++revision;
    var previous = new Map(Array.from(form.querySelectorAll('[name="final_levels"]'), function (input) {
      return [input.value, input.checked];
    }));
    var url = new URL(form.dataset.diplomaCreate, window.location.origin);
    Array.from(courses.selectedOptions).forEach(function (option) { url.searchParams.append('c', option.value); });
    submit.disabled = true;
    status.textContent = 'Actualisation des niveaux des cours sélectionnés…';
    try {
      var response = await fetch(url, {credentials: 'same-origin', cache: 'no-store'});
      if (!response.ok || response.redirected) throw new Error('Unavailable');
      var page = new DOMParser().parseFromString(await response.text(), 'text/html');
      var replacement = page.querySelector('#div_id_final_levels');
      if (!replacement) throw new Error('Missing levels');
      if (current !== revision) return;
      replacement.querySelectorAll('[name="final_levels"]').forEach(function (input) {
        if (previous.has(input.value)) input.checked = previous.get(input.value);
      });
      form.querySelector('#div_id_final_levels').replaceWith(replacement);
      status.textContent = replacement.querySelector('[name="final_levels"]') ? '' : 'Aucun enfant dans les cours sélectionnés.';
      submit.disabled = false;
    } catch (error) {
      if (current === revision) status.textContent = 'Impossible d’actualiser les niveaux. Modifiez la sélection des cours pour réessayer.';
    }
  }
  if (window.jQuery) window.jQuery(courses).on('change', refreshLevels);
  else courses.addEventListener('change', refreshLevels);
}());
