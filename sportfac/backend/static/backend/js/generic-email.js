(function () {
  'use strict';
  if (!window.Jodit) return;

  function initialize(root) {
    root.querySelectorAll('textarea[data-richtext]').forEach(function (textarea) {
      if (textarea.dataset.richtextReady || textarea.name.includes('__prefix__')) return;
      textarea.dataset.richtextReady = '1';
      var checkbox = textarea.dataset.htmlToggle ? document.querySelector(textarea.dataset.htmlToggle) : null;
      var editor = null;
      var csrf = textarea.form.querySelector('[name=csrfmiddlewaretoken]');
      var upload = {
        url: textarea.dataset.uploadUrl || '',
        headers: csrf ? {'X-CSRFToken': csrf.value} : {},
        imagesExtensions: ['jpg', 'jpeg', 'png', 'gif', 'webp'],
        insertImageAsBase64URI: false
      };
      function sync() {
        if (!editor) return;
        // Commit the last debounced keystroke when submitting from Source mode.
        if (editor.getMode() !== Jodit.MODE_WYSIWYG) editor.setMode(Jodit.MODE_WYSIWYG);
        textarea.value = editor.value;
      }
      function updateEditor() {
        if ((!checkbox || checkbox.checked) && !editor) {
          editor = Jodit.make(textarea, {
            language: 'fr', height: 450,
            toolbarAdaptive: false, toolbarSticky: false,
            buttons: ['paragraph', 'bold', 'italic', 'underline', 'superscript', 'subscript', '|',
              'font', 'fontsize', 'brush', 'align', '|', 'ul', 'ol', 'link', 'image', 'table', 'hr', '|',
              'undo', 'redo', 'source'],
            sourceEditor: 'area', beautifyHTML: false,
            disablePlugins: ['powered-by-jodit', 'speech-recognize', 'ai-assistant'],
            showXPathInStatusbar: false,
            uploader: upload,
            filebrowser: {
              ajax: {url: textarea.dataset.browseUrl || '', method: 'GET'},
              uploader: upload,
              permissions: false,
              permissionsPresets: {
                allowFileUpload: true, allowFiles: true, allowFolders: true, allowFolderTree: true,
                allowFileRemove: false, allowFileRename: false, allowFileMove: false,
                allowFolderCreate: false, allowFolderRemove: false, allowFolderRename: false,
                allowFolderMove: false, allowImageCrop: false, allowImageResize: false,
                allowFileUploadRemote: false
              },
              buttons: ['filebrowser.upload', 'filebrowser.update', 'filebrowser.select', '|',
                'filebrowser.tiles', 'filebrowser.list', 'filebrowser.filter'],
              createNewFolder: false, moveFolder: false, moveFile: false
            }
          });
        } else if (checkbox && !checkbox.checked && editor) {
          sync();
          editor.destruct();
          editor = null;
        }
      }
      if (checkbox) checkbox.addEventListener('change', updateEditor);
      textarea.form.addEventListener('submit', sync);
      updateEditor();
    });
  }
  initialize(document);
  document.addEventListener('DOMContentLoaded', function () { initialize(document); });
  document.addEventListener('formset:added', function (event) { initialize(event.target); });
  if (window.django && window.django.jQuery) {
    window.django.jQuery(document).on('formset:added', function (event, row) {
      if (row) initialize(row[0]);
    });
  }
}());
