"""Background media (real photos / video clips) for reels and carousels.

A background is given in a spec as either a path string or a dict:
  "bg": "pipeline/.cache/stock/pexels_123.mp4"
  "bg": {"src": "...mp4|jpg|png", "start": 2.5, "focus": [0.5, 0.4], "zoom": 1.08, "dim": 0.5}
- start  (video only) seconds into the clip to begin
- focus  crop centre as fractions of the source (x, y); default centre
- zoom   photos: slow push-in from 1.0 to this value over the scene (Ken Burns); default 1.07
- dim    0..1 how dark the grade is (default 0.52). Text always gets a legibility scrim too.
Relative paths resolve against the repo root.
"""
import os, subprocess, numpy as np
from PIL import Image, ImageEnhance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_EXT = (".mp4", ".mov", ".webm", ".m4v", ".mkv")


def norm(bg):
    if not bg:
        return None
    if isinstance(bg, str):
        bg = {"src": bg}
    bg = dict(bg)
    p = bg["src"]
    bg["path"] = p if os.path.isabs(p) else os.path.join(ROOT, p)
    if not os.path.exists(bg["path"]):
        raise FileNotFoundError(f"background not found: {p}")
    bg["video"] = bg["path"].lower().endswith(VIDEO_EXT)
    return bg


def cover(im, W, H, focus=(0.5, 0.5), zoom=1.0):
    """Scale to cover W x H (times zoom) and crop around focus."""
    sw, sh = im.size
    s = max(W / sw, H / sh) * zoom
    nw, nh = max(W, round(sw * s)), max(H, round(sh * s))
    im = im.resize((nw, nh), Image.LANCZOS if zoom == 1.0 else Image.BILINEAR)
    cx, cy = focus[0] * nw, focus[1] * nh
    x = int(min(max(cx - W / 2, 0), nw - W)); y = int(min(max(cy - H / 2, 0), nh - H))
    return im.crop((x, y, x + W, y + H))


def grade(im, dim=0.52, sat=0.78):
    """Brand grade: slightly desaturated, darkened, cool-neutral blacks."""
    im = ImageEnhance.Color(im.convert("RGB")).enhance(sat)
    a = np.asarray(im).astype(np.float32)
    a = a * (1 - dim) + np.array([14, 15, 17], np.float32) * dim * 0.6
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


_scrims = {}
def scrim(W, H, strength=0.55, centre=0.5):
    """Vertical darkening band around the text area plus top/bottom vignette (RGBA)."""
    k = (W, H, strength, centre)
    if k not in _scrims:
        y = np.linspace(0, 1, H)[:, None]
        band = np.exp(-((y - centre) / 0.30) ** 2) * strength
        edges = np.clip((0.18 - y) / 0.18, 0, 1) * 0.55 + np.clip((y - 0.80) / 0.20, 0, 1) * 0.6
        a = np.clip(band + edges, 0, 0.88) * 255
        a = np.repeat(a, W, axis=1).astype(np.uint8)
        rgba = np.zeros((H, W, 4), np.uint8); rgba[..., :3] = (8, 9, 10); rgba[..., 3] = a
        _scrims[k] = Image.fromarray(rgba, "RGBA")
    return _scrims[k]


def photo(bg, W, H):
    im = Image.open(bg["path"]); im.load()
    return grade(cover(im.convert("RGB"), W, H, bg.get("focus", (0.5, 0.5))), bg.get("dim", 0.52))


class Clip:
    """Sequential frame reader for one scene's background, W x H at fps. Photos get a slow push-in."""

    def __init__(self, bg, W, H, fps, dur):
        self.bg, self.W, self.H, self.fps, self.dur = bg, W, H, fps, dur
        self.proc = None; self.idx = -1; self.last = None
        if not bg["video"]:
            im = Image.open(bg["path"]).convert("RGB")
            z = bg.get("zoom", 1.07)
            self.base = cover(im, int(W * z) + 2, int(H * z) + 2, bg.get("focus", (0.5, 0.5)))

    def _vf(self):
        fx, fy = self.bg.get("focus", (0.5, 0.5))
        W, H = self.W, self.H
        return (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H}:(iw-{W})*{fx}:(ih-{H})*{fy},fps={self.fps},setsar=1")

    def _open(self, t0):
        self.close()
        cmd = ["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-ss", f"{self.bg.get('start', 0) + t0:.3f}",
               "-i", self.bg["path"], "-an", "-vf", self._vf(), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.idx = int(round(t0 * self.fps)) - 1

    def _read(self):
        n = self.W * self.H * 3
        buf = self.proc.stdout.read(n)
        if len(buf) < n:
            return self.last
        self.idx += 1
        self.last = Image.frombuffer("RGB", (self.W, self.H), buf, "raw", "RGB", 0, 1)
        return self.last

    def frame(self, t):
        """Background at t seconds into the scene (graded)."""
        t = max(t, 0)
        if not self.bg["video"]:
            u = min(t / max(self.dur, 0.1), 1)
            z = self.bg.get("zoom", 1.07); s = 1 + (z - 1) * (1 - (1 - u) ** 2)  # ease-out push-in
            bw, bh = self.base.size
            cw, ch = bw / s, bh / s
            x, y = (bw - cw) / 2, (bh - ch) / 2
            im = self.base.resize((self.W, self.H), Image.BILINEAR, box=(x, y, x + cw, y + ch))
            return grade(im, self.bg.get("dim", 0.52))
        want = int(round(t * self.fps))
        if self.proc is None or want < self.idx or want > self.idx + 90:
            self._open(t)
        im = self.last
        while self.idx < want:
            r = self._read()
            if r is None:
                break
            im = r
        if im is None:
            im = Image.new("RGB", (self.W, self.H), (14, 15, 17))
        return grade(im, self.bg.get("dim", 0.52))

    def close(self):
        if self.proc:
            self.proc.stdout.close(); self.proc.kill(); self.proc.wait(); self.proc = None
