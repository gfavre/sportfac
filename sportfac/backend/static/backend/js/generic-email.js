(function () {
  'use strict';
  var checkbox = document.getElementById('id_is_html');
  var textarea = document.getElementById('id_body_text');
  if (!checkbox || !textarea || !window.Jodit) return;
  var editor = null;
  function sync() {
    if (!editor) return;
    // Commit source mode immediately, including its debounced final keystroke.
    if (editor.getMode() !== Jodit.MODE_WYSIWYG) editor.setMode(Jodit.MODE_WYSIWYG);
    textarea.value = editor.value;
  }
  function updateEditor() {
    if (checkbox.checked && !editor) {
      editor = Jodit.make(textarea, {
        language: 'fr',
        height: 450,
        toolbarAdaptive: false,
        toolbarSticky: false,
        buttons: ['bold', 'italic', 'underline', '|', 'ul', 'ol', '|', 'link', 'image', 'table', '|', 'undo', 'redo', 'source'],
        sourceEditor: 'area',
        beautifyHTML: false,
        // Disable plugins that load external assets. Templates remain ordinary,
        // visible text: hiding Django tokens made staff think they were missing.
        disablePlugins: ['powered-by-jodit', 'speech-recognize', 'ai-assistant'],
        showXPathInStatusbar: false,
        uploader: {url: ''},
        filebrowser: {ajax: {url: ''}}
      });
    } else if (!checkbox.checked && editor) {
      sync();
      editor.destruct();
      editor = null;
    }
  }
  checkbox.addEventListener('change', updateEditor);
  textarea.form.addEventListener('submit', sync);
  updateEditor();
}());
