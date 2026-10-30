"""Find the photographer credit in an Instagram caption.

credit(caption) -> {"handle": str, "how": str} or None

"how" says which rule matched, from most to least certain:
  label    a credit label (📸, Photo by, Photography:, Shot by, Lens //, ...) followed by a handle or name
  after    a handle followed by a camera emoji ("timlenzphoto 📷")
  inferred no label, but a tagged account whose name says photo/photography ("julialynnphotography")
"""
import os, re

# Candid strips the "@" from mentions, so a handle is a bare token.
HANDLE = r"@?([A-Za-z0-9_](?:[A-Za-z0-9_.]{0,28}[A-Za-z0-9_])?)"
NAME = r"([A-Z][a-z]+(?:[ \t]+[A-Z][a-z'\-]+){1,2})"   # "Michael Hunter"
CAM = r"(?:📸|📷)️?"
SEP = (r"(?:\s*(?:[:\-–—|•/]+|by\b|credits?\b|cred\b|taken\b|courtesy\s+of\b|is\b))*\s*"
       r"(?:(?:the\s+)?(?:amazing|talented|wonderful|incredible|lovely|fabulous|brilliant|one and only)\s+)?")

LABELS = [
    CAM + r"(?:\s*(?:\+|&|and)\s*styl\w*)?",
    r"\bphoto(?:graph(?:y|ed|er|s)?|s)?(?:\s+(?:taken|captured|credits?|cred|courtesy))?(?:\s+by)?",
    r"\bimages?(?:\s+by)",
    r"\bshot\s+by",
    r"\bcaptured\s+by",
    r"\blens\b",
    r"\bp\.?c\.?(?=\s*[:\-|])",
]
LABEL_RE = re.compile(r"(?:" + LABELS[0] + r"|(?:" + "|".join(LABELS[1:]) + r")(?![A-Za-z0-9]))", re.I)
SEP_RE = re.compile(SEP, re.I)
NAME_AT = re.compile(NAME)
HANDLE_AT = re.compile(HANDLE)
AFTER_RE = re.compile(HANDLE + r"\s*[:\-–—]?\s*" + CAM)
INFER_RE = re.compile(r"(?<![#\w.@])@?([A-Za-z0-9_.]*(?:photo|photog|fotograf|fotos)[A-Za-z0-9_.]*)", re.I)

# Words that follow a label in ordinary sentences ("photo shoot", "photo is from").
_dict = set()
for path in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.txt"), "/usr/share/dict/words"):
    if os.path.exists(path):
        with open(path) as f:
            _dict = {w.strip().lower() for w in f if len(w.strip()) > 1}
        break
STOP = {
    "the", "a", "an", "of", "and", "for", "from", "in", "on", "at", "with", "this", "that", "these", "our",
    "my", "your", "is", "was", "are", "by", "to", "day", "shoot", "shoots", "session", "credit", "credits",
    "me", "us", "we", "i", "it", "taken", "styling", "stylist", "styled", "design", "designer", "via",
    "repost", "regram", "swipe", "more", "below", "above", "here", "op", "dump", "booth", "album", "oftheday",
}
GENERIC = {"photo", "photos", "photography", "photographer", "photographers", "photographs", "photooftheday",
           "photoshoot", "photographyinteriors", "photograph", "photographing", "photog", "interiorphotography",
           "photo_", "photogrid", "photography_", "photographi"}


def _ok_handle(tok, strict):
    t = tok.lower().strip(".")
    if len(t) < 3 or t in STOP or t in GENERIC or t.isdigit():
        return False
    if strict and t in _dict and not re.search(r"[._0-9]", t):
        return False   # a real word, so "Photo is from..." rather than a handle
    return True


def _label_candidates(text):
    """Yield (strength, position, credit) for each credit label in the caption."""
    pos = 0
    while True:
        m = LABEL_RE.search(text, pos)
        if not m:
            return
        pos = m.end()
        sep = SEP_RE.match(text, m.end())
        at = sep.end()
        label = text[m.start():at].lower()
        explicit = bool(re.search(r"[:\-–—|•/]|\bby\b|📸|📷|credit|cred|lens|courtesy", label))
        strength = 2 if explicit else 1
        name = NAME_AT.match(text, at)
        if name and explicit:
            yield strength, m.start(), re.sub(r"\s+(Photography|Photo|Studios?)$", "", name.group(1))
            continue
        h = HANDLE_AT.match(text, at)
        if not h:
            continue
        tok = h.group(1)
        if tok.lower() in GENERIC:
            pos = h.start()          # "📷| photography by X": read the next label instead
            continue
        if _ok_handle(tok, strict=not explicit or tok[0].isupper()):
            yield strength, m.start(), tok.strip(".")


def credit(caption):
    if not caption:
        return None
    text = caption.replace("\u2060", " ").replace("\u200b", " ").replace("\u2063", " ")
    found = sorted(_label_candidates(text), key=lambda c: (-c[0], c[1]))
    if found:
        return {"handle": found[0][2], "how": "label"}
    for m in AFTER_RE.finditer(text):
        if _ok_handle(m.group(1), strict=True):
            return {"handle": m.group(1).strip("."), "how": "after"}
    for m in INFER_RE.finditer(text):
        if _ok_handle(m.group(1), strict=False) and m.group(1).lower() not in GENERIC:
            return {"handle": m.group(1).strip("."), "how": "inferred"}
    return None
