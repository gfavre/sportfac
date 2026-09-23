const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

const template = fs.readFileSync('sportfac/absences/templates/absences/absences-table.html', 'utf8');
const start = template.indexOf("$absences.on('submit', 'form.session-form'");
const end = template.indexOf("$absences.on('click', '.edit-session .session-delete'", start);
const script = template.slice(start, end).replace(/{% translate "([^"]*)" %}/g, '$1');

test('saving Other clears the displayed instructor and allows assigning another one', () => {
    const dom = new JSDOM(`<table id="absences"><tr><th class="edit-session" data-instructor="7" data-url="/sessions/1/">
      <abbr title="Ancien moniteur">AM</abbr><span class="has-popover"></span>
      <form class="session-form"><select name="instructor"><option value="">Other</option>
      <option value="8">Nouveau moniteur</option></select></form>
      </th></tr><tr><td class="date" data-session="1"><span class="session-date"></span></td></tr></table>`,
      {runScripts: 'outside-only'});
    const {window} = dom;
    window.eval(fs.readFileSync('sportfac/static/js/vendor/jquery-2.1.1.js', 'utf8'));
    const $ = window.jQuery;
    window.$absences = $('#absences');
    window.API_FMT = 'YYYY-MM-DD';
    window.HUMAN_FMT = 'DD.MM.YYYY';
    window.moment = () => ({format: () => '23.09.2026'});
    $.fn.popover = function () { return this; };
    let instructor = null;
    $.ajax = options => {
        assert.equal(options.type, 'PATCH');
        assert.equal(options.data.instructor, instructor ? '8' : '');
        options.success({id: 1, date: '2026-09-23', instructor});
    };
    window.eval(script);
    $('form').trigger('submit');
    assert.equal($('abbr').text(), 'n/a');
    assert.equal($('abbr').attr('title'), 'Unknown instructor');
    assert.equal($('.edit-session').data('instructor'), null);
    instructor = {id: 8, initials: 'NM', full_name: 'Nouveau moniteur'};
    $('select').val('8');
    $('form').trigger('submit');
    assert.equal($('abbr').text(), 'NM');
    assert.equal($('abbr').attr('title'), 'Nouveau moniteur');
    assert.equal($('.edit-session').data('instructor'), 8);
    dom.window.close();
});
