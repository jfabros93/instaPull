"""Shared review state: Keep/Remove decisions and photographer entries.

Each collection is one Redis hash (field = document key, value = JSON). On Vercel the
Upstash Redis integration provides KV_REST_API_URL / KV_REST_API_TOKEN. Without them
(local development) the state lives in .local-state.json next to the project.
"""
import json, os, threading, urllib.request

COLLECTIONS = ("decisions", "photographers")
PREFIX = "candid:"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "seed.json")
LOCAL = os.path.join(ROOT, ".local-state.json")

URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")


def configured():
    return bool(URL and TOKEN)


def _redis(commands):
    req = urllib.request.Request(URL.rstrip("/") + "/pipeline", data=json.dumps(commands).encode(),
                                 headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        out = json.loads(r.read())
    for o in out:
        if o.get("error"):
            raise RuntimeError(o["error"])
    return [o.get("result") for o in out]


_lock = threading.Lock()


def _local_load():
    try:
        with open(LOCAL) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {c: {} for c in COLLECTIONS}


def _seed():
    """Copy the marks made in the first (claude.ai) version of the app, once."""
    if not os.path.exists(SEED):
        return
    with open(SEED) as f:
        seed = json.load(f)
    if configured():
        if not _redis([["SET", PREFIX + "seeded", "1", "NX"]])[0]:
            return
        cmds = [["HSETNX", PREFIX + c, k, json.dumps(v)] for c in COLLECTIONS for k, v in seed.get(c, {}).items()]
        if cmds:
            _redis(cmds)
    else:
        with _lock:
            state = _local_load()
            if state.get("seeded"):
                return
            for c in COLLECTIONS:
                for k, v in seed.get(c, {}).items():
                    state.setdefault(c, {}).setdefault(k, v)
            state["seeded"] = True
            with open(LOCAL, "w") as f:
                json.dump(state, f)


def read_all():
    _seed()
    if configured():
        res = _redis([["HGETALL", PREFIX + c] for c in COLLECTIONS])
        out = {}
        for c, flat in zip(COLLECTIONS, res):
            flat = flat or []
            out[c] = {flat[i]: json.loads(flat[i + 1]) for i in range(0, len(flat), 2)}
        return out
    state = _local_load()
    return {c: state.get(c, {}) for c in COLLECTIONS}


def apply(ops):
    """ops: [{"op": "set"|"delete", "collection", "key", "value"?}]"""
    if configured():
        cmds = []
        for o in ops:
            h = PREFIX + o["collection"]
            cmds.append(["HSET", h, o["key"], json.dumps(o["value"])] if o["op"] == "set" else ["HDEL", h, o["key"]])
        if cmds:
            _redis(cmds)
        return
    with _lock:
        state = _local_load()
        for o in ops:
            coll = state.setdefault(o["collection"], {})
            if o["op"] == "set":
                coll[o["key"]] = o["value"]
            else:
                coll.pop(o["key"], None)
        with open(LOCAL, "w") as f:
            json.dump(state, f)
