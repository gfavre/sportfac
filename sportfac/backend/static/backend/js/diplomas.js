(function () {
  'use strict';
  var form = document.querySelector('[data-diploma-actions]');
  if (form) {
    form.addEventListener('submit', function (event) {
      var button = event.submitter;
      if (!button || button.value !== 'download') return;
      var action = document.createElement('input');
      action.type = 'hidden';
      action.name = 'action';
      action.value = button.value;
      form.appendChild(action);
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      button.innerHTML = '<i class="diploma-spinner" aria-hidden="true"></i> Génération des diplômes, restez sur cette page';
    });
  }
  var panel = document.querySelector('[data-diploma-poll]');
  if (!panel) return;
  var message = panel.querySelector('[data-poll-message]');
  async function poll() {
    var controller = new AbortController();
    var timeout = window.setTimeout(function () { controller.abort(); }, 10000);
    try {
      var response = await fetch(panel.dataset.diplomaPoll, {
        credentials: 'same-origin', cache: 'no-store', signal: controller.signal
      });
      if (response.redirected || response.status === 403) {
        message.textContent = 'Session expirée. Rechargez la page pour vous reconnecter.';
        return;
      }
      if (!response.ok) throw new Error('Status unavailable');
      var data = await response.json();
      if (data.status === 'ready' || data.status === 'failed') {
        // Refresh once at completion; ?download=1 triggers the saved PDF download.
        window.location.reload();
        return;
      }
      message.textContent = data.status === 'queued' ? 'En attente de traitement…' : 'Préparation en arrière-plan…';
    } catch (error) {
      message.textContent = 'Connexion interrompue, nouvelle vérification dans quelques secondes…';
    } finally {
      window.clearTimeout(timeout);
    }
    window.setTimeout(poll, 3000);
  }
  poll();
}());
