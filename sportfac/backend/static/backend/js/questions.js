(function () {
    "use strict";
    var form = document.getElementById("question-form");
    if (!form) return;
    var type = document.getElementById("id_type");
    function updateType() {
        var binary = type.value === "B" || type.value === "IM";
        document.getElementById("boolean-prices").hidden = !binary;
        document.getElementById("choice-prices").hidden = binary;
        document.getElementById("image-question").hidden = type.value !== "IM";
        // Hidden answer inputs must not trigger native required validation.
        document.querySelectorAll("#choice-prices input:not([type=hidden])").forEach(function (input) {
            input.disabled = binary;
        });
    }
    type.addEventListener("change", updateType);
    document.getElementById("course-filter").addEventListener("input", function (event) {
        var query = event.target.value.toLocaleLowerCase().trim();
        document.querySelectorAll("#question-courses .checkbox").forEach(function (row) {
            row.hidden = row.textContent.toLocaleLowerCase().indexOf(query) === -1;
        });
    });
    document.getElementById("add-answer").addEventListener("click", function () {
        var total = document.getElementById("id_answers-TOTAL_FORMS");
        if (Number(total.value) >= 100) return;
        var html = document.getElementById("answer-template").innerHTML.replace(/__prefix__/g, total.value);
        document.getElementById("answer-rows").insertAdjacentHTML("beforeend", html);
        total.value = Number(total.value) + 1;
    });
    updateType();
}());
