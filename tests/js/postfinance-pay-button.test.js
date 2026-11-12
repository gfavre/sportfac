const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

async function setup(t) {
    const dom = new JSDOM(`
      <a href="#" id="pay-button">Pay</a>
      <span id="pay-loading" style="display:none">Connecting</span>
      <p id="pay-error" role="alert" hidden data-unavailable="Temporarily unavailable" data-error="Cannot open payment"></p>
    `, {url: 'https://example.test/hiver/wizard/steps/payment/', runScripts: 'outside-only'});
    t.after(() => dom.window.close());
    const w = dom.window;
    w.eval(fs.readFileSync('sportfac/static/js/vendor/jquery-2.1.1.js', 'utf8'));
    w.Cookies = {get: () => 'csrf'};
    const requests = [];
    w.$.post = (url, data) => {
        const deferred = w.$.Deferred();
        requests.push({url, data, deferred});
        return deferred.promise();
    };
    const template = fs.readFileSync('sportfac/payments/templates/payments/postfinance_pay_button.html', 'utf8');
    const script = template.match(/<script type="text\/javascript">([\s\S]*?)<\/script>/)[1]
        .replace(/{% url [\s\S]*?%}/g, '/hiver/postfinance/new-transaction/407/');
    w.eval(script);
    await new Promise(resolve => w.$(resolve));
    return {w, requests, click: () => w.$('#pay-button').trigger('click')};
}

test('temporary network failure displays an accessible message and permits explicit retry', async t => {
    const {w, requests, click} = await setup(t);
    click();
    assert.equal(w.$('#pay-button').css('display'), 'none');
    requests[0].deferred.reject({status: 503, responseJSON: {detail: 'sensitive exception'}});
    assert.notEqual(w.$('#pay-button').css('display'), 'none');
    assert.equal(w.$('#pay-loading').css('display'), 'none');
    assert.equal(w.document.getElementById('pay-error').hidden, false);
    assert.equal(w.$('#pay-error').text(), 'Temporarily unavailable');
    assert.equal(requests.length, 1);
    click();
    assert.equal(requests.length, 2);
    assert.equal(w.document.getElementById('pay-error').hidden, true);
    assert.equal(requests[1].data.fail_url, w.location.href);
});

test('unexpected server errors show a generic message without exposing the response', async t => {
    const {w, requests, click} = await setup(t);
    click();
    requests[0].deferred.reject({status: 500, responseText: 'sensitive traceback'});
    assert.equal(w.$('#pay-error').text(), 'Cannot open payment');
});

test('failure to download checkout script releases the button without creating another transaction', async t => {
    const {w, requests, click} = await setup(t);
    click();
    requests[0].deferred.resolve({paymentPageUrl: 'https://checkout.postfinance.ch/lightbox.js'});
    w.document.querySelector('script[src]').onerror();
    assert.notEqual(w.$('#pay-button').css('display'), 'none');
    assert.equal(w.$('#pay-error').text(), 'Temporarily unavailable');
    assert.equal(requests.length, 1);
});

test('successful response still opens the PostFinance lightbox', async t => {
    const {w, requests, click} = await setup(t);
    let opened = 0;
    w.LightboxCheckoutHandler = {startPayment: () => opened++};
    click();
    requests[0].deferred.resolve({paymentPageUrl: 'https://checkout.postfinance.ch/lightbox.js'});
    w.document.querySelector('script[src]').onload();
    assert.equal(opened, 1);
    assert.equal(w.document.getElementById('pay-error').hidden, true);
});
