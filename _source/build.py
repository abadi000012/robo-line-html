#!/usr/bin/env python3
"""Build the IGA Lines website into the repository root (the folder above _source/).

    _source/.venv/bin/python _source/build.py          # build everything
    _source/.venv/bin/python _source/build.py --og     # also re-render the social share images

Content lives in _source/src/content/*.py, styles in src/css, scripts in src/js.
The host (Hostinger, via GitHub) serves the repository root, so the built pages live there.
"""
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PUB = ROOT.parent  # the repository root is the website root
sys.path.insert(0, str(SRC))

from content import site  # noqa: E402
from content import home as home_content  # noqa: E402
from content import vending, packaging, recycling, car_wash  # noqa: E402

CATS = {m.CATEGORY["slug"]: m.CATEGORY for m in (vending, packaging, recycling, car_wash)}
ORDERED = [CATS[s] for s in site.CATEGORY_ORDER]
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
REBUILD_OG = "--og" in sys.argv
HOST = site.DOMAIN.split("://", 1)[1]


# ---------------------------------------------------------------- helpers

def e(s):
    return html.escape(str(s), quote=True)


def md(s):
    """Escape text, then allow [label](url) links and **bold**."""
    out = e(s)
    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                 lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>', out)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)


def plain(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return s.replace("**", "")


def url(path):
    return site.DOMAIN + path


def cat_path(c):
    return f"/categories/{c['slug']}/"


def wa(text):
    return f"https://wa.me/{site.WHATSAPP}?text={quote(text)}"


def ltr(s):
    return f'<bdi dir="ltr" class="num">{e(s)}</bdi>'


ICONS = {
    "wa": '<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12.04 2a9.9 9.9 0 0 0-8.45 15.07L2 22l5.06-1.55A9.9 9.9 0 1 0 12.04 2Zm0 18.1a8.2 8.2 0 0 1-4.2-1.15l-.3-.18-3 .92.94-2.92-.2-.31a8.2 8.2 0 1 1 6.76 3.64Zm4.5-6.14c-.25-.12-1.46-.72-1.69-.8-.23-.08-.39-.12-.56.13-.16.25-.64.8-.79.97-.14.16-.29.18-.54.06a6.7 6.7 0 0 1-3.34-2.92c-.25-.43.25-.4.72-1.34.08-.16.04-.3-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.4-.41-.56-.42h-.48a.92.92 0 0 0-.66.31 2.78 2.78 0 0 0-.87 2.07 4.83 4.83 0 0 0 1.01 2.56 11.05 11.05 0 0 0 4.23 3.74c1.58.68 2.2.74 2.99.62.48-.07 1.46-.6 1.67-1.18.2-.58.2-1.08.14-1.18-.06-.1-.22-.16-.47-.28Z"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.9v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.18 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.72c.12.96.36 1.9.7 2.8a2 2 0 0 1-.45 2.11L8.1 9.9a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.84.58 2.8.7A2 2 0 0 1 22 16.9Z"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="4.5" width="19" height="15" rx="2"/><path d="m3 6 9 7 9-7"/></svg>',
    "go": '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5m6-6-6 6 6 6"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h10"/></svg>',
    "caution": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 20.5h20L12 3Z" fill="#f0b429"/><path d="M12 9.5v5.2m0 2.6v.2" stroke="#3a2a00" stroke-width="2" stroke-linecap="round"/></svg>',
}


def logo(uid):
    svg = (SRC / "svg" / "logo.svg").read_text(encoding="utf-8")
    svg = re.sub(r'(id="|url\(#)l([gmf])', lambda m: m.group(1) + uid + m.group(2), svg)
    return svg.replace('role="img" aria-label="IGA Lines"', 'aria-hidden="true" focusable="false"')


# ---------------------------------------------------------------- images

SIZES = {"portrait": [240, 400, 640, 900], "landscape": [240, 480, 800, 1280], "photo": [480, 800, 1100],
         "hero": [800, 1280, 1696]}
IMAGES = {}


CACHE = ROOT / ".cache"


def crop_landscape(stem, focus=0.3):
    """A 3:2 crop of a portrait image, for slots that show machines in landscape.
    Saves phones from downloading pixels that object-fit would hide."""
    src = SRC / "images" / f"{stem}.png"
    out = CACHE / f"{stem}-wide.png"
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        CACHE.mkdir(exist_ok=True)
        im = Image.open(src).convert("RGB")
        w, h = im.size
        ch = round(w * 2 / 3)
        top = round((h - ch) * focus)
        im.crop((0, top, w, top + ch)).save(out)
    return f"{stem}-wide", out


def image_set(stem, kind, src=None):
    if stem in IMAGES:
        return IMAGES[stem]
    src = src or SRC / "images" / f"{stem}.png"
    out_dir = PUB / "img"
    out_dir.mkdir(parents=True, exist_ok=True)
    im = None
    w0, h0 = Image.open(src).size
    widths = []
    for w in SIZES[kind]:
        w = min(w, w0)
        h = round(h0 * w / w0)
        for fmt, opts in (("avif", dict(quality=55, speed=6)), ("webp", dict(quality=78, method=6))):
            dst = out_dir / f"{stem}-{w}.{fmt}"
            if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                if im is None:
                    im = Image.open(src).convert("RGB")
                im.resize((w, h), Image.LANCZOS).save(dst, fmt.upper(), **opts)
        widths.append((w, h))
    IMAGES[stem] = widths
    return widths


def picture(stem, kind, alt, sizes, eager=False, style="", src=None):
    widths = image_set(stem, kind, src)
    avif = ", ".join(f"/img/{stem}-{w}.avif {w}w" for w, _ in widths)
    webp = ", ".join(f"/img/{stem}-{w}.webp {w}w" for w, _ in widths)
    w, h = widths[-1]
    load = ' fetchpriority="high"' if eager == "high" else ("" if eager else ' loading="lazy"')
    st = f' style="{style}"' if style else ""
    return (f'<picture><source type="image/avif" srcset="{avif}" sizes="{sizes}">'
            f'<img src="/img/{stem}-{widths[1][0]}.webp" srcset="{webp}" sizes="{sizes}" '
            f'width="{w}" height="{h}" alt="{e(alt)}" decoding="async"{load}{st}></picture>')


def img_url(stem, kind, which=-1):
    w, _ = image_set(stem, kind)[which]
    return url(f"/img/{stem}-{w}.webp")


# ---------------------------------------------------------------- assets

def minify_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    return css.replace(";}", "}").strip()


CSS = minify_css((SRC / "css" / "site.css").read_text(encoding="utf-8"))
JS_SRC = (SRC / "js" / "site.js").read_text(encoding="utf-8")
JS_NAME = f"site.{hashlib.sha1(JS_SRC.encode()).hexdigest()[:10]}.js"


# ---------------------------------------------------------------- structured data

ORG_ID = site.DOMAIN + "/#organization"
SITE_ID = site.DOMAIN + "/#website"


def org_nodes():
    return [
        {
            "@type": "Organization", "@id": ORG_ID, "name": site.NAME,
            "alternateName": [site.NAME_AR, "IGA"], "url": url("/"),
            "logo": {"@type": "ImageObject", "url": url("/icon-512.png"), "width": 512, "height": 512},
            "description": site.SUMMARY, "email": site.EMAIL, "telephone": site.PHONE_E164,
            "slogan": site.TAGLINE,
            "areaServed": {"@type": "Country", "name": "Saudi Arabia"},
            "contactPoint": [{
                "@type": "ContactPoint", "contactType": "sales", "telephone": site.PHONE_E164,
                "email": site.EMAIL, "areaServed": "SA", "availableLanguage": ["ar"],
            }],
            "knowsAbout": [c["name"] for c in ORDERED],
        },
        {
            "@type": "WebSite", "@id": SITE_ID, "url": url("/"), "name": site.NAME,
            "alternateName": site.NAME_AR, "inLanguage": "ar-SA", "publisher": {"@id": ORG_ID},
        },
    ]


def breadcrumb_node(page_url, trail):
    return {
        "@type": "BreadcrumbList", "@id": page_url + "#breadcrumb",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                            for i, (n, u) in enumerate(trail)],
    }


def faq_node(page_url, items):
    return {
        "@type": "FAQPage", "@id": page_url + "#faq",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": plain(a)}} for q, a in items],
    }


def jsonld(nodes):
    data = {"@context": "https://schema.org", "@graph": org_nodes() + nodes}
    return ('<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
            + "</script>")


# ---------------------------------------------------------------- page chrome

def head(p):
    canonical = url(p["path"])
    robots = p.get("robots", "index, follow, max-image-preview:large, max-snippet:-1")
    og = url(f"/og/{p['og']}.jpg")
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(p['title'])}</title>
<meta name="description" content="{e(p['description'])}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#050a14">
<meta name="format-detection" content="telephone=no">
<meta property="og:type" content="website">
<meta property="og:locale" content="ar_SA">
<meta property="og:site_name" content="{site.NAME}">
<meta property="og:title" content="{e(p['title'])}">
<meta property="og:description" content="{e(p['description'])}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(p.get('og_alt', p['title']))}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" href="/assets/fonts/noto-kufi-arabic-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/ibm-plex-sans-arabic-400.woff2" as="font" type="font/woff2" crossorigin>
<script>document.documentElement.classList.add("js")</script>
<style>{CSS}</style>
<script src="/assets/{JS_NAME}" defer></script>
{p.get('jsonld', '')}
</head>
"""


def header(active):
    items = [(c["nav"], cat_path(c)) for c in ORDERED] + [("تواصل معنا", "/contact/")]

    def li(label, path):
        cur = ' aria-current="page"' if path == active else ""
        return f'<li><a href="{path}"{cur}>{e(label)}</a></li>'

    links = "".join(li(*i) for i in items)
    return f"""<body>
<a class="skip" href="#main">تخطَّ إلى المحتوى</a>
<header class="site-header">
<div class="wrap">
<a class="brand" href="/" aria-label="IGA Lines، الصفحة الرئيسية">{logo("h")}</a>
<nav class="nav" aria-label="الفئات"><ul>{links}</ul></nav>
<a class="btn btn-primary header-cta" href="{wa('مرحبًا IGA Lines، أرغب بعرض سعر.')}" target="_blank" rel="noopener">{ICONS['wa']}واتساب</a>
<details class="menu">
<summary>{ICONS['menu']}<span>القائمة</span></summary>
<div class="menu-panel"><ul>{links}</ul>
<a class="btn btn-primary" href="{wa('مرحبًا IGA Lines، أرغب بعرض سعر.')}" target="_blank" rel="noopener">{ICONS['wa']}اطلب عرضًا عبر واتساب</a>
</div>
</details>
</div>
</header>
"""


def footer():
    cats = "".join(f'<li><a href="{cat_path(c)}">{e(c["name"])}</a></li>' for c in ORDERED)
    return f"""<footer class="site-footer">
<div class="wrap">
<div class="footer-grid">
<div>
<a class="brand" href="/" aria-label="IGA Lines، الصفحة الرئيسية">{logo("f")}</a>
<p class="footer-name">{e(site.NAME_AR)}</p>
<p>{e(site.SUMMARY)}</p>
</div>
<nav aria-label="الفئات في التذييل">
<h2>الفئات</h2>
<ul>{cats}</ul>
</nav>
<div>
<h2>تواصل</h2>
<ul>
<li><a href="{wa('مرحبًا IGA Lines، أرغب بعرض سعر.')}" target="_blank" rel="noopener">واتساب: {ltr(site.PHONE_DISPLAY)}</a></li>
<li><a href="tel:{site.PHONE_E164}">اتصال: {ltr(site.PHONE_DISPLAY)}</a></li>
<li><a href="mailto:{site.EMAIL}">{ltr(site.EMAIL)}</a></li>
<li><a href="/contact/">صفحة التواصل</a></li>
</ul>
</div>
</div>
<div class="footer-base">
<span>© {site.YEAR} {site.NAME}. جميع الحقوق محفوظة.</span>
<span>{e(site.TAGLINE)}</span>
</div>
</div>
</footer>
"""


def dock(message):
    return f"""<div class="dock">
<a class="btn btn-wa" href="{wa(message)}" target="_blank" rel="noopener">{ICONS['wa']}واتساب</a>
<a class="btn btn-call" href="tel:{site.PHONE_E164}">{ICONS['phone']}اتصال</a>
</div>
"""


def page(p, body):
    return head(p) + header(p["path"]) + body + footer() + dock(p.get("dock", "مرحبًا IGA Lines، أرغب بعرض سعر.")) + "</body>\n</html>\n"


def lines(text):
    return " <br>".join(e(part) for part in text.split("\n"))


def rail_title(main, tail):
    tail_html = f' <span class="rail-title__tail">{lines(tail)}</span>' if tail else ""
    short = " rail-title--short" if tail and len(tail) <= 24 else ""
    return (f'<h1 class="rail-title{short}"><span class="rail-title__main">{e(main)}'
            f'<span class="rail-node" aria-hidden="true"></span></span>{tail_html}</h1>')


def hero_bg():
    """The previous site's production-line photo, washed light behind the hero text."""
    src = SRC / "images" / "hero-line.webp"
    return f'<div class="hero-bg" aria-hidden="true">{picture("hero-line", "hero", "", "100vw", eager="high", src=src)}</div>'


def section_head(title, id_, lede=None):
    return (f'<div class="section-head">{h2(title, id_)}'
            + (f'<p class="lede">{md(lede)}</p>' if lede else "") + "</div>")


def h2(text, id_=None):
    i = f' id="{id_}"' if id_ else ""
    return f'<h2 class="h2"{i}>{e(text)}</h2>'


def faq_html(items):
    return '<div class="faq">' + "".join(
        f'<details><summary>{e(q)}</summary><div class="answer"><p>{md(a)}</p></div></details>'
        for q, a in items) + "</div>"


QUOTE_FIELDS = {
    "vending-machines": (("نوع الموقع", "مثال: مول، نادٍ رياضي، فندق"), ("عدد المكائن", "مثال: 2")),
    "packaging-machines": (("المنتج والعبوة", "مثال: بهارات في أكياس 250 جم"), ("الإنتاج المستهدف", "مثال: 1,500 عبوة يوميًا")),
    "recycling-lines": (("نوع المادة", "مثال: قوارير PET مفروزة"), ("الكمية الشهرية", "مثال: 60 طنًا")),
    "car-wash": (("نوع الموقع والمركبات", "مثال: محطة وقود، سيارات ركوب"), ("الطلب المتوقع", "مثال: 80 سيارة يوميًا")),
    None: (("المنتج أو نوع الموقع", "مثال: مول، مصنع أغذية، محطة وقود"), ("الكمية أو الطاقة", "مثال: مكينتان، 1,500 عبوة يوميًا")),
}


def builder(uid, cat=None, page_name=""):
    if cat:
        opts = "".join(f'<option>{e(p["name"])}</option>' for p in cat["products"])
        first = (f'<div class="field"><label for="{uid}-s">الحل المطلوب</label>'
                 f'<select id="{uid}-s" data-q="الحل"><option value="">لم أحدد بعد</option>{opts}</select></div>')
        (l1, p1), (l2, p2) = QUOTE_FIELDS[cat["slug"]]
    else:
        opts = "".join(f'<option>{e(c["name"])}</option>' for c in ORDERED)
        first = (f'<div class="field"><label for="{uid}-s">الفئة</label>'
                 f'<select id="{uid}-s" data-q="الفئة"><option value="">اختر الفئة</option>{opts}<option>أخرى</option></select></div>')
        (l1, p1), (l2, p2) = QUOTE_FIELDS[None]
    return f"""<form class="builder" data-quote action="https://wa.me/{site.WHATSAPP}" method="get" target="_blank" data-page="{e(page_name)}">
<h3>جهّز رسالة طلب العرض</h3>
{first}
<div class="row-2">
<div class="field"><label for="{uid}-c">المدينة</label><input type="text" id="{uid}-c" data-q="المدينة" autocomplete="address-level2" placeholder="مثال: الرياض"></div>
<div class="field"><label for="{uid}-q">{e(l2)}</label><input type="text" id="{uid}-q" data-q="{e(l2)}" placeholder="{e(p2)}"></div>
</div>
<div class="field"><label for="{uid}-t">{e(l1)}</label><input type="text" id="{uid}-t" data-q="{e(l1)}" placeholder="{e(p1)}"></div>
<div class="field"><label for="{uid}-n">ملاحظات</label><textarea id="{uid}-n" data-q="ملاحظات" placeholder="الميزانية، الموعد، الكهرباء والماء المتاحة، أي تفاصيل أخرى"></textarea></div>
<button class="btn btn-wa" type="submit">{ICONS['wa']}افتح الرسالة في واتساب</button>
<p class="fine">لا نحفظ ما تكتبه هنا؛ تُفتح الرسالة في واتساب لتراجعها وترسلها بنفسك.</p>
</form>"""


def calculator(c):
    k = c["calculator"]
    uid = "calc-" + c["slug"]

    def field(name, label, hint, unit="ر.س"):
        return (f'<div class="field"><label for="{uid}-{name}">{e(label)} ({e(unit)})</label>'
                f'<input type="text" id="{uid}-{name}" name="{name}" inputmode="decimal" autocomplete="off" placeholder="0">'
                + (f'<span class="hint">{e(hint)}</span>' if hint else "") + "</div>")

    if k["kind"] == "breakeven":
        inputs = (field("price", k["price"][0], None)
                  + field("variable", k["variable"][0], k["variable"][1])
                  + field("fixed", k["fixed"][0], k["fixed"][1])
                  + '<div class="optional"><p>اختياري: لحساب الصافي ومدة الاسترداد</p><div class="row-2">'
                  + field("expected", k["expected"], None, unit=k["unit"])
                  + field("capital", k["capital"], None)
                  + "</div></div>")
        lines = (f'<li data-line="margin" hidden><span>هامش المساهمة لكل {e(k["unit"])}</span><b></b></li>'
                 f'<li data-line="daily" hidden><span>ما يعادل يوميًا (30 يومًا)</span><b></b></li>'
                 f'<li data-line="net" hidden><span>الصافي الشهري بالحجم المتوقع</span><b></b></li>'
                 f'<li data-line="payback" hidden><span>مدة استرداد الاستثمار</span><b></b></li>')
        label = f"نقطة التعادل: عدد {k['unit_plural']} شهريًا"
        small = "شهريًا"
    else:
        inputs = (field("current", k["current"][0], k["current"][1])
                  + field("new", k["new"][0], k["new"][1])
                  + field("volume", k["volume"], None, unit=k["unit"])
                  + '<div class="optional"><p>اختياري: لحساب مدة الاسترداد</p>'
                  + field("capital", k["capital"], None) + "</div>")
        lines = (f'<li data-line="unit" hidden><span>الوفر في كل {e(k["unit"])}</span><b></b></li>'
                 f'<li data-line="payback" hidden><span>مدة استرداد الاستثمار</span><b></b></li>')
        label = "الوفر الشهري المتوقع"
        small = "ر.س شهريًا"
    return f"""<div class="calc" data-calc="{k['kind']}" data-unit="{e(k['unit'])}" data-unit-plural="{e(k['unit_plural'])}">
<div class="calc-form" role="group" aria-labelledby="{uid}-h">
<h3 id="{uid}-h">{e(k['title'])}</h3>
{inputs}
</div>
<div class="calc-out" aria-live="polite">
<p class="label">{e(label)}</p>
<p class="readout is-empty" data-out="main">— <small>{e(small)}</small></p>
<ul class="calc-lines">{lines}</ul>
<p class="calc-msg" data-out="msg">أدخل أرقامك لتظهر النتيجة.</p>
<noscript><p class="calc-msg">تحتاج الحاسبة إلى تفعيل JavaScript.</p></noscript>
</div>
</div>"""


def table(head_cells, rows):
    th = "".join(f'<th scope="col">{e(h)}</th>' for h in head_cells)
    body = ""
    for r in rows:
        cells = f'<th scope="row">{e(r[0])}</th>' + "".join(
            f'<td data-label="{e(head_cells[i + 1])}">{e(v)}</td>' for i, v in enumerate(r[1:]))
        body += f"<tr>{cells}</tr>"
    return f'<table class="table"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


# ---------------------------------------------------------------- pages

def build_category(c):
    path = cat_path(c)
    page_url = url(path)
    products = c["products"]
    portrait = products[0]["orientation"] == "portrait"
    kind = "portrait" if portrait else "landscape"

    showcase_sizes = "(min-width: 1200px) 220px, (min-width: 900px) 18vw, 42vw"
    show = "".join(
        f'<li><a href="#{p["id"]}">'
        f'<span class="showcase-img">{picture(p["image"], kind, "تصور " + p["name"] + " بهوية IGA Lines", showcase_sizes, eager=True)}</span>'
        f'<span class="showcase-label">{e(p["short"])}</span></a></li>' for p in products)

    stations = "".join(f'<li><a href="#{p["id"]}">{e(p["short"])}</a></li>' for p in products)

    intro = c["intro"]
    intro_html = "".join(f"<p>{md(x)}</p>" for x in intro["paragraphs"])
    if intro.get("note"):
        intro_html += f'<p class="note-sm">{md(intro["note"])}</p>'

    sol = c["solutions"]
    sol_head = ""
    if sol.get("title"):
        sol_head = section_head(sol["title"], "solutions-title", sol.get("intro"))

    stage_sizes = ("(min-width: 1200px) 400px, (min-width: 900px) 34vw, 100vw" if portrait
                   else "(min-width: 1200px) 540px, (min-width: 900px) 44vw, 100vw")
    articles = ""
    for p in products:
        feats = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in p["features"])
        value = f'<p class="value"><strong>القيمة العملية:</strong> {md(p["value"])}</p>' if p.get("value") else ""
        ask = wa(f"مرحبًا IGA Lines، أرغب بمعلومات وعرض سعر عن: {p['name']}.")
        articles += f"""<article class="solution{' solution--portrait' if portrait else ''}" id="{p['id']}" aria-labelledby="{p['id']}-t">
<figure class="stage"><div class="stage-frame">{picture(p['image'], kind, 'تصور ' + p['name'] + ' بهوية IGA Lines', stage_sizes)}</div>
<figcaption>{e(site.IMAGE_NOTE)}</figcaption></figure>
<div class="solution-text">
<p class="eyebrow tag">{e(p['tag'])}</p>
<h2 id="{p['id']}-t">{e(p['name'])}</h2>
<p>{md(p['body'])}</p>
<dl class="plate">{feats}</dl>
{value}
<p class="callout callout--chance"><strong>{e(sol['opportunity_label'])}:</strong> {md(p['opportunity'])}</p>
<p class="callout callout--check"><strong>{ICONS['caution']}قبل الاختيار:</strong> {md(p['check'])}</p>
<div class="btn-row">
<a class="btn btn-primary" href="{ask}" target="_blank" rel="noopener">{ICONS['wa']}اسأل عن {e(p['short'])}</a>
<a class="btn btn-light" href="tel:{site.PHONE_E164}">{ICONS['phone']}اتصل بنا</a>
</div>
</div>
</article>
"""

    ex = c["extras"]
    extras = "".join(f'<div class="card"><h3>{e(t)}</h3><p>{md(b)}</p></div>' for t, b in ex["items"])

    sp = c["specs"]
    specs_html = section_head(sp["title"], "specs", sp.get("intro")) + table(sp["head"], sp["rows"])
    loc = c.get("locations")
    loc_html = ""
    if loc:
        loc_html = (f'<section class="band band-steel" aria-labelledby="locations"><div class="wrap">'
                    f'{section_head(loc["title"], "locations")}{table(loc["head"], loc["rows"])}'
                    f'<p class="note-sm" style="margin-top:14px">{md(loc["note"])}</p></div></section>')

    b = c["business"]
    biz = "".join(f"<p>{md(x)}</p>" for x in b["paragraphs"])
    if b.get("formula"):
        biz += f'<p class="callout callout--chance">{md(b["formula"])}</p>'
    biz += "".join(f"<p>{md(x)}</p>" for x in b.get("after", []))
    if b.get("source"):
        biz += f'<p class="note-sm">{md(b["source"])}</p>'

    f = c["faq"]
    faq_source = f'<p class="note-sm" style="margin-top:18px">{md(f["source"])}</p>' if f.get("source") else ""

    q = c["quote"]
    checklist = "".join(f"<li>{md(x)}</li>" for x in q["items"])

    others = ""
    for o in ORDERED:
        if o is c:
            continue
        op = o["products"][0]
        okind = op["orientation"]
        others += (f'<a class="other" href="{cat_path(o)}">'
                   f'{picture(op["image"], okind, "", "112px", style="object-position:50% 30%")}'
                   f'<div><h3>{e(o["name"])}</h3><p>{e(o["card_lead"])}</p></div></a>')

    ask_cat = wa(f"مرحبًا IGA Lines، أرغب بعرض سعر لـ{c['name']}.")
    body = f"""<main id="main">
<section class="hero">
{hero_bg()}
<div class="wrap">
<nav class="crumbs" aria-label="مسار التصفح"><ol><li><a href="/">الرئيسية</a></li><li aria-current="page">{e(c['name'])}</li></ol></nav>
<p class="eyebrow">{e(c['eyebrow'])}</p>
{rail_title(c['h1_main'], c['h1_tail'])}
<p class="lede">{md(c['lead'])}</p>
<div class="btn-row">
<a class="btn btn-primary" href="{ask_cat}" target="_blank" rel="noopener">{ICONS['wa']}اطلب عرضًا عبر واتساب</a>
<a class="btn btn-outline" href="tel:{site.PHONE_E164}">{ICONS['phone']}اتصل {ltr(site.PHONE_DISPLAY)}</a>
</div>
<p class="meta">آخر تحديث: <time datetime="{site.UPDATED_ISO}">{site.UPDATED_AR}</time></p>
<ol class="showcase showcase--{kind}">{show}</ol>
</div>
</section>
<div class="zone">
<div class="stationbar" data-stations><nav aria-label="حلول {e(c['name'])}"><ol style="--n:{len(products)}">{stations}</ol></nav></div>
<section class="band band-steel" aria-labelledby="intro"><div class="wrap"><div class="prose">{h2(intro['title'], 'intro')}{intro_html}</div></div></section>
<section class="band band-light solutions" aria-label="{e(sol.get('title') or c['name'])}"><div class="wrap">
{sol_head}
{articles}
</div></section>
</div>
<section class="band band-steel" aria-labelledby="extras"><div class="wrap">{section_head(ex['title'], 'extras', ex.get('intro'))}<div class="cards">{extras}</div></div></section>
<section class="band band-light" aria-labelledby="specs"><div class="wrap">{specs_html}</div></section>
{loc_html}
<section class="band {'band-light' if loc else 'band-steel'}" aria-labelledby="feasibility"><div class="wrap"><div class="prose">{h2(b['title'], 'feasibility')}{biz}</div>{calculator(c)}</div></section>
<section class="band {'band-steel' if loc else 'band-light'}" aria-labelledby="faq-title"><div class="wrap">{section_head(f['title'], 'faq-title')}{faq_html(f['items'])}{faq_source}</div></section>
<section class="band band-dark" id="quote" aria-labelledby="quote-title"><div class="wrap">
{section_head(q['title'], 'quote-title', q['intro'])}
<div class="quote-grid">
<div class="quote-info"><ul class="checklist">{checklist}</ul><p>{md(q['closing'])}</p>
<ul class="contact-lines">
<li><a href="tel:{site.PHONE_E164}">{ICONS['phone']}{ltr(site.PHONE_DISPLAY)}</a></li>
<li><a href="mailto:{site.EMAIL}">{ICONS['mail']}{ltr(site.EMAIL)}</a></li>
</ul></div>
{builder('qb', c, c['name'])}
</div>
</div></section>
<section class="band band-steel" aria-labelledby="others"><div class="wrap">{section_head('فئات أخرى من IGA Lines', 'others')}<div class="others">{others}</div></div></section>
</main>
"""

    nodes = [
        {
            "@type": "CollectionPage", "@id": page_url + "#webpage", "url": page_url, "name": c["title"],
            "description": c["description"], "inLanguage": "ar-SA", "isPartOf": {"@id": SITE_ID},
            "about": {"@id": page_url + "#service"}, "publisher": {"@id": ORG_ID},
            "datePublished": site.UPDATED_ISO, "dateModified": site.UPDATED_ISO,
            "primaryImageOfPage": {"@type": "ImageObject", "url": img_url(products[0]["image"], kind)},
            "breadcrumb": {"@id": page_url + "#breadcrumb"}, "mainEntity": {"@id": page_url + "#solutions"},
        },
        {
            "@type": "Service", "@id": page_url + "#service", "name": c["name"], "serviceType": c["name"],
            "description": plain(c["lead"]), "provider": {"@id": ORG_ID}, "url": page_url,
            "areaServed": {"@type": "Country", "name": "Saudi Arabia"},
        },
        {
            "@type": "ItemList", "@id": page_url + "#solutions", "name": sol.get("title") or c["name"],
            "numberOfItems": len(products),
            "itemListElement": [{
                "@type": "ListItem", "position": i + 1, "name": p["name"], "url": page_url + "#" + p["id"],
                "image": img_url(p["image"], kind),
            } for i, p in enumerate(products)],
        },
        breadcrumb_node(page_url, [("الرئيسية", url("/")), (c["name"], page_url)]),
        faq_node(page_url, f["items"]),
    ]
    p = dict(path=path, title=c["title"], description=c["description"], og=c["slug"],
             og_alt=c["h1_main"] + " " + c["h1_tail"], jsonld=jsonld(nodes),
             dock=f"مرحبًا IGA Lines، أرغب بعرض سعر لـ{c['name']}.")
    write(path, page(p, body))


def build_home():
    h = home_content.HOME
    stations = ""
    for n, c in enumerate(ORDERED):
        p0 = c["products"][0]
        stem, src = (crop_landscape(p0["image"]) if p0["orientation"] == "portrait" else (p0["image"], None))
        links = " · ".join(e(p["short"]) for p in c["products"])
        stations += (f'<li class="station"><a class="station-card" href="{cat_path(c)}">'
                     f'<figure>{picture(stem, "landscape", "تصور " + p0["name"] + " بهوية IGA Lines", "(min-width: 1200px) 285px, (min-width: 900px) 22vw, calc(100vw - 66px)", eager="high" if n == 0 else True, src=src)}</figure>'
                     f'<div class="body"><h3>{e(c["name"])}</h3><p>{e(c["card_lead"])}</p>'
                     f'<p class="sol-list">{links}</p>'
                     f'<span class="go">استكشف الفئة{ICONS["go"]}</span></div></a></li>')

    rules = "".join(f"<li><h3>{e(t)}</h3><p>{md(b)}</p></li>" for t, b in h["rules"])
    process = "".join(f"<li><h3>{e(t)}</h3><p>{md(b)}</p></li>" for t, b in h["process"])
    photos = "".join(f'<figure>{picture(stem, "photo", alt, "(min-width: 900px) 28vw, 50vw")}<figcaption>{e(cap)}</figcaption></figure>'
                     for stem, alt, cap in h["team_photos"])
    prep = "".join(f"<li>{md(x)}</li>" for x in home_content.CONTACT["prepare"])
    body = f"""<main id="main">
<section class="hero hero--home">
{hero_bg()}
<div class="wrap">
<p class="eyebrow">{e(h['eyebrow'])}</p>
{rail_title(h['h1_main'], h['h1_tail'])}
<p class="lede">{md(h['lead'])}</p>
<div class="btn-row">
<a class="btn btn-primary" href="{wa('مرحبًا IGA Lines، أرغب بعرض سعر.')}" target="_blank" rel="noopener">{ICONS['wa']}اطلب عرضًا عبر واتساب</a>
<a class="btn btn-outline" href="tel:{site.PHONE_E164}">{ICONS['phone']}اتصل {ltr(site.PHONE_DISPLAY)}</a>
</div>
</div>
</section>
<section class="band band-light" aria-labelledby="categories"><div class="wrap">{section_head(h['categories_title'], 'categories', h['categories_intro'])}<ol class="stations">{stations}</ol></div></section>
<section class="band band-steel" aria-labelledby="rules"><div class="wrap">{section_head(h['rules_title'], 'rules', h['rules_intro'])}<ol class="rules">{rules}</ol></div></section>
<section class="band band-hull" aria-labelledby="process"><div class="wrap">{section_head(h['process_title'], 'process')}<ol class="process">{process}</ol></div></section>
<section class="band band-light" aria-labelledby="team"><div class="wrap"><div class="team"><div class="team-text">{h2(h['team_title'], 'team')}<p class="lede">{md(h['team_text'])}</p></div><div class="team-photos">{photos}</div></div></div></section>
<section class="band band-steel" aria-labelledby="faq-title"><div class="wrap">{section_head(h['faq_title'], 'faq-title')}{faq_html(h['faq'])}</div></section>
<section class="band band-dark" id="contact" aria-labelledby="contact-title"><div class="wrap">
{section_head(h['contact_title'], 'contact-title', h['contact_intro'])}
<div class="quote-grid">
<div class="quote-info"><ul class="checklist">{prep}</ul>
<ul class="contact-lines">
<li><a href="{wa('مرحبًا IGA Lines، أرغب بعرض سعر.')}" target="_blank" rel="noopener">{ICONS['wa']}واتساب {ltr(site.PHONE_DISPLAY)}</a></li>
<li><a href="tel:{site.PHONE_E164}">{ICONS['phone']}اتصال {ltr(site.PHONE_DISPLAY)}</a></li>
<li><a href="mailto:{site.EMAIL}">{ICONS['mail']}{ltr(site.EMAIL)}</a></li>
</ul></div>
{builder('hb', None, 'الصفحة الرئيسية')}
</div>
</div></section>
</main>
"""
    home_url = url("/")
    nodes = [
        {
            "@type": "WebPage", "@id": home_url + "#webpage", "url": home_url, "name": h["title"],
            "description": h["description"], "inLanguage": "ar-SA", "isPartOf": {"@id": SITE_ID},
            "about": {"@id": ORG_ID}, "datePublished": site.UPDATED_ISO, "dateModified": site.UPDATED_ISO,
        },
        {
            "@type": "ItemList", "@id": home_url + "#categories", "name": "فئات IGA Lines",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": c["name"], "url": url(cat_path(c))}
                                for i, c in enumerate(ORDERED)],
        },
        faq_node(home_url, h["faq"]),
    ]
    p = dict(path="/", title=h["title"], description=h["description"], og="home",
             og_alt="IGA Lines — مكائن وخطوط آلية جديدة", jsonld=jsonld(nodes))
    write("/", page(p, body))


def build_contact():
    ct = home_content.CONTACT
    prep = "".join(f"<li>{md(x)}</li>" for x in ct["prepare"])
    body = f"""<main id="main">
<section class="hero">
{hero_bg()}
<div class="wrap">
<nav class="crumbs" aria-label="مسار التصفح"><ol><li><a href="/">الرئيسية</a></li><li aria-current="page">تواصل معنا</li></ol></nav>
{rail_title(ct['h1_main'], ct['h1_tail'])}
<p class="lede">{md(ct['lead'])}</p>
<div class="btn-row">
<a class="btn btn-primary" href="{wa('مرحبًا IGA Lines، أرغب بعرض سعر.')}" target="_blank" rel="noopener">{ICONS['wa']}واتساب {ltr(site.PHONE_DISPLAY)}</a>
<a class="btn btn-outline" href="tel:{site.PHONE_E164}">{ICONS['phone']}اتصال {ltr(site.PHONE_DISPLAY)}</a>
<a class="btn btn-outline" href="mailto:{site.EMAIL}">{ICONS['mail']}{ltr(site.EMAIL)}</a>
</div>
</div>
</section>
<section class="band band-dark" id="quote" aria-labelledby="prep"><div class="wrap">
{section_head(ct['prepare_title'], 'prep')}
<div class="quote-grid">
<div class="quote-info"><ul class="checklist">{prep}</ul></div>
{builder('cb', None, 'صفحة التواصل')}
</div>
</div></section>
<section class="band band-steel" aria-labelledby="cats"><div class="wrap">{section_head('تصفّح الفئات', 'cats')}<div class="others">{''.join(
        f'<a class="other" href="{cat_path(o)}">{picture(o["products"][0]["image"], o["products"][0]["orientation"], "", "112px", style="object-position:50% 30%")}<div><h3>{e(o["name"])}</h3><p>{e(o["card_lead"])}</p></div></a>'
        for o in ORDERED)}</div></div></section>
</main>
"""
    page_url = url("/contact/")
    nodes = [
        {"@type": "ContactPage", "@id": page_url + "#webpage", "url": page_url, "name": ct["title"],
         "description": ct["description"], "inLanguage": "ar-SA", "isPartOf": {"@id": SITE_ID},
         "about": {"@id": ORG_ID}, "breadcrumb": {"@id": page_url + "#breadcrumb"}},
        breadcrumb_node(page_url, [("الرئيسية", url("/")), ("تواصل معنا", page_url)]),
    ]
    p = dict(path="/contact/", title=ct["title"], description=ct["description"], og="home",
             og_alt="تواصل مع IGA Lines", jsonld=jsonld(nodes))
    write("/contact/", page(p, body))


def build_404():
    nf = home_content.NOT_FOUND
    cats = "".join(
        f'<a class="other" href="{cat_path(o)}">{picture(o["products"][0]["image"], o["products"][0]["orientation"], "", "112px", style="object-position:50% 30%")}<div><h3>{e(o["name"])}</h3><p>{e(o["card_lead"])}</p></div></a>'
        for o in ORDERED)
    body = f"""<main id="main">
<section class="hero">
{hero_bg()}
<div class="wrap">
{rail_title(nf['h1_main'], None)}
<p class="lede">{md(nf['lead'])}</p>
<div class="btn-row"><a class="btn btn-primary" href="/">الصفحة الرئيسية</a>
<a class="btn btn-outline" href="{wa('مرحبًا IGA Lines، أبحث عن صفحة في موقعكم.')}" target="_blank" rel="noopener">{ICONS['wa']}راسلنا عبر واتساب</a></div>
</div></section>
<section class="band band-steel"><div class="wrap"><div class="others">{cats}</div></div></section>
</main>
"""
    p = dict(path="/404.html", title=nf["title"], description=nf["lead"], og="home", robots="noindex, follow")
    (PUB / "404.html").write_text(page(p, body), encoding="utf-8")


def write(path, text):
    out = PUB / path.strip("/") / "index.html" if path != "/" else PUB / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- site files

def build_static():
    (PUB / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    for f in (SRC / "fonts").glob("*.woff2"):
        shutil.copy2(f, PUB / "assets" / "fonts" / f.name)
    for old in (PUB / "assets").glob("site.*.js"):
        old.unlink()
    (PUB / "assets" / JS_NAME).write_text(JS_SRC, encoding="utf-8")
    shutil.copy2(SRC / "svg" / "favicon.svg", PUB / "favicon.svg")
    for f in ("favicon.ico", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        shutil.copy2(SRC / "images" / f, PUB / f)

    (PUB / "site.webmanifest").write_text(json.dumps({
        "name": site.NAME, "short_name": site.NAME, "lang": "ar", "dir": "rtl",
        "start_url": "/", "display": "standalone", "background_color": "#050a14", "theme_color": "#050a14",
        "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    pages = [("/", "1.0")] + [(cat_path(c), "0.9") for c in ORDERED] + [("/contact/", "0.6")]
    items = []
    for path, prio in pages:
        imgs = ""
        c = next((c for c in ORDERED if cat_path(c) == path), None)
        if c:
            kind = c["products"][0]["orientation"]
            imgs = "".join(
                f"<image:image><image:loc>{img_url(p['image'], kind)}</image:loc></image:image>"
                for p in c["products"])
        items.append(f"<url><loc>{url(path)}</loc><lastmod>{site.UPDATED_ISO}</lastmod>"
                     f"<priority>{prio}</priority>{imgs}</url>")
    (PUB / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "\n".join(items) + "\n</urlset>\n", encoding="utf-8")

    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
               "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "Bingbot",
               "DuckAssistBot", "meta-externalagent", "CCBot"]
    robots = ["# IGA Lines — every page is open to search engines and AI assistants.", "User-agent: *", "Allow: /",
              "Disallow: /_source/", ""]
    robots += ["# AI search and assistant crawlers are welcome."]
    for b in ai_bots:
        robots += [f"User-agent: {b}", "Allow: /", "Disallow: /_source/", ""]
    robots += [f"Sitemap: {url('/sitemap.xml')}", ""]
    (PUB / "robots.txt").write_text("\n".join(robots), encoding="utf-8")

    llms = [f"# {site.NAME} ({site.NAME_AR})", "",
            f"> {site.NAME} supplies new automated machines and lines in Saudi Arabia: self-service vending "
            "machines, packaging machines, recycling machines and automatic car wash systems. "
            "The site is in Arabic. Each category page explains the solutions, what to compare before "
            "buying, how to judge a project's feasibility, and common questions.", "",
            f"- Phone and WhatsApp: {site.PHONE_DISPLAY}",
            f"- Email: {site.EMAIL}",
            "- Service area: Saudi Arabia",
            "- Machine images on the site are illustrations; final specifications come with each technical offer.", "",
            "## Categories", ""]
    for c in ORDERED:
        sols = "، ".join(p["name"] for p in c["products"])
        llms.append(f"- [{c['h1_main']} {c['h1_tail']}]({url(cat_path(c))}): {plain(c['description'])} الحلول: {sols}.")
    llms += ["", "## Contact", "", f"- [تواصل مع IGA Lines]({url('/contact/')}): WhatsApp, phone and email.", ""]
    (PUB / "llms.txt").write_text("\n".join(llms), encoding="utf-8")

    (PUB / ".htaccess").write_text(htaccess(), encoding="utf-8")


def htaccess():
    host = re.escape(HOST)
    return rf"""# IGA Lines — Apache/LiteSpeed settings (Hostinger reads this file).
Options -Indexes
DirectoryIndex index.html
ErrorDocument 404 /404.html

RewriteEngine On

# One address for every page: https://{HOST}/ (Hostinger already sends http to https)
RewriteCond %{{HTTP_HOST}} ^www\.{host}$ [NC]
RewriteRule ^ https://{HOST}%{{REQUEST_URI}} [L,R=301]

# The build folder and repository files are not part of the website
RewriteRule (^|/)(_source|\.git|\.claude|\.kilo)(/|$) - [F,L]
RewriteRule ^(README\.md|\.gitignore)$ - [F,L]

# Addresses from the previous website
RewriteRule ^products(\.html)?(/.*)?$ / [R=301,L]
RewriteRule ^categories/(construction-equipment|agricultural-equipment)(\.html)?/?$ / [R=301,L]
RewriteRule ^categories/(vending-machines|packaging-machines|recycling-lines)\.html$ /categories/$1/ [R=301,L]

AddType image/avif .avif
AddType font/woff2 .woff2
AddType application/manifest+json .webmanifest
AddDefaultCharset utf-8
AddCharset utf-8 .txt .xml .webmanifest

<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css text/plain text/xml application/xml application/javascript application/json application/ld+json application/manifest+json image/svg+xml
</IfModule>

<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
  <FilesMatch "\.html$">
    Header set Cache-Control "no-cache"
  </FilesMatch>
  <FilesMatch "^site\.[0-9a-f]+\.js$">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </FilesMatch>
  <FilesMatch "\.(avif|webp|jpg|png|svg|ico|woff2)$">
    Header set Cache-Control "public, max-age=2592000"
  </FilesMatch>
</IfModule>
"""


# ---------------------------------------------------------------- social share images

def og_cards():
    cards = [("home", home_content.HOME["h1_main"], home_content.HOME["h1_tail"],
              ["iga-flower-vending", "iga-pack-pouch", "iga-recycle-sort", "iga-wash-tunnel"])]
    for c in ORDERED:
        cards.append((c["slug"], c["h1_main"], c["h1_tail"], [p["image"] for p in c["products"][:3]]))
    return cards


def build_og():
    out = PUB / "og"
    out.mkdir(parents=True, exist_ok=True)
    stamp_file = out / ".stamp"
    font_dir = (PUB / "assets" / "fonts").as_uri()
    stamp = hashlib.sha1((site.DOMAIN + json.dumps(og_cards(), ensure_ascii=False)
                          + (SRC / "svg" / "logo.svg").read_text()).encode()).hexdigest()
    have_all = all((out / f"{slug}.jpg").exists() for slug, *_ in og_cards())
    if have_all and not REBUILD_OG and stamp_file.exists() and stamp_file.read_text() == stamp:
        return
    if not CHROME.exists():
        print("! Chrome not found; social share images not rendered")
        return
    with tempfile.TemporaryDirectory() as tmp:
        for slug, main, tail, imgs in og_cards():
            tiles = "".join(f'<div class="t"><img src="{(SRC / "images" / (s + ".png")).as_uri()}"></div>' for s in imgs)
            doc = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:K;src:url("{font_dir}/noto-kufi-arabic-700.woff2")}}
@font-face{{font-family:P;src:url("{font_dir}/ibm-plex-sans-arabic-600.woff2")}}
html,body{{margin:0;width:1200px;height:630px;overflow:hidden;background:#050a14}}
body{{position:relative;font-family:K;color:#fff}}
.glow{{position:absolute;inset:0;background:radial-gradient(55% 60% at 70% 45%,rgba(31,95,255,.28),transparent 70%)}}
.logo{{position:absolute;top:44px;right:64px;height:54px}}
.logo svg{{height:54px;width:auto}}
h1{{position:absolute;right:64px;top:168px;width:640px;margin:0;font-size:{64 if len(main) < 20 else 54}px;line-height:1.34;font-weight:700}}
.m{{display:block;background:linear-gradient(to bottom,transparent calc(1.0035em - 9px),rgba(31,95,255,.2) calc(1.0035em - 5px),#8cc4ff calc(1.0035em - 1.5px),#8cc4ff calc(1.0035em + 1.5px),rgba(31,95,255,.2) calc(1.0035em + 5px),transparent calc(1.0035em + 9px));background-size:100% 1.34em;margin-right:-64px;padding-right:64px}}
.n{{display:inline-block;width:.3em;height:.3em;border-radius:50%;margin-right:.22em;vertical-align:-.15em;background:#6aaeff;box-shadow:0 0 .5em .12em rgba(31,95,255,.8)}}
.tail{{display:block;margin-top:18px;font:600 28px/1.5 P;color:#a3b4cf}}
.site{{position:absolute;right:64px;bottom:46px;font:600 24px/1 P;color:#6aaeff;direction:ltr}}
.tiles{{position:absolute;left:48px;top:48px;bottom:48px;width:420px;display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.t{{border-radius:18px;overflow:hidden;background:#dde4ed}}
.t img{{width:100%;height:100%;object-fit:cover;object-position:50% 30%}}
.tiles.three .t:first-child{{grid-row:span 2}}
</style></head><body><div class="glow"></div><div class="logo">{logo("o")}</div>
<h1><span class="m">{e(main)}<span class="n"></span></span><span class="tail">{lines(tail)}</span></h1>
<div class="site">{HOST}</div>
<div class="tiles{' three' if len(imgs) == 3 else ''}">{tiles}</div></body></html>"""
            src = Path(tmp) / f"{slug}.html"
            src.write_text(doc, encoding="utf-8")
            png = Path(tmp) / f"{slug}.png"
            subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--allow-file-access-from-files", "--force-device-scale-factor=1",
                            "--window-size=1200,630", "--virtual-time-budget=3000",
                            f"--screenshot={png}", src.as_uri()],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            Image.open(png).convert("RGB").save(out / f"{slug}.jpg", "JPEG", quality=84, optimize=True, progressive=True)
    stamp_file.write_text(stamp)
    print("rendered social share images")


# ---------------------------------------------------------------- main

def main():
    PUB.mkdir(exist_ok=True)
    for stale in ("index.html", "404.html"):
        (PUB / stale).unlink(missing_ok=True)
    for d in ("categories", "contact"):
        shutil.rmtree(PUB / d, ignore_errors=True)
    build_static()
    build_home()
    for c in ORDERED:
        build_category(c)
    build_contact()
    build_404()
    build_og()
    keep = {f"{stem}-{w}.{fmt}" for stem, ws in IMAGES.items() for w, _ in ws for fmt in ("avif", "webp")}
    for f in (PUB / "img").iterdir():
        if f.name not in keep:
            f.unlink()
    files = [f for f in site_files() if f.is_file()]
    total = sum(f.stat().st_size for f in files)
    pages = sum(1 for f in files if f.suffix == ".html")
    print(f"built {pages} pages · website files {total / 1e6:.1f} MB · css {len(CSS) / 1024:.1f} KB inline · {site.DOMAIN}")


SITE_DIRS = ("assets", "img", "og", "categories", "contact")
SITE_ROOT_FILES = ("index.html", "404.html", "robots.txt", "sitemap.xml", "llms.txt", "site.webmanifest",
                   ".htaccess", "favicon.ico", "favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png")


def site_files():
    """Everything the build owns in the repository root, and nothing else."""
    for name in SITE_ROOT_FILES:
        if (PUB / name).exists():
            yield PUB / name
    for d in SITE_DIRS:
        if (PUB / d).exists():
            yield from (PUB / d).rglob("*")


if __name__ == "__main__":
    main()
