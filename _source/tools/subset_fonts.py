"""Subset the source fonts to the characters the site uses and write WOFF2 files.

Run once after changing fonts:  .venv/bin/python tools/subset_fonts.py
Source TTFs live in tools/fonts-src/ (downloaded from github.com/google/fonts, OFL).
"""
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "fonts-src"
OUT = ROOT / "src" / "fonts"
OUT.mkdir(parents=True, exist_ok=True)

# Basic Latin, Latin-1 punctuation used in copy, general punctuation,
# bidi controls, arrows, and the full Arabic block. Shaping forms are kept
# through GSUB closure, so presentation-form code points are not needed.
UNICODES = (
    "U+0020-007E,U+00A0,U+00AB,U+00B0,U+00B7,U+00BB,U+00D7,U+00F7,"
    "U+2010-2027,U+2030,U+2039-203A,U+200C-200F,U+2066-2069,U+2190-2193,U+2212,"
    "U+0600-06FF"
)

JOBS = [
    # (source, output name, variable-axis pin)
    ("NotoKufiArabic-VF.ttf", "noto-kufi-arabic-700.woff2", {"wght": 700}),
    ("IBMPlexSansArabic-Regular.ttf", "ibm-plex-sans-arabic-400.woff2", None),
    ("IBMPlexSansArabic-SemiBold.ttf", "ibm-plex-sans-arabic-600.woff2", None),
]


def build(src_name, out_name, pin):
    font = TTFont(SRC / src_name)
    if pin:
        font = instancer.instantiateVariableFont(font, pin, updateFontNames=True)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]  # keep every OpenType feature Arabic shaping may need
    options.name_IDs = ["*"]
    options.notdef_outline = True
    options.hinting = False
    options.desubroutinize = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=subset.parse_unicodes(UNICODES))
    subsetter.subset(font)
    out = OUT / out_name
    font.flavor = "woff2"
    font.save(out)
    print(f"{out_name}: {out.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    for job in JOBS:
        build(*job)
