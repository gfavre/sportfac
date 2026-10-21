(function ($) {
    'use strict';
    $(function () {
        var form = $('#registration-create');
        if (!form.length) { return; }
        var child = form.find('[name="child"]');
        var container = $('#registration-course');
        var submit = $('#registration-submit');
        var error = $('#registration-course-error');
        var pending = null;

        child.on('change', function () {
            if (pending) { pending.abort(); }
            error.prop('hidden', true);
            container.attr('aria-busy', 'true');
            container.find('select').prop('disabled', true);
            submit.prop('disabled', true);
            pending = $.ajax({
                url: form.data('courses-url'),
                data: {courses: '1', child: child.val() || ''},
                dataType: 'html'
            }).done(function (html) {
                // A login redirect is a full page, never a valid course fragment.
                if (html.indexOf('name="course"') === -1) {
                    error.prop('hidden', false);
                    return;
                }
                container.find('.django-select2').select2('destroy');
                container.html(html);
                container.find('.django-select2').djangoSelect2();
                submit.prop('disabled', !child.val());
            }).fail(function (xhr, status) {
                if (status !== 'abort') { error.prop('hidden', false); }
            }).always(function () {
                container.attr('aria-busy', 'false');
            });
        });
    });
}(jQuery));
