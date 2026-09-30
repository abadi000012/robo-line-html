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

## Analytics and WhatsApp sources (2026-10-01)

GA4 account `410318390`, property `556934542`, stream `15892752173`, measurement ID `G-57TZ7CL20R` (separate IGA Lines / Robo Line property). Search Console domain `robo-line.com` is DNS verified and the sitemap successfully submitted (6 URLs).

`_source/src/js/attribution.js` loads GA4, tracks WhatsApp/phone clicks, and appends a compact source code to WhatsApp messages, including the quote builder. Enhanced measurement is off: message text/form values are not collected. Query parameters are allowlisted before GA receives the page URL.

UTMs take precedence, followed by ad click IDs, external referrers, then the last known source retained for 30 days in first-party storage. Direct visits retain the previous source; new external referrals replace it. Missing evidence is labelled direct/unknown. Prefixes: TK = TikTok, ADW = Google Ads, HRJ = Haraj, GO = Google organic, DIR = direct/unknown. A random three-digit suffix is stored per visitor (for example TK010); it is a short reference, not a globally unique client number. Campaign names are not included in the message. Attribution does not prove a message was sent; customers can edit the prefilled message.

Use these destination patterns in your ads/listings, with a distinct non-personal campaign name in place of `website`:

- TikTok: `https://robo-line.com/?utm_source=tiktok&utm_medium=paid_social&utm_campaign=website`
- Google Ads: `https://robo-line.com/?utm_source=google&utm_medium=cpc&utm_campaign=website`
- Haraj: `https://robo-line.com/?utm_source=haraj&utm_medium=referral&utm_campaign=website`

The same parameters can be used on category page URLs. Do not tag internal navigation links. Ad accounts/listing URLs have not been changed by this website deployment.
