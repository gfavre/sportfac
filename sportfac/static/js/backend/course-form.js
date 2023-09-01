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

  $('#id_price').on('change', function () {
    $id_price_local = $("#id_price_local");
    if ($id_price_local.val() == '') {
      $id_price_local.val($(this).val())
    }
    $id_price_family = $("#id_price_family");
    if ($id_price_family.val() == '') {
      $id_price_family.val($(this).val())
    }
    $id_price_local_family = $("#id_price_local_family");
    if ($id_price_local_family.val() == '') {
      $id_price_local_family.val($(this).val())
    }
  });
  $type.on('change', function () {
    updateFields();
  })
  updateFields();

});