document.addEventListener('DOMContentLoaded', function () {
  const input = document.querySelector('.account-birth-date');
  if (!input) return;

  $.fn.datepicker.dates.fr = {
    days: ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'],
    daysShort: ['dim.', 'lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.'],
    daysMin: ['di', 'lu', 'ma', 'me', 'je', 've', 'sa', 'di'],
    months: ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'],
    monthsShort: ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'],
    today: 'Aujourd’hui',
    clear: 'Effacer'
  };

  $(input).datepicker({
    format: 'dd.mm.yyyy',
    language: document.documentElement.lang.startsWith('fr') ? 'fr' : 'en',
    weekStart: 1,
    startView: 2,
    autoclose: true,
    forceParse: false
  });
  // This vendored picker toggles the selected day off; keep a birth date on a repeated click.
  const picker = $(input).data('datepicker');
  picker.picker[0].addEventListener('click', function (event) {
    if (event.target.closest('td.day.active')) {
      event.preventDefault();
      event.stopPropagation();
      $(input).datepicker('hide');
    }
  }, true);
  $(input).wrap('<div class="input-group account-date-control"></div>');
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'btn btn-default';
  button.setAttribute('aria-label', input.dataset.calendarLabel);
  const icon = document.createElement('i');
  icon.className = 'icon-calendar';
  icon.setAttribute('aria-hidden', 'true');
  button.append(icon);
  const addon = document.createElement('span');
  addon.className = 'input-group-btn';
  addon.append(button);
  input.parentNode.append(addon);
  button.addEventListener('click', function () {
    input.focus();
    $(input).datepicker('update');
    $(input).datepicker('show');
  });
});
