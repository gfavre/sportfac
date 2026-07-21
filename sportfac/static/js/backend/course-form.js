$(function () {
  let $type = $('#id_course_type')

  let updateFields = function () {
    switch ($type.val()) {
      case 'course':
        $('.course-visible').show();
        $('.course-hidden').hide();
        break;
      case 'multicourse':
        $('.multicourse-visible').show();
        $('.multicourse-hidden').hide();
        break;
      case 'camp':
        $('.camp-visible').show();
        $('.camp-hidden').hide();
        break;
    }
  }

  $type.on('change', function () {
    updateFields();
  })
  updateFields();

});
