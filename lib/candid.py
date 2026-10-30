"""Read the Made Goods Candid stream and shape it for the review page.

catalog() -> {"syncedAt", "streamId", "images": [...]}, every approved image with its tags,
products, full caption, photographer credit and links.
"""
import json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

from photographer import credit

STREAM_ID = "7e4da7e1-7e92-4c00-af90-c93d9d1e34a4"
API = "https://api.getcandid.com"
PAGE_SIZE = 100
PARALLEL = 8


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1 + i)


def page(n):
    url = (f"{API}/stream/page/?id={STREAM_ID}&sort=date&approvalFilter=Approved"
           f"&pageSize={PAGE_SIZE}&page={n}")
    return json.loads(get(url))["Views"]


def fetch_views():
    """Fetch pages a batch at a time until one comes back short."""
    views, start = [], 0
    with ThreadPoolExecutor(PARALLEL) as pool:
        while True:
            batch = list(pool.map(page, range(start, start + PARALLEL)))
            for b in batch:
                views += b
                if len(b) < PAGE_SIZE:
                    return views
            start += PARALLEL


def _https(url):
    return "https:" + url if url.startswith("//") else url


def record(v):
    m, e = v["Media"], v["StreamEntry"]
    items = e["Tags"]["Items"]
    user = m.get("User") or {}
    found = credit(m.get("Caption") or "")
    return {
        "id": e.get("MediaId") or m["Id"],
        "tags": sorted({t["TagId"] for t in items if t["TagType"] != "Product"}),
        "products": [t["TagId"] for t in items if t["TagType"] == "Product"],
        "user": user.get("UserName") or user.get("Id", "").split("@")[0] or m.get("Source", "upload"),
        "caption": m.get("Caption") or "",
        "photographer": found["handle"] if found else "",
        "creditHow": found["how"] if found else "",
        "link": m.get("OriginalLink") or "",
        "image": _https(m["Images"]["StandardResolution"]["Url"]),
        "type": m.get("Type", "image"),
        "date": v.get("CreatedTime", 0),
    }


def catalog():
    images = [record(v) for v in fetch_views()]
    return {"syncedAt": int(time.time() * 1000), "streamId": STREAM_ID, "images": images}


if __name__ == "__main__":
    c = catalog()
    print(f"{len(c['images'])} approved images, "
          f"{sum(1 for i in c['images'] if i['photographer'])} with a photographer")
