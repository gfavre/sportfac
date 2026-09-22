/* Standalone admin widget: no legacy frontend bundle required. */
(function () {
  "use strict";
  function initialize(root) {
    const value = root.querySelector("[data-columns-value]");
    const rows = root.querySelector("[data-columns-rows]");
    function sync() {
      value.value = JSON.stringify(Array.from(rows.children, function (row) {
        const mappings = Object.create(null);
        row.querySelectorAll("[data-mapping]").forEach(function (mapping) {
          const stored = mapping.querySelector("[data-stored]");
          stored.setCustomValidity(Object.hasOwn(mappings, stored.value) ? "Cette valeur possède déjà une correspondance." : "");
          mappings[stored.value] = mapping.querySelector("[data-displayed]").value;
        });
        return {question: row.querySelector("[data-question]").value, label: row.querySelector("[data-label]").value, values: mappings};
      }));
    }
    function addMapping(row, stored, displayed) {
      const mapping = root.querySelector("[data-mapping-template]").content.firstElementChild.cloneNode(true);
      mapping.querySelector("[data-stored]").value = stored;
      mapping.querySelector("[data-displayed]").value = displayed;
      mapping.querySelector("[data-remove-mapping]").onclick = function () { mapping.remove(); sync(); };
      row.querySelector("[data-mappings]").appendChild(mapping);
    }
    function addColumn(column) {
      const row = root.querySelector("[data-column-template]").content.firstElementChild.cloneNode(true);
      const select = row.querySelector("[data-question]");
      if (column.question && !Array.from(select.options).some(function (option) { return option.value === column.question; })) {
        select.add(new Option(column.question + " (absente de cette période)", column.question));
      }
      select.value = column.question || "";
      row.querySelector("[data-label]").value = column.label || "";
      Object.entries(column.values || {}).forEach(function (pair) { addMapping(row, pair[0], pair[1]); });
      row.querySelector("[data-add-mapping]").onclick = function () { addMapping(row, "", ""); sync(); };
      row.querySelector("[data-remove-column]").onclick = function () { row.remove(); sync(); };
      row.querySelector("[data-up]").onclick = function () { if (row.previousElementSibling) rows.insertBefore(row, row.previousElementSibling); sync(); };
      row.querySelector("[data-down]").onclick = function () { if (row.nextElementSibling) rows.insertBefore(row.nextElementSibling, row); sync(); };
      rows.appendChild(row);
    }
    let columns;
    try {
      columns = JSON.parse(value.value || "[]");
      if (!Array.isArray(columns)) columns = Object.entries(columns).map(function (pair) { return {label: pair[0], question: pair[1], values: {}}; });
      columns.forEach(addColumn);
    } catch (error) {
      value.hidden = false;
      root.querySelector("[data-add-column]").disabled = true;
      return; // Preserve malformed existing data for correction, never silently erase it.
    }
    root.addEventListener("input", sync);
    root.addEventListener("change", sync);
    root.querySelector("[data-add-column]").onclick = function () { addColumn({}); sync(); };
    if (root.closest("form")) root.closest("form").addEventListener("submit", sync);
  }
  function start() { document.querySelectorAll(".attendance-extra-columns").forEach(initialize); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
}());
