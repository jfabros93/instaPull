"""/api/state — the team's Keep/Remove decisions and photographer entries.

GET  returns {"decisions": {key: doc}, "photographers": {key: doc}}
POST takes {"ops": [{"op": "set"|"delete", "collection", "key", "value"?}]}

Both need the X-Team-Password header to match the TEAM_PASSWORD environment variable.
"""
import hmac, json, os, re, sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import store  # noqa: E402

KEY_RE = re.compile(r"^[A-Za-z0-9_\-.~:@+]{1,300}$")
MAX_BODY = 200_000
MAX_DOC = 4_000
MAX_OPS = 100


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self._authorized():
            return
        try:
            self._json(200, store.read_all())
        except Exception as exc:
            self._json(502, {"error": f"Couldn't read the review store: {exc}"})

    def do_POST(self):
        if not self._authorized():
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._json(413, {"error": "Too much at once."})
            ops = json.loads(self.rfile.read(n) or b"{}").get("ops")
            if not isinstance(ops, list) or not 0 < len(ops) <= MAX_OPS:
                return self._json(400, {"error": "Send 1 to 100 ops."})
            for o in ops:
                problem = _check(o)
                if problem:
                    return self._json(400, {"error": problem})
        except ValueError:
            return self._json(400, {"error": "The body isn't JSON."})
        try:
            store.apply(ops)
        except Exception as exc:
            return self._json(502, {"error": f"Couldn't save: {exc}"})
        self._json(200, {"ok": True})

    def _authorized(self):
        expected = os.environ.get("TEAM_PASSWORD") or ""
        if not expected:
            self._json(503, {"error": "TEAM_PASSWORD isn't set for this deployment."})
            return False
        given = self.headers.get("X-Team-Password") or ""
        if not hmac.compare_digest(given.encode(), expected.encode()):
            self._json(401, {"error": "Wrong team password."})
            return False
        return True

    def _json(self, code, data):
        body = json.dumps(data, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _check(o):
    if not isinstance(o, dict) or o.get("op") not in ("set", "delete"):
        return "Each op needs op set or delete."
    if o.get("collection") not in store.COLLECTIONS:
        return "Unknown collection."
    if not isinstance(o.get("key"), str) or not KEY_RE.match(o["key"]):
        return "Bad key."
    if o["op"] == "set":
        if not isinstance(o.get("value"), dict) or len(json.dumps(o["value"])) > MAX_DOC:
            return "Each value must be an object under 4 KB."
    return None
