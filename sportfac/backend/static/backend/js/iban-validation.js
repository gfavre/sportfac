(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-iban-validation-url]').forEach(function (input) {
      const status = document.createElement('span');
      status.id = input.id + '-validation';
      status.className = 'help-block';
      status.setAttribute('role', 'status');
      input.after(status);
      input.setAttribute('aria-describedby', [input.getAttribute('aria-describedby'), status.id].filter(Boolean).join(' '));
      let timer;
      let revision = 0;
      async function validate() {
        const current = ++revision;
        status.textContent = '';
        input.removeAttribute('aria-invalid');
        if (!input.value.trim()) return;
        try {
          const response = await fetch(input.dataset.ibanValidationUrl, {
            method: 'POST',
            headers: {'X-CSRFToken': input.form.querySelector('[name=csrfmiddlewaretoken]').value},
            body: new URLSearchParams({iban: input.value}),
            credentials: 'same-origin'
          });
          if (!response.ok) return;
          const result = await response.json();
          if (current !== revision) return;
          status.className = 'help-block ' + (result.valid ? 'text-success' : 'text-danger');
          const icon = document.createElement('i');
          icon.className = result.valid ? 'icon-ok' : 'icon-warning';
          icon.setAttribute('aria-hidden', 'true');
          status.replaceChildren(icon, document.createTextNode(' ' + result.message));
          input.setAttribute('aria-invalid', String(!result.valid));
        } catch (_) {
          // Saving still runs the authoritative server-side validation.
        }
      }
      input.addEventListener('input', function () {
        ++revision;
        clearTimeout(timer);
        status.textContent = '';
        input.removeAttribute('aria-invalid');
        timer = setTimeout(validate, 600);
      });
      input.addEventListener('blur', function () { clearTimeout(timer); validate(); });
    });
  });
})();
