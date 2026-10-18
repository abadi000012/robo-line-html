/* Optional analytics are off until an affirmative choice; no account data is stored here. */
(function () {
  'use strict';
  var key = 'site_privacy_choice_v1', age = 180 * 86400000, choice = null, loaded = false;
  try {
    var saved = JSON.parse(localStorage.getItem(key) || 'null');
    if (saved && Date.now() - saved.time < age && ['accepted', 'rejected'].includes(saved.value)) choice = saved.value;
  } catch (_) {}
  window.SitePrivacy = { allowed: function () { return choice === 'accepted'; } };
  function clearOptionalStorage() {
    ['website_source_v1', 'luniru_tk', 'luniru_ttclid'].forEach(function (name) {
      try { localStorage.removeItem(name); } catch (_) {}
    });
    document.cookie.split(';').forEach(function (entry) {
      var name = entry.split('=')[0].trim();
      if (!/^(?:_ga|_gid|_gat|_gcl|_ttp|_tt_|ttcsid|website_source_v1)/.test(name)) return;
      var parts = location.hostname.split('.');
      document.cookie = name + '=; Max-Age=0; Path=/';
      for (var i = 0; i < parts.length - 1; i++) {
        document.cookie = name + '=; Max-Age=0; Path=/; Domain=' + parts.slice(i).join('.');
      }
    });
  }
  async function activate() {
    if (loaded || choice !== 'accepted') return;
    loaded = true;
    for (var old of document.querySelectorAll('script[data-optional-tracking]')) {
      var script = document.createElement('script');
      for (var attr of old.attributes) {
        if (!['type', 'data-optional-tracking', 'data-src', 'async', 'defer'].includes(attr.name)) script.setAttribute(attr.name, attr.value);
      }
      if (old.dataset.src) {
        script.src = old.dataset.src;
        script.async = false;
        await new Promise(function (resolve) {
          script.onload = resolve; script.onerror = resolve;
          document.head.appendChild(script);
        });
      } else {
        script.textContent = old.textContent;
        document.head.appendChild(script);
      }
    }
  }
  function show() {
    if (document.getElementById('privacy-choice')) return;
    var box = document.createElement('section');
    box.id = 'privacy-choice'; box.dir = 'rtl'; box.setAttribute('aria-label', 'اختيارات الخصوصية');
    box.innerHTML = '<p><strong>خصوصيتك واختيارك</strong><br>نستخدم أدوات اختيارية لتحليل الزيارات وقياس الإعلانات. يمكنك رفضها مع استمرار تصفح الموقع والتواصل. <a href="/policies.html#privacy">سياسة الخصوصية</a></p><div><button type="button" data-choice="rejected">رفض الاختيارية</button><button type="button" data-choice="accepted">قبول التحليلات والإعلانات</button></div>' + (loaded ? '<small>سحب الموافقة يعيد تحميل الصفحة لإيقاف الأدوات التي سبق تشغيلها.</small>' : '');
    var style = document.createElement('style');
    style.textContent = '#privacy-choice{position:fixed;z-index:10000;inset:auto 14px 14px auto;width:min(540px,calc(100% - 28px));max-height:65vh;overflow:auto;padding:20px;margin:0;background:#fff;color:#172331;border:1px solid #8e969e;border-radius:12px;box-shadow:0 10px 45px #0003;font:15px/1.8 Tahoma,Arial,sans-serif;text-align:right}#privacy-choice p{margin:0 0 12px}#privacy-choice a{color:#164b96;text-decoration:underline}#privacy-choice div{display:flex;flex-wrap:wrap;gap:10px}#privacy-choice button{font:inherit;color:#142d48;background:#f1f4f8;border:1px solid #66788b;border-radius:6px;padding:9px 12px;cursor:pointer}#privacy-choice button:focus-visible{outline:3px solid #2563eb;outline-offset:3px}#privacy-choice small{display:block;margin-top:10px}';
    box.appendChild(style); document.body.appendChild(box);
    box.addEventListener('click', function (event) {
      var button = event.target.closest('[data-choice]'); if (!button) return;
      var wasLoaded = loaded; choice = button.dataset.choice;
      try { localStorage.setItem(key, JSON.stringify({ value: choice, time: Date.now() })); } catch (_) {}
      box.remove();
      if (choice === 'accepted') activate();
      else { clearOptionalStorage(); if (wasLoaded) location.reload(); }
    });
  }
  function ready() {
    if (choice === 'accepted') activate();
    else { clearOptionalStorage(); if (!choice) show(); }
    document.addEventListener('click', function (event) {
      if (event.target.closest('[data-privacy-settings]')) { event.preventDefault(); show(); }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready, { once: true });
  else ready();
})();
