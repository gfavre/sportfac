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
    clearInvalidFeedback(form);  // Clear any previous invalid highlights

    let firstInvalidField = null;

    // Iterate through errors and apply `is-invalid` class to fields
    for (const [fieldName, errorMessages] of Object.entries(errors)) {
      const field = form.querySelector(`[name="${fieldName}"]`);
      if (field) {
        field.classList.add('is-invalid');

        // Add or display error message
        let errorFeedback = field.nextElementSibling;
        if (errorFeedback && errorFeedback.classList.contains('invalid-feedback')) {
          errorFeedback.textContent = errorMessages.join(', ');
        } else {
          const newFeedback = document.createElement('div');
          newFeedback.classList.add('invalid-feedback');
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

    // Show the alert at the top
    displayAlert('There are errors in the form. Please fix them before proceeding.');
  }

  function clearInvalidFeedback(form) {
    // Remove all invalid field highlights and feedback messages
    const invalidFields = form.querySelectorAll('.is-invalid');
    invalidFields.forEach((field) => {
      field.classList.remove('is-invalid');
      const feedback = field.nextElementSibling;
      if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.textContent = '';
      }
    });

    // Remove the alert
    removeAlert();
  }

  function displayAlert(message) {
    // Check if the alert already exists, if not, create it
    let alertDiv = document.querySelector('.alert-danger');
    if (!alertDiv) {
      alertDiv = document.createElement('div');
      alertDiv.classList.add('alert', 'alert-danger', 'alert-dismissible');
      alertDiv.setAttribute('role', 'alert');
      alertDiv.innerHTML = `
                <strong>Error!</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
      const formWrapper = document.getElementById('alert-container');
      formWrapper.parentNode.insertBefore(alertDiv, formWrapper);
    } else {
      alertDiv.querySelector('strong').textContent = 'Error!';
      alertDiv.querySelector('span').textContent = message;
    }
  }

  function removeAlert() {
    const alertDiv = document.querySelector('.alert-danger');
    if (alertDiv) {
      alertDiv.remove();
    }
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
      console.error('Error:', error);
      return false;
    }
  }

  async function saveAllForms(event) {
    event.preventDefault();
    const forms = document.querySelectorAll('.form-wrapper form');
    let allValid = true;

    for (const form of forms) {
      const isValid = await saveForm(form);
      if (!isValid) {
        allValid = false;
        break;
      }
    }

    // If all forms are saved successfully, navigate to the next page
    if (allValid) {
      window.location.href = event.target.href;  // Manually follow the link
    }
  }

  // Add event listener to the "Save and Next" button
  document.getElementById('save-next-button').addEventListener('click', saveAllForms);


  // Initialize form toggles and drag-and-drop functionality
  initializeFormToggles();
});
