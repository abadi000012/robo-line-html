/* First-party source labels for WhatsApp. Never stores click IDs or customer details. */
(function () {
  'use strict';
  if (window.SiteAttribution) return;
  var config = document.currentScript;
  var measurementId = config && config.getAttribute('data-ga-id');
  var key = 'website_source_v1';
  var lifetime = 30 * 24 * 60 * 60 * 1000;
  var sources = {
    tiktok: ['TK', 'TikTok'],
    google_ads: ['ADW', 'Google Ads'],
    haraj: ['HRJ', 'حراج'],
    google_organic: ['GO', 'بحث Google'],
    referral: ['REF', 'إحالة من موقع آخر'],
    campaign: ['CAM', 'رابط حملة أخرى'],
    direct: ['DIR', 'مباشر / غير معروف']
  };
  var here = new URL(window.location.href);
  var params = here.searchParams;
  function clean(value) {
    value = (value || '').trim();
    return /^[a-zA-Z0-9\u0600-\u06ff _.-]{1,80}$/.test(value) ? value : '';
  }
  function hostname(value) {
    try { return new URL(value).hostname.toLowerCase().replace(/^www\./, ''); }
    catch (_) { return ''; }
  }
  function belongs(host, domain) { return host === domain || host.endsWith('.' + domain); }
  var ref = hostname(document.referrer);
  var ownHost = hostname(here.href);
  var utm = (params.get('utm_source') || '').trim().toLowerCase();
  var medium = (params.get('utm_medium') || '').trim().toLowerCase();
  var googleClick = ['gclid', 'gbraid', 'wbraid'].some(function (p) { return !!params.get(p); });
  var source = '';
  if (/^(tiktok|tik_tok|tik-tok|tt)$/.test(utm)) source = 'tiktok';
  else if (/^(google|googleads|google_ads|adwords)$/.test(utm)) {
    source = googleClick || /^(cpc|ppc|paid|paid_search|paidsearch)$/.test(medium) || utm !== 'google' ? 'google_ads' : 'google_organic';
  } else if (/^(haraj|حراج|haraj.com.sa)$/.test(utm)) source = 'haraj';
  else if (utm) source = 'campaign';
  else if (googleClick) source = 'google_ads';
  else if (params.get('ttclid')) source = 'tiktok';
  else if (ref && ref !== ownHost) {
    if (belongs(ref, 'tiktok.com')) source = 'tiktok';
    else if (belongs(ref, 'haraj.com.sa')) source = 'haraj';
    else if (/^(www\.)?google\.(com|com\.sa|co\.uk|ae|sa)$/.test(ref)) source = 'google_organic';
    else source = 'referral';
  }
  function readSaved() {
    try {
      var cookie = document.cookie.split('; ').find(function (v) { return v.indexOf(key + '=') === 0; });
      var value = cookie ? decodeURIComponent(cookie.slice(key.length + 1)) : window.localStorage.getItem(key);
      var saved = JSON.parse(value || 'null');
      if (saved && sources[saved.source] && typeof saved.time === 'number' &&
          saved.time <= Date.now() && Date.now() - saved.time < lifetime) {
        return { source: saved.source, campaign: clean(saved.campaign), time: saved.time,
          number: /^\d{3}$/.test(saved.number || '') ? saved.number : '' };
      }
    } catch (_) { /* Storage can be unavailable in private browsers. */ }
    return null;
  }
  var previous = readSaved();
  var current = source ? { source: source, campaign: clean(params.get('utm_campaign')), time: Date.now() } : previous;
  if (!current) current = { source: 'direct', campaign: '', time: Date.now() };
  // Keep the visitor's random suffix stable across navigation and source changes.
  // Three digits are a convenient reference, not a unique customer ID.
  var number = previous && previous.number;
  if (!number) {
    var random = Math.floor(Math.random() * 1000);
    try {
      var bytes = new Uint32Array(1);
      window.crypto.getRandomValues(bytes);
      random = bytes[0] % 1000;
    } catch (_) { /* Math.random fallback for older browsers. */ }
    number = String(random).padStart(3, '0');
  }
  current.number = number;
  current.code = sources[current.source][0] + number;
  {
    var serialized = JSON.stringify(current);
    try { window.localStorage.setItem(key, serialized); } catch (_) { /* Keep working without storage. */ }
    try {
      var domain = ['sanadalsharq.com', 'robo-line.com'].find(function (d) { return belongs(ownHost, d); });
      document.cookie = key + '=' + encodeURIComponent(serialized) + '; Path=/; Max-Age=' + lifetime / 1000 +
        '; SameSite=Lax' + (here.protocol === 'https:' ? '; Secure' : '') + (domain ? '; Domain=' + domain : '');
    } catch (_) { /* Keep working without cookies. */ }
  }
  function isWhatsApp(url) {
    return (url.protocol === 'https:' && ['wa.me', 'api.whatsapp.com', 'web.whatsapp.com'].indexOf(url.hostname) !== -1) ||
      (url.protocol === 'whatsapp:' && url.hostname === 'send');
  }
  function whatsappUrl(href) {
    try {
      var url = new URL(href, here.href);
      if (!isWhatsApp(url)) return href;
      var original = (url.searchParams.get('text') || 'مرحبًا، أرغب بالاستفسار عن خدماتكم.');
      // Replace our own trailing block, keeping product details and the original message.
      original = original.replace(/\n\n\[المصدر: [^\n]*\](?:\nالحملة: [^\n]*)?$/, '');
      original = original.replace(/\n\n(?:TK|HRJ|ADW|GO|REF|CAM|DIR)\d{3}$/, '');
      var message = original + '\n\n' + current.code;
      url.searchParams.set('text', message);
      return url.href;
    } catch (_) { return href; }
  }
  function safePageUrl() {
    var url = new URL(here.origin + here.pathname);
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'utm_id'].forEach(function (p) {
      var v = clean(params.get(p));
      if (v) url.searchParams.set(p, v);
    });
    ['gclid', 'gbraid', 'wbraid'].forEach(function (p) {
      var v = params.get(p);
      if (v && /^[a-zA-Z0-9_.~-]{1,500}$/.test(v)) url.searchParams.set(p, v);
    });
    return url.href;
  }
  function track(name) {
    if (!measurementId || typeof window.gtag !== 'function') return;
    window.gtag('event', name, { send_to: measurementId, contact_source: current.source,
      source_code: sources[current.source][0], source_campaign: current.campaign });
  }
  window.SiteAttribution = { whatsappUrl: whatsappUrl, track: track, get: function () { return Object.assign({}, current); } };
  if (/^G-[A-Z0-9]+$/.test(measurementId || '')) {
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', measurementId, { page_location: safePageUrl(),
      page_referrer: ref ? 'https://' + ref + '/' : '', allow_google_signals: false,
      allow_ad_personalization_signals: false });
    var script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
    document.head.appendChild(script);
  }
  function updateLink(link) {
    var href = link.getAttribute('href');
    if (!href) return;
    var decorated = whatsappUrl(href);
    if (decorated !== href) link.setAttribute('href', decorated);
  }
  document.querySelectorAll('a[href]').forEach(updateLink);
  ['click', 'auxclick', 'contextmenu'].forEach(function (name) {
    document.addEventListener(name, function (event) {
      var link = event.target && event.target.closest ? event.target.closest('a[href]') : null;
      if (!link) return;
      updateLink(link);
      if (name === 'contextmenu' || (name === 'auxclick' && event.button !== 1)) return;
      try {
        var url = new URL(link.href, here.href);
        if (isWhatsApp(url)) track('whatsapp_click');
        else if (url.protocol === 'tel:') track('phone_click');
      } catch (_) { /* An invalid link should not interrupt navigation. */ }
    }, true);
  });
})();
