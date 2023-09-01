$(function () {
    $('.multidateinput').datepicker({
      multidate: true,
      multidateSeparator: ',',
      language: 'fr',
      format: "dd.mm.yyyy",
      weekStart: "1",
      todayHighlight: true,
    });
  });