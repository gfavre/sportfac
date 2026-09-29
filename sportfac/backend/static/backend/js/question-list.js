(function () {
    "use strict";
    var search = document.getElementById("question-search");
    if (!search) return;
    var clear = document.getElementById("clear-question-search");
    function normalize(value) {
        return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase();
    }
    var rows = Array.from(document.querySelectorAll("[data-question-row]")).map(function (row) {
        return {element: row, text: normalize(row.cells[0].textContent + " " + row.cells[1].textContent)};
    });
    function filter() {
        var words = normalize(search.value).trim().split(/\s+/).filter(Boolean);
        var visible = 0;
        rows.forEach(function (row) {
            var matches = words.every(function (word) { return row.text.indexOf(word) !== -1; });
            row.element.style.display = matches ? "" : "none";
            if (matches) visible++;
        });
        clear.hidden = search.value.length === 0;
        document.getElementById("no-matching-questions").hidden = visible !== 0;
    }
    search.addEventListener("input", filter);
    clear.addEventListener("click", function () {
        search.value = "";
        filter();
        search.focus();
    });
    document.getElementById("question-search-tools").hidden = false;
    filter();
}());
