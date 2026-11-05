"""Sanidade do LEIA-ME, da imagem oficial e das instruções de instalação.

Roda com a distribuição Windows também: ela não inclui .bat nem .github.
Não requer PySide6, Ollama, Node, rede nem dados pessoais.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DOCS = ROOT / "docs"


class DocumentationTests(unittest.TestCase):
    def test_official_yuna_portrait_is_embedded_and_valid(self):
        readme = README.read_text(encoding="utf-8")
        relative = "docs/yuna-portrait.webp"
        self.assertIn('src="' + relative + '"', readme)
        photo = (ROOT / relative).read_bytes()
        self.assertGreater(len(photo), 500)
        self.assertEqual(photo[:4], b"RIFF")
        self.assertEqual(photo[8:12], b"WEBP")
        self.assertIn("retrato de referência visual oficial", readme)

    def test_version_and_install_entrypoints(self):
        readme = README.read_text(encoding="utf-8")
        source = (ROOT / "self_model.py").read_text(encoding="utf-8")
        version = re.search(r'^VERSION\s*=\s*"([^"]+)"', source, re.M)
        self.assertIsNotNone(version)
        self.assertIn("Versão do código:** " + version.group(1), readme)
        self.assertIn("Yuna-Setup.exe", readme)
        self.assertIn("Yuna.bat", readme)
        self.assertIn("Ollama", readme)
        self.assertIn("qwen2.5:1.5b", readme)
        self.assertIn("qwen2.5:3b", readme)
        # No runtime distribuído o BAT é intencionalmente excluído.
        if (ROOT / "Yuna.bat").is_file():
            self.assertEqual(
                [p.name for p in ROOT.glob("*.bat")], ["Yuna.bat"])

    def test_local_documentation_links_exist(self):
        markdown = README.read_text(encoding="utf-8")
        for address in re.findall(r"\]\(([^)\s]+)\)", markdown):
            if (address.startswith(("http:", "https:", "#", "mailto:"))):
                continue
            path = address.split("#", 1)[0]
            if not path:
                continue
            # A pasta .github não é incluída no instalador empacotado.
            if path.startswith(".github/") and not (ROOT / ".github").exists():
                continue
            with self.subTest(link=address):
                self.assertTrue((ROOT / path).is_file(), address)
        for path in ("docs/INSTALACAO_WINDOWS.md",
                     "docs/ESTRUTURA_DO_PROJETO.md",
                     "docs/GUIA_COMPLETO.md", "docs/README.md"):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_public_documentation_avoids_tokens_or_sample_passwords(self):
        readme = README.read_text(encoding="utf-8")
        self.assertIn("Nunca publique", readme)
        self.assertNotIn("github_pat_", readme)
        self.assertNotIn("sk-proj-", readme)
        setup = (DOCS / "INSTALACAO_WINDOWS.md").read_text(encoding="utf-8")
        self.assertIn("Get-FileHash", setup)
        self.assertIn("SHA256SUMS.txt", setup)
        self.assertIn("Problemas frequentes", setup)


if __name__ == "__main__":
    unittest.main()
