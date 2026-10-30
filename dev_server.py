#!/usr/bin/env python3
"""Run the app locally: python3 dev_server.py, then open http://localhost:3000

Serves index.html and runs the functions in api/ the way Vercel does. Without the Upstash
variables, review marks are kept in .local-state.json. The team password defaults to "dev".
"""
import importlib.util, os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 3000))
os.environ.setdefault("TEAM_PASSWORD", "dev")
_modules = {}


def api(name):
    if name not in _modules:
        path = os.path.join(ROOT, "api", name + ".py")
        if not os.path.exists(path):
            return None
        spec = importlib.util.spec_from_file_location("api_" + name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _modules[name] = mod
    return _modules[name]


class Dev(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def _route(self, method):
        path = self.path.split("?")[0]
        if not path.startswith("/api/"):
            return False
        mod = api(path[len("/api/"):].strip("/"))
        if not mod or not hasattr(mod.handler, method):
            self.send_error(404)
            return True
        self.__class__ = mod.handler   # hand this request to the function's handler
        getattr(self, method)()
        return True

    def do_GET(self):
        if not self._route("do_GET"):
            super().do_GET()

    def do_POST(self):
        if not self._route("do_POST"):
            self.send_error(405)


if __name__ == "__main__":
    print(f"Candid Review on http://localhost:{PORT} (team password: {os.environ['TEAM_PASSWORD']})")
    ThreadingHTTPServer(("", PORT), Dev).serve_forever()
