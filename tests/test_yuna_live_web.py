"""Valida que a prévia web usa peças SVG articuladas, não uma imagem com zoom."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "yuna-preview.html"
SCRIPT = ROOT / "docs" / "yuna-viva.js"


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.scripts = []
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if "id" in props:
            self.ids.add(props["id"])
        if tag == "script" and props.get("src"):
            self.scripts.append(props["src"])
        if tag == "button":
            self.buttons.append(props)


class LiveWebPreviewTests(unittest.TestCase):
    def test_local_scripts_and_default_articulated_mode(self):
        html = PAGE.read_text(encoding="utf-8")
        script = SCRIPT.read_text(encoding="utf-8")
        parser = Tags()
        parser.feed(html)
        self.assertIn("./yuna-viva.js", parser.scripts)
        self.assertIn("./yuna-chat.js", parser.scripts)
        for control in ('chatForm', 'chatInput', 'sendChat', 'chatMessages', 'chatActivity'):
            self.assertIn(control, parser.ids)
        self.assertIn('class="stage-panel live-mode"', html)
        self.assertIn("modeLive", parser.ids)
        self.assertIn("modePortrait", parser.ids)
        self.assertIn("pauseMotion", parser.ids)
        self.assertIn("motionChip", parser.ids)
        self.assertIn("portraitLabel", parser.ids)
        self.assertIn("setSvgTransform", script.replace("motion(", "setSvgTransform("))
        self.assertIn("requestAnimationFrame", script)
        self.assertIn("idleLook", script)
        self.assertIn("blink(", script)
        self.assertIn("armRight", script)
        self.assertIn("hairFront", script)
        self.assertIn("mouth", script)
        self.assertIn("eyeX", script)
        self.assertIn("setPortraitMode(false)", script)
        for mood in ("idle", "happy", "shy", "angry", "wave", "sleep",
                     "curious", "walk", "surprised", "dance", "laugh"):
            self.assertTrue(any(b.get("data-action") == mood for b in parser.buttons))

    def test_no_privileged_browser_access(self):
        js = SCRIPT.read_text(encoding="utf-8")
        for prohibited in ("getUserMedia(", "fetch(", "WebSocket(",
                           "localStorage.", "eval(", "document.cookie",
                           "navigator.geolocation", "serviceWorker"):
            self.assertNotIn(prohibited, js)
        self.assertLess(len(js), 15000)
        self.assertLess(PAGE.stat().st_size, 80000)


if __name__ == "__main__":
    unittest.main()

