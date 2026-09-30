"""Build the IGA Lines logo as SVG, plus favicon files.

Geometry is traced from the neon logo supplied by the client
(src/images/iga-lines-neon-logo.png, measured in a crop starting at 120,280):
heavy I-G-A letters cut by a horizontal band; inside the band runs the glowing
line in four segments, with a node in the A where its crossbar would be.
"Lines" sits on the same baseline.

Run:  .venv/bin/python tools/make_logo.py
"""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SVG_OUT = ROOT / "src" / "svg"
IMG_OUT = ROOT / "src" / "images"
SVG_OUT.mkdir(parents=True, exist_ok=True)

TOP, BASE = 23, 297                  # cap top and baseline of I-G-A
BAND = (148, 197)                    # the cut through the letters
LINE_Y, LINE_H = 164, 20             # the glowing line inside the cut
NODE = (598, 174, 30)

LETTER_TOP, LETTER_BOTTOM = "#2456DB", "#12348F"
GLOW = "#3A8DFF"


def a_letter():
    # outer flat top with softened corners, open counter below the apex
    return ("M540 33Q545 23 556 23H639Q650 23 655 33L801 297H710L598 92L486 297H394Z")


def g_letter():
    # left half-circle, straight top arm cut parallel to the A's leg,
    # counter with rounded left side, spur rising from the bottom arm,
    # lower-right edge running parallel to the A's leg.
    return ("M259 23H467L412 127H292"
            "A52 52 0 0 0 292 232H332V174H448L386 297H259"
            "A137 137 0 0 1 259 23Z")


def i_letter():
    return f"M20 {TOP}H103V{BASE}H20Z"


def line_segments():
    y, h = LINE_Y, LINE_H
    r = h / 2
    segs = [(20, 103), (124, 186), (241, 574)]
    d = "".join(f'<rect x="{a}" y="{y}" width="{b - a}" height="{h}" rx="3"/>' for a, b in segs)
    # last segment ends on a slant that follows the A's right leg
    d += f'<path d="M625 {y}H741L752 {y + h}H625Z"/>'
    cx, cy, rr = NODE
    d += f'<circle cx="{cx}" cy="{cy}" r="{rr}"/>'
    return d


def word_paths(text, x, cap_h, font_file, tracking=0):
    font = TTFont(ROOT / "tools" / "fonts-src" / font_file)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    s = cap_h / font["OS/2"].sCapHeight
    d, cursor = [], 0
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        gs[name].draw(TransformPen(pen, (s, 0, 0, -s, x + cursor * s, BASE)))
        d.append(pen.getCommands())
        cursor += font["hmtx"][name][0] + tracking
    return " ".join(d), x + cursor * s


def logo_svg(uid="l"):
    word, end = word_paths("Lines", 822, 155, "Poppins-SemiBold.ttf", tracking=-62)
    w = round(end) + 22
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} 320" role="img" aria-label="IGA Lines">'
        f'<defs>'
        f'<linearGradient id="{uid}g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{LETTER_TOP}"/><stop offset="1" stop-color="{LETTER_BOTTOM}"/></linearGradient>'
        f'<mask id="{uid}m"><rect width="{w}" height="320" fill="#fff"/>'
        f'<rect y="{BAND[0]}" width="{w}" height="{BAND[1] - BAND[0]}" fill="#000"/></mask>'
        f'<filter id="{uid}f" x="-5%" y="-40%" width="110%" height="180%">'
        f'<feGaussianBlur stdDeviation="7" result="b"/>'
        f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        f'</defs>'
        f'<g fill="url(#{uid}g)" mask="url(#{uid}m)"><path d="{i_letter()}"/><path d="{g_letter()}"/><path d="{a_letter()}"/></g>'
        f'<g fill="{GLOW}" filter="url(#{uid}f)">{line_segments()}<path d="{word}"/></g>'
        f'</svg>'
    )


def favicon_svg():
    # The A with its line and node, on a night-blue tile.
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="14" fill="#050A14"/>'
            f'<path d="M26 9H38L57 55H45L32 24L19 55H7Z" fill="{LETTER_TOP}"/>'
            '<rect x="7" y="33" width="50" height="8" fill="#050A14"/>'
            f'<rect x="4" y="34.5" width="56" height="5" rx="2.5" fill="{GLOW}"/>'
            f'<circle cx="32" cy="37" r="6.5" fill="{GLOW}"/>'
            '</svg>')


def favicon_png(size):
    k = 8  # draw large, then downsample for anti-aliasing
    S = size * k
    u = S / 64
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=14 * u, fill="#050A14")
    d.polygon([(26 * u, 9 * u), (38 * u, 9 * u), (57 * u, 55 * u), (45 * u, 55 * u), (32 * u, 24 * u),
               (19 * u, 55 * u), (7 * u, 55 * u)], fill=LETTER_TOP)
    d.rectangle([7 * u, 33 * u, 57 * u, 41 * u], fill="#050A14")
    d.rounded_rectangle([4 * u, 34.5 * u, 60 * u, 39.5 * u], radius=2.5 * u, fill=GLOW)
    d.ellipse([25.5 * u, 30.5 * u, 38.5 * u, 43.5 * u], fill=GLOW)
    return im.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    (SVG_OUT / "logo.svg").write_text(logo_svg(), encoding="utf-8")
    (SVG_OUT / "favicon.svg").write_text(favicon_svg(), encoding="utf-8")
    favicon_png(180).convert("RGB").save(IMG_OUT / "apple-touch-icon.png")
    favicon_png(192).save(IMG_OUT / "icon-192.png")
    favicon_png(512).save(IMG_OUT / "icon-512.png")
    favicon_png(64).save(IMG_OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("logo.svg", len((SVG_OUT / "logo.svg").read_text()), "bytes")
