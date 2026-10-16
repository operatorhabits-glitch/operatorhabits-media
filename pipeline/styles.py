"""Extra carousel looks, so the grid is not one template repeated (added 2026-10-16).

Use per slide or spec-wide in a carousel spec:  "style": "brand" (default) | "poster" | "journal"

poster  — black slide, huge condensed uppercase type (Anton), one statement that reads at thumbnail size.
          title: the statement; "*word" = lime accent. body (optional): one small line under it.
          kicker (optional): small lime label at the top, e.g. "RULE 01". Default "OPERATOR HABITS".
journal — off-white paper, serif ink text (Lora), a slow reflective note made to be saved.
          title (optional): heading in italic, "size" sets it (default 64; 80+ for a hook).
          body: the note at 46 px (shrinks to fit); "\\n" = new line, "\\n\\n" = new paragraph.
          "*word" = italic, "_word" = underlined. Footer: "@operatorhabits".
Both keep the slide dots and the swipe arrow of the brand style.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350
BLACK = (10, 10, 11); FG = (244, 242, 236); AC = (198, 255, 61)
PAPER = (246, 243, 236); INK = (28, 27, 25); MUTED = (120, 116, 108)
_f = {}


def font(name, size, var=None):
    k = (name, size, var)
    if k not in _f:
        f = ImageFont.truetype(os.path.join(HERE, "fonts", name), size)
        if var:
            f.set_variation_by_axes([{"Regular": 400, "Medium": 500, "SemiBold": 600, "Bold": 700}[var]])
        _f[k] = f
    return _f[k]


def _dots(d, i, n, on, off, x0=96):
    for j in range(n):
        cx = x0 + j * 30
        d.ellipse([cx, 1232, cx + 12, 1244], fill=on if j == i else off)
    if i < n - 1:
        ax = W - x0; c = off if on == AC else on
        d.line([ax - 70, 1238, ax, 1238], fill=c, width=5)
        d.line([ax - 22, 1218, ax, 1238, ax - 22, 1258], fill=c, width=5, joint="curve")


def _wrap(d, words, fnt, maxw, clean=lambda w: w):
    lines, cur = [], []
    for w in words:
        t = " ".join(clean(x) for x in cur + [w])
        if cur and d.textlength(t, font=fnt) > maxw:
            lines.append(cur); cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def poster(s, i, n):
    im = Image.new("RGB", (W, H), BLACK); d = ImageDraw.Draw(im)
    X0, MAXW = 84, W - 168
    kicker = s.get("kicker", "OPERATOR HABITS")
    d.text((X0, 96), kicker.upper(), font=font("Inter-Bold.otf", 30), fill=AC)
    words = s["title"].upper().split(); clean = lambda w: w.lstrip("*")
    size = 200
    while size > 80:
        f = font("Anton-Regular.ttf", size)
        lines = _wrap(d, words, f, MAXW, clean)
        lh = int(size * 1.0)
        body_h = 90 if s.get("body") else 0
        if len(lines) * lh + body_h <= 1000 and all(d.textlength(" ".join(map(clean, l)), font=f) <= MAXW for l in lines):
            break
        size -= 6
    total = len(lines) * lh + (90 if s.get("body") else 0)
    y = max(170, (H - total) // 2 - 10)
    for l in lines:
        x = X0
        for w in l:
            acc = w.startswith("*"); w = clean(w)
            d.text((x, y), w, font=f, fill=AC if acc else FG)
            x += d.textlength(w + " ", font=f)
        y += lh
    if s.get("body"):
        y += 36
        bf = font("Inter-Bold.otf", 40)
        for l in _wrap(d, s["body"].split(), bf, MAXW):
            d.text((X0, y), " ".join(l), font=bf, fill=(170, 168, 162)); y += 54
    _dots(d, i, n, AC, (90, 90, 92), X0)
    return im


def journal(s, i, n):
    im = Image.new("RGB", (W, H), PAPER); d = ImageDraw.Draw(im)
    X0, MAXW = 110, W - 220
    clean = lambda w: w.lstrip("*_")
    tsize = s.get("size", 64)
    lines = [ln.split() if ln.strip() else None for ln in s.get("body", "").split("\n")]
    size = 46
    while True:
        laid = []  # (words, size, italic_all) or ("gap", px)
        if s.get("title"):
            tf = font("Lora-Italic-Variable.ttf", tsize, "Regular")
            for l in _wrap(d, s["title"].split(), tf, MAXW, clean):
                laid.append((l, tsize, True))
            if any(lines):
                laid.append(("gap", int(tsize * 0.8)))
        reg = font("Lora-Variable.ttf", size, "Regular")
        for ln in lines:
            if ln is None:
                laid.append(("gap", int(size * 0.8))); continue
            for l in _wrap(d, ln, reg, MAXW, clean):
                laid.append((l, size, False))
        h = sum(e[1] if e[0] == "gap" else int(e[1] * 1.42) for e in laid)
        if h <= 960 or (size <= 32 and tsize <= 40):
            break
        if size > 32: size -= 2
        else: tsize -= 4
    y = max(150, (H - h) // 2 - 30)
    for e in laid:
        if e[0] == "gap":
            y += e[1]; continue
        words, sz, all_it = e
        reg = font("Lora-Variable.ttf", sz, "Regular"); it = font("Lora-Italic-Variable.ttf", sz, "Regular")
        x = X0
        for w in words:
            italic = all_it or w.startswith("*"); under = w.startswith("_"); w = clean(w)
            fnt = it if italic else reg
            d.text((x, y), w, font=fnt, fill=INK)
            wl = d.textlength(w, font=fnt)
            if under:
                d.line([x, y + int(sz * 1.2), x + wl, y + int(sz * 1.2)], fill=INK, width=2)
            x += wl + d.textlength(" ", font=fnt)
        y += int(sz * 1.42)
    d.text((X0, 1170), "@operatorhabits", font=font("Lora-Italic-Variable.ttf", 30, "Regular"), fill=MUTED)
    _dots(d, i, n, INK, (200, 196, 188), X0)
    return im


def render(style, s, i, n):
    return {"poster": poster, "journal": journal}[style](s, i, n)
