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

  async function saveForm(form) {
        const formData = new FormData(form);
        const id = formData.get('id');  // Get the ID from the form data if it exists

        let url = '/api/extra-info/';
        let method = 'POST';

        // If the form has an existing ID, use PUT to update the record
        if (id) {
            url = `/api/extra-info/${id}/`;
            method = 'PUT';
        }

        try {
            const response = await fetch(url, {
                method: method,
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                }
            });

            const data = await response.json();

            if (data.success) {
                console.log('Form saved successfully');
                if (!id) {
                    form.querySelector('[name="id"]').value = data.extra_info_id;  // Update ID in form if it was a new record
                }
            } else {
                console.error('Form save failed:', data.errors);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

  async function saveAllForms() {
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
            window.location.href = '/wizard2/next-step/';  // Adjust this URL to the next step in your wizard
        } else {
            alert('Please fix the errors in the forms before proceeding.');
        }
    }

    // Add event listener to the "Save and Next" button
    document.getElementById('save-next-button').addEventListener('click', saveAllForms);


    // Initialize form toggles and drag-and-drop functionality
  initializeFormToggles();
});
