document.addEventListener('DOMContentLoaded', function () {
  const filters = document.querySelector('.appointments-filters');
  const results = document.getElementById('appointment-results');
  const filterStatus = document.getElementById('appointments-filter-status');
  let filterController;
  let searchTimer;

  async function loadResults(url, pushHistory) {
    if (filterController) filterController.abort();
    const requestController = new AbortController();
    filterController = requestController;
    results.setAttribute('aria-busy', 'true');
    filterStatus.hidden = false;
    filterStatus.textContent = filterStatus.dataset.loading;
    try {
      const response = await fetch(url, {signal: requestController.signal});
      if (response.redirected) {
        window.location.assign(response.url);
        return;
      }
      if (!response.ok) throw new Error('Loading failed');
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const replacement = page.getElementById('appointment-results');
      if (!replacement) throw new Error('Missing results');
      results.replaceChildren(...replacement.childNodes);
      if (pushHistory) window.history.pushState(null, '', url);
      else window.history.replaceState(null, '', url);
      filterStatus.hidden = true;
    } catch (error) {
      if (error.name !== 'AbortError') filterStatus.textContent = filterStatus.dataset.error;
    } finally {
      if (filterController === requestController) results.setAttribute('aria-busy', 'false');
    }
  }

  function applyFilters() {
    clearTimeout(searchTimer);
    const url = new URL(window.location.href);
    url.searchParams.set('date', filters.elements.date.value);
    url.searchParams.set('empty', filters.querySelector('input[type="checkbox"]').checked ? '1' : '0');
    const search = filters.elements.q.value.trim();
    if (search) url.searchParams.set('q', search);
    else url.searchParams.delete('q');
    url.searchParams.delete('page');
    loadResults(url.href, false);
  }

  filters.elements.date.addEventListener('change', applyFilters);
  filters.querySelector('input[type="checkbox"]').addEventListener('change', applyFilters);
  filters.elements.q.addEventListener('input', function () {
    clearTimeout(searchTimer);
    if (filterController) filterController.abort();
    searchTimer = setTimeout(applyFilters, 350);
  });
  filters.addEventListener('submit', function (event) {
    event.preventDefault();
    applyFilters();
  });
  results.addEventListener('click', function (event) {
    const link = event.target.closest('.appointments-pagination a');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    clearTimeout(searchTimer);
    loadResults(link.href, true);
  });
  window.addEventListener('popstate', function () {
    clearTimeout(searchTimer);
    const url = new URL(window.location.href);
    filters.elements.date.value = url.searchParams.get('date') || 'all';
    filters.elements.q.value = url.searchParams.get('q') || '';
    filters.querySelector('input[type="checkbox"]').checked = url.searchParams.get('empty') !== '0';
    loadResults(url.href, false);
  });

  const modal = document.getElementById('appointment-modal');
  const content = modal.querySelector('.modal-content');
  let controller;

  function showError() {
    let error = content.querySelector('.appointments-modal-error');
    if (!error) {
      error = document.createElement('p');
      error.className = 'alert alert-danger appointments-modal-error';
      error.setAttribute('role', 'alert');
      (content.querySelector('.modal-body') || content).prepend(error);
    }
    error.textContent = modal.dataset.error;
  }

  results.addEventListener('click', async function (event) {
    const link = event.target.closest('.appointments-modal-link');
    if (!link) return;
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (controller) controller.abort();
    controller = new AbortController();
    content.replaceChildren();
    const loading = document.createElement('p');
    loading.className = 'modal-body';
    loading.textContent = modal.dataset.loading;
    content.append(loading);
    $(modal).modal('show');
    try {
      const response = await fetch(link.href, {
        headers: {'X-Requested-With': 'XMLHttpRequest'},
        signal: controller.signal
      });
      if (response.redirected) {
        window.location.assign(response.url);
        return;
      }
      if (!response.ok) throw new Error('Loading failed');
      content.innerHTML = await response.text();
      $(modal).modal('handleUpdate');
    } catch (error) {
      if (error.name !== 'AbortError') showError();
    }
  });

  content.addEventListener('submit', async function (event) {
    const form = event.target;
    if (!form.matches('form')) return;
    event.preventDefault();
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: {'X-Requested-With': 'XMLHttpRequest'},
        body: new FormData(form)
      });
      if (response.redirected) {
        window.location.assign(response.url);
        return;
      }
      if (!response.ok) throw new Error('Saving failed');
      if ((response.headers.get('Content-Type') || '').includes('application/json')) {
        const result = await response.json();
        if (!result.success) throw new Error('Saving failed');
        const url = new URL(window.location.href);
        if (result.deleted) url.searchParams.delete('page');
        window.location.assign(url.href);
      } else {
        content.innerHTML = await response.text();
        $(modal).modal('handleUpdate');
      }
    } catch (error) {
      showError();
    } finally {
      submit.disabled = false;
    }
  });
  $(modal).on('hidden.bs.modal', function () {
    if (controller) controller.abort();
  });
});
