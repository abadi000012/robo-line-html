# IGA Lines website — robo-line.com

Arabic (RTL) website for **IGA Lines** (خطوط نمو الذكاء الآلي). The brand is IGA Lines; robo-line.com is
only the web address. Hostinger deploys this repository from GitHub, and **the repository root is
the website**. Every file at the top level except `_source/` is built output.

| Page | Address |
|---|---|
| Home | `/` |
| Vending machines | `/categories/vending-machines/` |
| Packaging machines | `/categories/packaging-machines/` |
| Recycling machines | `/categories/recycling-lines/` |
| Automatic car wash | `/categories/car-wash/` |
| Contact | `/contact/` |

There are no product pages. Each example product is a section on its category page with its own
anchor (e.g. `/categories/vending-machines/#flower-vending`) and WhatsApp/call buttons.

## Change something

Edit the source in `_source/`, rebuild, commit, push.

| What | Where |
|---|---|
| Phone, WhatsApp, email, domain | `_source/src/content/site.py` |
| Home and contact page text | `_source/src/content/home.py` |
| Category text, FAQs, tables, calculators | `_source/src/content/vending.py`, `packaging.py`, `recycling.py`, `car_wash.py` |
| Colors and layout | `_source/src/css/site.css` |
| Calculators, WhatsApp message builder | `_source/src/js/site.js` |
| Images (source files) | `_source/src/images/` — replace a file with a real photo of the same name |

```sh
_source/.venv/bin/python _source/build.py        # rebuild the site (add --og to redo share images)
python3 -m http.server 5601                      # preview at http://127.0.0.1:5601
```

First time on a new machine: `python3 -m venv _source/.venv && _source/.venv/bin/pip install pillow fonttools brotli`.
The share images (`og/`) are rendered with Google Chrome.

## What the build produces

- Pages with inlined CSS, AVIF/WebP images in several sizes, and self-hosted fonts.
- JSON-LD on every page: Organization, WebSite, and per page CollectionPage/Service/ItemList/
  BreadcrumbList/FAQPage. There is no Product/price/rating markup, because no prices are published.
- `sitemap.xml`, `robots.txt` (open to search engines and AI assistants), `llms.txt`,
  `site.webmanifest`, favicons, and 1200×630 share images for WhatsApp and social links.
- `.htaccess`, which Hostinger reads. It redirects www to the bare domain and the previous site's
  addresses to the new pages, adds caching and compression, and blocks `_source/` from the web.

The logo (`_source/src/svg/logo.svg`) is redrawn from the neon IGA Lines logo by `_source/tools/make_logo.py`.
