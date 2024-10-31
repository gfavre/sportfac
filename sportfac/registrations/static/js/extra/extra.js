document.addEventListener('DOMContentLoaded', function () {
    // Function to initialize drag-and-drop on all forms and toggle image visibility
    function initializeFormToggles() {
        const valueFields = document.querySelectorAll('[data-value-field]');

        valueFields.forEach((valueField) => {
            const uniqueId = valueField.getAttribute('data-value-field');
            const imageField = document.querySelector(`[data-image-field="${uniqueId}"]`);
            const dropArea = document.querySelector(`[data-drop-area="${uniqueId}"]`);
            const fileInput = document.querySelector(`[data-file-input="${uniqueId}"]`);
            const imagePreview = document.querySelector(`[data-image-preview="${uniqueId}"]`);

            if (imageField && dropArea && fileInput && imagePreview) {
                // Initial toggle based on the initial value of the field
                toggleImageField(valueField, imageField, dropArea);

                // Add event listener for changes in the value field
                valueField.addEventListener('change', () => toggleImageField(valueField, imageField, dropArea));

                // Set up drag and drop for this specific form
                setupDragAndDrop(dropArea, fileInput, imagePreview);
            }
        });
    }

    function toggleImageField(valueField, imageField, dropArea) {
        const showImage = ['True', 'true', 'YES', 'Yes', 'yes', 'OUI', 'Oui', 'oui', '1'].includes(valueField.value);

        if (showImage) {
            imageField.closest('.form-group').style.display = 'block';
            dropArea.style.display = 'block';  // Show the drop area when value is set
        } else {
            imageField.closest('.form-group').style.display = 'none';
            dropArea.style.display = 'none';
        }
    }

    function setupDragAndDrop(dropArea, fileInput, imagePreview) {
        dropArea.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', (e) => handleFiles(e.target.files, imagePreview));

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('hover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('hover'), false);
        });

        dropArea.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            fileInput.files = files;  // Update the file input
            handleFiles(files, imagePreview);
        });
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function handleFiles(files, imagePreview) {
        const file = files[0];
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onloadend = () => {
                imagePreview.src = reader.result;
                imagePreview.style.display = 'block';  // Show the image preview
            };
        }
    }

    function highlightInvalidFields(form, errors) {
        // Get the form's prefix from one of the fields (e.g., the hidden id field)
        const idField = form.querySelector('[name$="-id"]');  // Select the field that ends with '-id'
        const prefix = idField ? idField.name.replace('-id', '') : '';  // Extract the prefix from the field name

        clearInvalidFeedback(form);  // Clear any previous invalid highlights

        let firstInvalidField = null;

        // Iterate through errors and apply `is-invalid` class to fields
        for (const [fieldName, errorMessages] of Object.entries(errors)) {
            // Add the prefix to match the form field name (with prefix)
            const prefixedFieldName = `${prefix}-${fieldName}`;

            const field = form.querySelector(`[name="${prefixedFieldName}"]`);
            if (field) {
                field.classList.add('is-invalid');
                field.parentNode.parentNode.classList.add('has-error');

                // Add or display error message
                let errorFeedback = field.nextElementSibling;
                if (errorFeedback && errorFeedback.classList.contains('help-block')) {
                    errorFeedback.textContent = errorMessages.join(', ');
                } else {
                    const newFeedback = document.createElement('div');
                    newFeedback.classList.add('help-block');
                    newFeedback.textContent = errorMessages.join(', ');
                    field.parentNode.insertBefore(newFeedback, field.nextSibling);
                }

                // Focus on the first invalid field
                if (!firstInvalidField) {
                    firstInvalidField = field;
                }
            }
        }
        // Focus on the first invalid field
        if (firstInvalidField) {
            firstInvalidField.focus();
        }

    }

    function clearInvalidFeedback(form) {
        // Remove all invalid field highlights and feedback messages
        const invalidFields = form.querySelectorAll('.is-invalid');
        invalidFields.forEach((field) => {
            field.classList.remove('is-invalid');
            field.parentNode.parentNode.classList.remove('has-error');
            const feedback = field.nextElementSibling;
            if (feedback && feedback.classList.contains('help-block')) {
                feedback.textContent = '';
            }
        });

        // Remove the alert
        removeAlert();
    }

    function displayAlert() {
        const alertNode = document.getElementById('alert-container');
        alertNode.style.display = 'block';
    }

    function removeAlert() {
        const alertNode = document.getElementById('alert-container');
        alertNode.style.display = 'none';
    }


    async function saveForm(form) {
        const formData = new FormData(form);

        const idField = form.querySelector('[name$="-id"]');  // Select the field that ends with '-id'
        const prefix = idField ? idField.name.replace('-id', '') : '';  // Extract the prefix from the field name

        // Create a new FormData object without the prefix in the field names
        const cleanedFormData = new FormData();
        // Loop through the original form data and strip the prefix from each field name
        formData.forEach((value, key) => {
            const cleanedKey = key.replace(`${prefix}-`, '');  // Strip the prefix
            cleanedFormData.append(cleanedKey, value);
        });

        const id = cleanedFormData.get('id');  // Get the id using the prefixed field name

        let url = '/api/extra-infos/';
        let method = 'POST';

        // If the form has an existing ID, use PUT to update the record
        if (id) {
            url = `/api/extra-infos/${id}/`;
            method = 'PUT';
        }

        try {
            const response = await fetch(url, {
                method: method,
                body: cleanedFormData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                }
            });

            const data = await response.json();

            if (data.success) {
                if (!id) {
                    form.querySelector('[name="id"]').value = data.extra_info_id;  // Update ID in form if it was a new record
                }
                clearInvalidFeedback(form);  // Clear any previous invalid highlights
                return true;
            } else {
                highlightInvalidFields(form, data.errors);  // Highlight invalid fields
                return false;
            }
        } catch (error) {
            /* our data is invalid */
            return false;
        }
    }

    async function saveAllForms(event) {
        event.preventDefault();
        const button = event.currentTarget; // This will always refer to the button element
        const url = button.getAttribute('data-url');
        const forms = document.querySelectorAll('.form-wrapper form');
        let allValid = true;

        for (const form of forms) {
            const isValid = await saveForm(form);
            if (!isValid) {
                allValid = false;
            }
        }
        if (allValid) {
            window.location.href = url;
        } else {
            displayAlert();
        }
    }

    // Add event listener to the "Save and Next" button
    document.getElementById('save-next-button').addEventListener('click', saveAllForms);


    // Initialize form toggles and drag-and-drop functionality
    initializeFormToggles();
});
