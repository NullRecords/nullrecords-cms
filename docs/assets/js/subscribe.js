/**
 * NullRecords — Shared Email Subscription Handler
 *
 * Tries the AI-Engine CRM first (localhost or deployed).
 * Falls back to formsubmit.co so the admin gets an email notification
 * even on the static GitHub Pages site.
 * Each fetch has a 5-second timeout so the form never hangs.
 */
(function () {
  'use strict';

  var CRM_URL  = 'http://localhost:8008/crm/subscribe';
  var FORM_URL = 'https://formsubmit.co/ajax/hello@nullrecords.com';
  var TIMEOUT  = 5000;

  function timedFetch(url, opts) {
    var ctrl  = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, TIMEOUT);
    return fetch(url, Object.assign({}, opts, { signal: ctrl.signal }))
      .finally(function () { clearTimeout(timer); });
  }

  async function submitEmail(email, source) {
    /* 1 — AI-Engine CRM (works when running locally or deployed) */
    try {
      var r = await timedFetch(CRM_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, source: source }),
      });
      if (r.ok) return true;
    } catch (_) { /* CRM not reachable */ }

    /* 2 — formsubmit.co (sends notification email to admin) */
    try {
      var r2 = await timedFetch(FORM_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          email: email,
          source: source,
          _subject: 'New Subscriber: ' + email,
          _template: 'table',
        }),
      });
      if (r2.ok) return true;
    } catch (_) { /* also unreachable */ }

    return false;
  }

  function handleSubmit(e) {
    e.preventDefault();
    var form   = e.target;
    var btn    = form.querySelector('button[type="submit"]');
    var orig   = btn.textContent;
    var source = form.getAttribute('data-source') || 'website';
    var email  = form.querySelector('input[name="email"]').value.trim();

    btn.textContent = 'Subscribing\u2026';
    btn.disabled = true;

    submitEmail(email, source).then(function (ok) {
      btn.textContent = orig;
      btn.disabled = false;
      if (ok) {
        form.innerHTML =
          '<p style="color:#00ff41;font-size:0.9rem;">' +
          'You\u2019re in! Check your inbox for the free lossless track.</p>';
      } else {
        form.innerHTML =
          '<p style="color:#fbbf24;font-size:0.85rem;">' +
          'Trouble subscribing? Email ' +
          '<a href="mailto:hello@nullrecords.com?subject=Subscribe&body=Please add me to the mailing list."' +
          ' style="color:#00bfff;text-decoration:underline;">hello@nullrecords.com</a>' +
          ' and we\u2019ll add you.</p>';
      }
    });
  }

  /* Auto-bind every <form data-subscribe> on the page */
  document.addEventListener('DOMContentLoaded', function () {
    var forms = document.querySelectorAll('form[data-subscribe]');
    for (var i = 0; i < forms.length; i++) {
      forms[i].addEventListener('submit', handleSubmit);
    }
  });
})();
