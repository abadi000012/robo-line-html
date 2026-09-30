/* IGA Lines — progressive enhancements. Every page reads fine without this file. */
(function () {
  "use strict";
  var d = document;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var nf = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
  var nf0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

  /* Headings draw their rail, blocks fade in, when they come into view. */
  var watched = d.querySelectorAll(".reveal, .h2");
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -12% 0px" });
    watched.forEach(function (el) { io.observe(el); });
  } else {
    watched.forEach(function (el) { el.classList.add("is-in"); });
  }

  /* Station bar: light the node of the solution being read. */
  var bar = d.querySelector("[data-stations]");
  if (bar && "IntersectionObserver" in window) {
    var list = bar.querySelector("ol");
    var links = Array.prototype.slice.call(bar.querySelectorAll("a[href^='#']"));
    var sections = links.map(function (a) { return d.getElementById(a.hash.slice(1)); });
    var visible = new Set();
    var current = -1;
    var setActive = function (i) {
      if (i === current) return;
      current = i;
      links.forEach(function (a, j) {
        if (j === i) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
        a.classList.toggle("is-passed", i > -1 && j < i);
      });
      list.style.setProperty("--p", i < 1 ? 0 : i / (links.length - 1));
      if (i > -1) {
        var a = links[i], nav = a.closest("nav");
        var target = a.offsetLeft - (nav.clientWidth - a.offsetWidth) / 2;
        nav.scrollTo({ left: target, behavior: reduce ? "auto" : "smooth" });
      }
    };
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var i = sections.indexOf(e.target);
        if (e.isIntersecting) visible.add(i); else visible.delete(i);
      });
      if (visible.size) setActive(Math.min.apply(null, Array.from(visible)));
      else {
        var first = sections[0].getBoundingClientRect().top;
        if (first > window.innerHeight * 0.5) setActive(-1);
      }
    }, { rootMargin: "-40% 0px -55% 0px" });
    sections.forEach(function (s) { if (s) spy.observe(s); });
  }

  /* Calculators. Numbers come only from the visitor; nothing is prefilled. */
  var num = function (form, name) {
    var el = form.querySelector("[name='" + name + "']");
    if (!el || el.value.trim() === "") return null;
    var v = parseFloat(el.value.replace(/[٠-٩]/g, function (c) { return "٠١٢٣٤٥٦٧٨٩".indexOf(c); }).replace(/[,٬]/g, "").replace("٫", "."));
    return isFinite(v) ? v : null;
  };
  d.querySelectorAll("[data-calc]").forEach(function (calc) {
    var form = calc.querySelector(".calc-form");
    var out = function (key) { return calc.querySelector("[data-out='" + key + "']"); };
    var unit = calc.getAttribute("data-unit");
    var units = calc.getAttribute("data-unit-plural");
    var kind = calc.getAttribute("data-calc");
    var render = function () {
      var main = out("main"), msg = out("msg");
      var lines = calc.querySelectorAll("[data-line]");
      lines.forEach(function (li) { li.hidden = true; });
      main.classList.add("is-empty");
      msg.classList.remove("warn");
      var show = function (key, text) { var li = calc.querySelector("[data-line='" + key + "']"); li.hidden = false; li.querySelector("b").textContent = text; };

      if (kind === "breakeven") {
        var price = num(form, "price"), variable = num(form, "variable"), fixed = num(form, "fixed");
        var expected = num(form, "expected"), capital = num(form, "capital");
        if (price === null || variable === null || fixed === null) {
          main.firstChild.textContent = "—";
          msg.textContent = "أدخل السعر والتكلفة المتغيرة والتكاليف الثابتة لتظهر النتيجة.";
          return;
        }
        var margin = price - variable;
        show("margin", nf.format(margin) + " ر.س");
        if (margin <= 0) {
          main.firstChild.textContent = "—";
          msg.textContent = "الهامش صفر أو سالب: كل " + unit + " تزيد الخسارة. راجع السعر أو التكلفة المتغيرة.";
          msg.classList.add("warn");
          return;
        }
        var need = Math.ceil(fixed / margin);
        main.classList.remove("is-empty");
        main.firstChild.textContent = nf0.format(need) + " ";
        show("daily", nf.format(need / 30));
        msg.textContent = "عدد " + units + " المطلوب شهريًا لتغطية التكاليف الثابتة. جرّب سيناريو منخفضًا وآخر متوسطًا.";
        if (expected !== null) {
          var net = expected * margin - fixed;
          show("net", nf0.format(net) + " ر.س");
          if (capital !== null) {
            show("payback", net > 0 ? nf.format(capital / net) + " شهر" : "لا يُسترد بهذا الحجم");
          }
        }
      } else if (kind === "savings") {
        var cur = num(form, "current"), nw = num(form, "new"), vol = num(form, "volume"), cap = num(form, "capital");
        if (cur === null || nw === null || vol === null) {
          main.firstChild.textContent = "—";
          msg.textContent = "أدخل تكلفة العبوة الحالية والمتوقعة وعدد العبوات الشهري لتظهر النتيجة.";
          return;
        }
        var saving = (cur - nw) * vol;
        show("unit", nf.format(cur - nw) + " ر.س");
        if (saving <= 0) {
          main.firstChild.textContent = "—";
          msg.textContent = "لا يظهر وفر بهذه الأرقام: تكلفة العبوة بعد الأتمتة ليست أقل من الحالية.";
          msg.classList.add("warn");
          return;
        }
        main.classList.remove("is-empty");
        main.firstChild.textContent = nf0.format(saving) + " ";
        msg.textContent = "الوفر الشهري المتوقع قبل تكاليف التمويل. اعتمد تكلفة العبوة بعد الأتمتة من اختبار عينتك.";
        if (cap !== null) show("payback", nf.format(cap / saving) + " شهر");
      }
    };
    form.addEventListener("input", render);
    render();
  });

  /* Quote builder: turn the fields into a WhatsApp message. */
  d.querySelectorAll("[data-quote]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var parts = ["مرحبًا IGA Lines، أرغب بعرض سعر."];
      form.querySelectorAll("[data-q]").forEach(function (el) {
        var v = (el.value || "").trim();
        if (v) parts.push(el.getAttribute("data-q") + ": " + v);
      });
      var page = form.getAttribute("data-page");
      if (page) parts.push("الصفحة: " + page);
      var url = form.getAttribute("action") + "?text=" + encodeURIComponent(parts.join("\n"));
      var win = window.open(url, "_blank", "noopener");
      if (!win) window.location.href = url;
    });
  });

  /* Mobile menu closes after choosing a link. */
  d.querySelectorAll(".menu a").forEach(function (a) {
    a.addEventListener("click", function () { a.closest("details").removeAttribute("open"); });
  });
})();
