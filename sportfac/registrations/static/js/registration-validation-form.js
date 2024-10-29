document.addEventListener("DOMContentLoaded", function() {
    const form = document.querySelector("#registration-validation-form");
    const checkbox = form.querySelector("[name='consent_given']");
    const tooltipMessage = form.getAttribute("data-tooltip-message");

    form.addEventListener("submit", function(event) {
        if (!checkbox.checked) {
            event.preventDefault();
            checkbox.classList.add("highlight-checkbox");
            checkbox.setAttribute("title", "Vous devez cocher cette case pour continuer.");

            const tooltip = document.createElement("div");
            tooltip.className = "tooltip auto bottom";
            tooltip.setAttribute("role", "tooltip");

            const arrow = document.createElement("div");
            arrow.className = "tooltip-arrow";

            const inner = document.createElement("div");
            inner.className = "tooltip-inner";
            inner.textContent = tooltipMessage;

            tooltip.appendChild(arrow);
            tooltip.appendChild(inner);
            checkbox.parentNode.appendChild(tooltip);

            // Remove tooltip after a few seconds
            /*setTimeout(() => {
            #    checkbox.classList.remove("highlight-checkbox");
                if (tooltip) {
                    tooltip.remove();
                }
            }, 3000);*/
        }
    });
});
