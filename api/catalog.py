"""GET /api/catalog — every approved Candid image, read live and cached at Vercel's edge."""
import json, os, sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import candid  # noqa: E402

# Serve a cached copy for 15 minutes, then refresh in the background while the old one is still served.
CACHE = "public, max-age=0, s-maxage=900, stale-while-revalidate=86400"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            body = json.dumps(candid.catalog(), separators=(",", ":")).encode()
        except Exception as exc:
            return self._send(502, json.dumps({"error": f"Couldn't read the Candid feed: {exc}"}).encode(), "no-store")
        self._send(200, body, CACHE)

    def _send(self, code, body, cache):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
