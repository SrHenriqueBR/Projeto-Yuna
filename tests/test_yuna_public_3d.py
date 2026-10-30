"""HTML da prévia 3D: importações estáticas, sem webcam ou acesso remoto."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "yuna-3d-viva.html"
SCRIPT = ROOT / "docs" / "yuna-3d-viva.mjs"


class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.scripts = []
        self.reactions = set()
    def handle_starttag(self, tag, attrs):
        p = dict(attrs)
        if p.get("id"):
            self.ids.add(p["id"])
        if tag == "script" and p.get("src"):
            self.scripts.append(p["src"])
        if p.get("data-pose"):
            self.reactions.add(p["data-pose"])


class Public3DPreviewTests(unittest.TestCase):
    def test_static_page_wires_public_3d_stage(self):
        text = PAGE.read_text(encoding="utf-8")
        script = SCRIPT.read_text(encoding="utf-8")
        parser = Reader()
        parser.feed(text)
        self.assertIn("./yuna-3d-viva.mjs", parser.scripts)
        self.assertTrue({"stage", "message", "speak", "pause", "intensity",
                         "eyeColor", "hairStyle", "cameraReset"} <= parser.ids)
        self.assertTrue({"idle", "happy", "wave", "walk", "curious",
                         "shy", "angry", "wink", "sit"} <= parser.reactions)
        self.assertIn("@0.180.0", text)
        self.assertIn("three.module.js", text)
        self.assertIn("WebGLRenderer", script)
        self.assertIn("PerformanceDirector", script)
        self.assertIn("createAnimePreview", script)
        self.assertIn("renderer.render", script)
        self.assertIn("requestAnimationFrame", script)

    def test_no_sensitive_access_or_unlicensed_model(self):
        script = SCRIPT.read_text(encoding="utf-8")
        for denied in ["getUserMedia(", "fetch(", "WebSocket(",
                       "document.cookie", "localStorage", "navigator.geolocation",
                       "eval(", "new Function("]:
            self.assertNotIn(denied, script)
        self.assertFalse((ROOT / "docs" / "yuna.vrm").exists())
        self.assertLess(SCRIPT.stat().st_size, 20000)


if __name__ == "__main__":
    unittest.main()
