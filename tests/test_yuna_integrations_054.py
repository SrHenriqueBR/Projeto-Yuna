"""Testes de integrações 0.54: local-first, consentimento e limites de acesso."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from document_library import DocumentLibrary
import yuna_rag
import ollama_memory
import osv_security
import windows_events


class FakeOpener:
    def __init__(self, response):
        self.response = response
        self.requests = []
    def open(self, request, timeout):
        self.requests.append(request)
        return io.BytesIO(json.dumps(self.response).encode("utf-8"))


class RagTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.library = DocumentLibrary(self.root / "data")
        self.doc = self.root / "documento.md"
        self.doc.write_text(
            "A Yuna possui uma biblioteca de documentos guardados com consentimento. "
            "O motor de busca semântica usa a CPU e o Ollama local. "
            "Cada arquivo é indexado manualmente. "
            "As memórias pessoais ficam em outro banco de dados.",
            encoding="utf-8")
        self.item = self.library.add(self.doc)
        db = self.root / "data/yuna.db"
        db.write_bytes(b"MEMORIA-PRIVADA")

    def tearDown(self):
        self.tmp.cleanup()

    def test_chunks_and_invalid_inputs(self):
        self.assertTrue(yuna_rag.split_chunks("texto " * 600))
        self.assertLessEqual(len(yuna_rag.split_chunks("texto " * 10000)), 24)
        with self.assertRaises(ValueError):
            yuna_rag.split_chunks("", size=8)

    def test_index_query_and_clear_never_touch_original_memory(self):
        calls = []
        def fake_embed(texts):
            calls.append(texts)
            if len(texts) == 1 and "Ollama" in texts[0]:
                return [[0.85, 0.15]]
            return [[0.8, 0.2] for _ in texts]
        with patch("yuna_rag.embeddings", side_effect=fake_embed):
            result = yuna_rag.index_document(self.root, self.item["id"])
            self.assertIn("Indexei", result)
            output = yuna_rag.search_documents(self.root, "Ollama na biblioteca")
        self.assertIn("documento.md", output)
        self.assertIn("DADOS NÃO CONFIÁVEIS", output)
        self.assertEqual((self.root / "data/yuna.db").read_bytes(), b"MEMORIA-PRIVADA")
        self.assertEqual(len(self.library.entries()), 1)
        self.assertTrue(yuna_rag.rag_path(self.root).is_file())
        self.assertIn("apagado", yuna_rag.clear_index(self.root))
        self.assertFalse(yuna_rag.rag_path(self.root).exists())
        self.assertTrue(self.library.path_for(self.item["id"]).is_file())
        self.assertEqual((self.root / "data/yuna.db").read_bytes(), b"MEMORIA-PRIVADA")

    def test_no_unconsented_path_or_orphaned_result(self):
        with patch("yuna_rag.embeddings", return_value=[[1.0, 0.0]]):
            yuna_rag.index_document(self.root, self.item["id"])
        with self.assertRaises(ValueError):
            yuna_rag.index_document(self.root, "../segredo")
        # Excluindo a entrada na biblioteca original, o RAG não deve retornar
        # conteúdo de documentos fora da lista explicitamente arquivada.
        self.library._save_index([])
        self.assertIn("Não há documentos", yuna_rag.search_documents(
            self.root, "buscar documentação"))

    def test_local_embed_endpoint_and_limits(self):
        def local(path, payload=None, timeout=0):
            self.assertEqual(path, "/api/embed")
            self.assertEqual(payload["model"], "embeddinggemma")
            self.assertEqual(payload["keep_alive"], 0)
            return io.BytesIO(json.dumps({"embeddings": [[3.0, 4.0] * 32]}).encode())
        with patch("yuna_rag.local_api", side_effect=local):
            result = yuna_rag.embeddings(["Documento de teste"])
        self.assertEqual(len(result[0]), 64)
        self.assertAlmostEqual(sum(x*x for x in result[0]), 1.0)
        with patch("yuna_rag.local_api", return_value=io.BytesIO(
                b'{"embeddings":[[1,NaN]]}')):
            with self.assertRaises(RuntimeError):
                yuna_rag.embeddings(["teste"])
        self.assertEqual((self.root / "data/yuna.db").read_bytes(), b"MEMORIA-PRIVADA")

    def test_embedding_model_only_downloaded_on_explicit_call(self):
        self.assertEqual(self.library.entries()[0]["name"], "documento.md")
        with patch("yuna_rag.local_api") as local:
            yuna_rag.available_documents(self.root)
            local.assert_not_called()
            local.return_value = io.BytesIO(b'{"status":"success"}\n')
            self.assertIn("EmbeddingGemma disponível", yuna_rag.install_embedding_model())
            self.assertEqual(local.call_args.args[0], "/api/pull")
            self.assertEqual(local.call_args.args[1]["model"], "embeddinggemma")


class OllamaMemoryTests(unittest.TestCase):
    def test_status_and_selective_unload(self):
        call_log = []
        def api(path, payload=None, timeout=0):
            call_log.append((path, payload))
            if path == "/api/ps":
                return io.BytesIO(json.dumps({"models": [
                    {"name": "qwen3.5:4b", "size": 2000000000, "size_vram": 1000000000}
                ]}).encode())
            self.assertEqual(path, "/api/generate")
            self.assertEqual(payload, {"model": "qwen3.5:4b", "prompt": "",
                                      "stream": False, "keep_alive": 0})
            return io.BytesIO(b'{"done":true}')
        with patch("ollama_memory.local_api", side_effect=api):
            self.assertIn("qwen3.5:4b", ollama_memory.loaded_model_status())
            with self.assertRaises(ValueError):
                ollama_memory.unload_model("modelo-nao-carregado")
            self.assertIn("descarregar", ollama_memory.unload_model("qwen3.5:4b"))
        self.assertEqual([x[0] for x in call_log].count("/api/generate"), 1)

    def test_idle_has_no_network_side_effect(self):
        with patch("ollama_memory.local_api", return_value=io.BytesIO(b'{"models":[]}')):
            self.assertIn("Nenhum modelo", ollama_memory.loaded_model_status())
            with self.assertRaises(ValueError):
                ollama_memory.unload_model("qwen3.5:4b")


class OsvTests(unittest.TestCase):
    def test_api_payload_and_explicit_response(self):
        client = FakeOpener({"vulns": [{"id": "GHSA-demo-123", "summary": "Vulnerabilidade de exemplo"}]})
        answer = osv_security.check_package("PyPI", "requests", "2.0.0", opener=client)
        self.assertIn("GHSA-demo-123", answer)
        self.assertEqual(len(client.requests), 1)
        req = client.requests[0]
        self.assertEqual(req.full_url, "https://api.osv.dev/v1/query")
        self.assertEqual(json.loads(req.data),
                         {"package": {"ecosystem": "PyPI", "name": "requests"},
                          "version": "2.0.0"})

    def test_only_public_name_version_and_valid_scope(self):
        for bad in (";rm", "https://example.com", "../../data", "tool\nname"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    osv_security.validate("PyPI", bad, "1.0.0")
        with self.assertRaises(ValueError):
            osv_security.validate("PyPI", "ok", "1;command")
        self.assertEqual(osv_security.validate("npm", "@acme/package", "1.2.3")
                         ["package"]["name"], "@acme/package")
        self.assertIn("não prova segurança",
                      osv_security.check_package(
                          "PyPI", "requests", "2.0.0",
                          opener=FakeOpener({"vulns": []})))


class WindowsEventTests(unittest.TestCase):
    def test_explicit_windows_only_metadata_without_message(self):
        fake = Mock(returncode=0, stdout=json.dumps([
            {"Quando": "2026-11-05T11:00:00", "Origem": "Kernel-Power",
             "Codigo": 41, "Nivel": "Crítico", "Message": "segredo privado"}
        ]))
        with patch("windows_events.sys.platform", "win32"):
            text = windows_events.read_recent_events("System", runner=Mock(return_value=fake))
        self.assertIn("Kernel-Power", text)
        self.assertIn("Evento 41", text)
        self.assertNotIn("segredo privado", text)

    def test_rejects_unknown_logs_and_non_windows(self):
        self.assertIn("somente no Windows", windows_events.read_recent_events("System"))
        with patch("windows_events.sys.platform", "win32"):
            with self.assertRaises(ValueError):
                windows_events.read_recent_events("Security")


if __name__ == "__main__":
    unittest.main()
