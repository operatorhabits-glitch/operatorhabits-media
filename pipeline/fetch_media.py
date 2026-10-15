#!/usr/bin/env python3
"""Find and download real stock footage / photos (free licences, no attribution required, no cost).

Usage:
  python3 pipeline/fetch_media.py video "man typing laptop night" [--n 3]
  python3 pipeline/fetch_media.py photo "coffee desk morning light" [--n 3]

Sources, in order: Pexels (env PEXELS_API_KEY), Pixabay (env PIXABAY_API_KEY). Both keys are free.
Portrait (9:16 / 4:5) results are preferred. Files land in pipeline/.cache/stock/ (git-ignored: the raw
stock files are never published from this repo, only our edited reels and slides). Every download is
appended to content/media_credits.md with source page, author and licence, so we can always show where
a clip came from. Prints JSON: [{"path": ..., "w": ..., "h": ..., "dur": ..., "page": ..., "author": ...}]
Never use a clip that shows a recognisable brand, logo or a famous person, and never present a stock
person as the account owner or as a customer.
"""
import json, os, sys, urllib.parse, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, ".cache", "stock")
CREDITS = os.path.join(ROOT, "content", "media_credits.md")
UA = {"User-Agent": "operatorhabits-pipeline/1.0"}


def get(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def download(url, path):
    if not os.path.exists(path):
        data = get(url)
        with open(path, "wb") as f:
            f.write(data)
    return path


def pexels(kind, q, n):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    h = {"Authorization": key}
    if kind == "video":
        u = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
            {"query": q, "orientation": "portrait", "size": "medium", "per_page": 15})
        res = json.loads(get(u, h)).get("videos", [])
        out = []
        for v in res:
            if not 5 <= v.get("duration", 0) <= 60:
                continue
            files = [f for f in v["video_files"] if f.get("file_type") == "video/mp4" and f.get("height")]
            files = [f for f in files if f["height"] >= f["width"]] or files
            if not files:
                continue
            f = min(files, key=lambda f: abs(f["height"] - 1920))  # closest to 1080x1920
            p = download(f["link"], os.path.join(OUT, f"pexels_{v['id']}.mp4"))
            out.append({"path": p, "w": f["width"], "h": f["height"], "dur": v["duration"],
                        "page": v["url"], "author": v["user"]["name"], "licence": "Pexels License"})
            if len(out) >= n:
                break
        return out
    u = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": q, "orientation": "portrait", "per_page": 15})
    res = json.loads(get(u, h)).get("photos", [])
    out = []
    for ph in res[:n]:
        p = download(ph["src"]["large2x"], os.path.join(OUT, f"pexels_{ph['id']}.jpg"))
        out.append({"path": p, "w": ph["width"], "h": ph["height"], "page": ph["url"],
                    "author": ph["photographer"], "licence": "Pexels License"})
    return out


def pixabay(kind, q, n):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return None
    if kind == "video":
        u = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": key, "q": q, "per_page": 20, "safesearch": "true"})
        out = []
        for v in json.loads(get(u)).get("hits", []):
            vs = v["videos"]; f = vs.get("large") or vs.get("medium")
            if not f or not f.get("url") or not 5 <= v.get("duration", 0) <= 60:
                continue
            p = download(f["url"], os.path.join(OUT, f"pixabay_{v['id']}.mp4"))
            out.append({"path": p, "w": f["width"], "h": f["height"], "dur": v["duration"],
                        "page": v["pageURL"], "author": v["user"], "licence": "Pixabay Content License"})
            if len(out) >= n:
                break
        return out
    u = "https://pixabay.com/api/?" + urllib.parse.urlencode(
        {"key": key, "q": q, "image_type": "photo", "orientation": "vertical", "per_page": 20, "safesearch": "true"})
    out = []
    for ph in json.loads(get(u)).get("hits", [])[:n]:
        p = download(ph["largeImageURL"], os.path.join(OUT, f"pixabay_{ph['id']}.jpg"))
        out.append({"path": p, "w": ph["imageWidth"], "h": ph["imageHeight"], "page": ph["pageURL"],
                    "author": ph["user"], "licence": "Pixabay Content License"})
    return out


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("video", "photo"):
        sys.exit(__doc__)
    kind, q = a[0], a[1]
    n = int(a[a.index("--n") + 1]) if "--n" in a else 3
    os.makedirs(OUT, exist_ok=True)
    errors = []
    for src in (pexels, pixabay):
        try:
            res = src(kind, q, n)
        except Exception as e:  # network blocked, bad key, rate limit
            errors.append(f"{src.__name__}: {e}")
            continue
        if res:
            today = datetime.date.today().isoformat()
            new = not os.path.exists(CREDITS)
            with open(CREDITS, "a") as f:
                if new:
                    f.write("# Stock media credits\n\nEvery stock clip or photo used under our edits. Raw files are not stored in this repo.\n\n"
                            "| Fetched | File | Source page | Author | Licence |\n|---|---|---|---|---|\n")
                for r in res:
                    f.write(f"| {today} | {os.path.basename(r['path'])} | {r['page']} | {r['author']} | {r['licence']} |\n")
            for r in res:
                r["path"] = os.path.relpath(r["path"], ROOT)
            print(json.dumps(res, indent=1))
            return
        if res is None:
            errors.append(f"{src.__name__}: no API key in environment")
        else:
            errors.append(f"{src.__name__}: no results for '{q}'")
    sys.exit("No stock media fetched. " + " | ".join(errors))


if __name__ == "__main__":
    main()
