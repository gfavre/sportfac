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
    var courseSearch = document.getElementById("course-filter");
    var courseList = document.getElementById("question-courses");
    var selectedOnly = false;
    function updateCourses() {
        var query = courseSearch.value.toLocaleLowerCase().trim();
        var selected = 0, displayed = 0, hiddenSelected = 0;
        courseList.querySelectorAll(".checkbox").forEach(function (row) {
            var checked = row.querySelector('input[type="checkbox"]').checked;
            row.hidden = (selectedOnly && !checked) || row.textContent.toLocaleLowerCase().indexOf(query) === -1;
            if (checked) selected++;
            if (!row.hidden) displayed++;
            if (checked && row.hidden) hiddenSelected++;
        });
        document.getElementById("selected-course-count").textContent = selected;
        document.getElementById("selected-filter-count").textContent = selected;
        document.getElementById("displayed-course-count").textContent = displayed;
        document.getElementById("hidden-course-count").textContent = hiddenSelected;
        document.getElementById("hidden-course-selection").hidden = hiddenSelected === 0;
        document.getElementById("no-matching-courses").hidden = displayed !== 0;
        ["show-all-courses", "show-selected-courses"].forEach(function (id, index) {
            var active = index === (selectedOnly ? 1 : 0);
            var button = document.getElementById(id);
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });
    }
    function filterCourses(onlySelected) {
        selectedOnly = onlySelected;
        updateCourses();
        courseList.scrollTop = 0;
    }
    courseSearch.addEventListener("input", function () { filterCourses(selectedOnly); });
    courseList.addEventListener("change", updateCourses);
    document.getElementById("show-all-courses").addEventListener("click", function () { filterCourses(false); });
    document.getElementById("show-selected-courses").addEventListener("click", function () { filterCourses(true); });
    document.getElementById("show-course-selection").addEventListener("click", function () {
        courseSearch.value = "";
        filterCourses(true);
        document.getElementById("show-selected-courses").focus();
    });
    document.getElementById("course-selection-tools").hidden = false;
    document.getElementById("course-filter-status").hidden = false;
    updateCourses();
    var answerRows = document.getElementById("answer-rows");
    var draggedAnswer = null;
    var dragPreview = null;
    var dragOffset = 0;
    answerRows.addEventListener("pointerdown", function (event) {
        var handle = event.target.closest(".answer-drag-handle");
        if (!handle || event.button !== 0 || !event.isPrimary) return;
        event.preventDefault();
        draggedAnswer = handle.closest("tr");
        var bounds = draggedAnswer.getBoundingClientRect();
        dragOffset = event.clientY - bounds.top;
        dragPreview = document.createElement("table");
        dragPreview.className = "table content answer-drag-preview";
        dragPreview.setAttribute("aria-hidden", "true");
        dragPreview.style.width = bounds.width + "px";
        dragPreview.style.left = bounds.left + "px";
        dragPreview.style.top = bounds.top + "px";
        var previewBody = document.createElement("tbody");
        var previewRow = draggedAnswer.cloneNode(true);
        previewRow.querySelectorAll("[id], [name]").forEach(function (element) {
            element.removeAttribute("id");
            element.removeAttribute("name");
        });
        previewRow.querySelectorAll("input, button").forEach(function (element) { element.tabIndex = -1; });
        Array.from(previewRow.cells).forEach(function (cell, index) {
            cell.style.width = draggedAnswer.cells[index].getBoundingClientRect().width + "px";
        });
        previewBody.appendChild(previewRow);
        dragPreview.appendChild(previewBody);
        document.body.appendChild(dragPreview);
        draggedAnswer.classList.add("answer-dragging");
        answerRows.setPointerCapture(event.pointerId);
    });
    answerRows.addEventListener("pointermove", function (event) {
        if (!draggedAnswer) return;
        dragPreview.style.top = (event.clientY - dragOffset) + "px";
        var siblings = Array.from(answerRows.children).filter(function (row) { return row !== draggedAnswer; });
        var before = siblings.find(function (row) {
            var bounds = row.getBoundingClientRect();
            return event.clientY < bounds.top + bounds.height / 2;
        });
        if (before !== draggedAnswer.nextElementSibling) answerRows.insertBefore(draggedAnswer, before || null);
        if (event.clientY < 60) window.scrollBy(0, -20);
        else if (event.clientY > window.innerHeight - 60) window.scrollBy(0, 20);
    });
    function finishAnswerDrag() {
        if (!draggedAnswer) return;
        draggedAnswer.classList.remove("answer-dragging");
        dragPreview.remove();
        dragPreview = null;
        draggedAnswer = null;
        updateAnswerOrder();
    }
    answerRows.addEventListener("pointerup", finishAnswerDrag);
    answerRows.addEventListener("pointercancel", finishAnswerDrag);
    answerRows.addEventListener("lostpointercapture", finishAnswerDrag);
    function updateAnswerOrder() {
        var rows = Array.from(answerRows.children);
        rows.forEach(function (row, index) {
            // Keep each answer, price and deletion flag together in Django's posted formset.
            row.querySelectorAll("*").forEach(function (element) {
                ["name", "id", "for", "aria-describedby"].forEach(function (attribute) {
                    var value = element.getAttribute(attribute);
                    if (value) element.setAttribute(attribute, value.replace(/answers-\d+-/g, "answers-" + index + "-"));
                });
            });
        });
    }
    answerRows.addEventListener("keydown", function (event) {
        var button = event.target.closest(".answer-drag-handle");
        if (!button || (event.key !== "ArrowUp" && event.key !== "ArrowDown")) return;
        event.preventDefault();
        var row = button.closest("tr");
        var sibling = event.key === "ArrowUp" ? row.previousElementSibling : row.nextElementSibling;
        if (!sibling) return;
        if (event.key === "ArrowUp") answerRows.insertBefore(row, sibling);
        else answerRows.insertBefore(sibling, row);
        updateAnswerOrder();
        button.focus();
    });
    document.getElementById("add-answer").addEventListener("click", function () {
        var total = document.getElementById("id_answers-TOTAL_FORMS");
        if (Number(total.value) >= 100) return;
        var html = document.getElementById("answer-template").innerHTML.replace(/__prefix__/g, total.value);
        document.getElementById("answer-rows").insertAdjacentHTML("beforeend", html);
        total.value = Number(total.value) + 1;
        updateAnswerOrder();
    });
    updateAnswerOrder();
    updateType();
}());
