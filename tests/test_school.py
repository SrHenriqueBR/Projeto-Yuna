import base64
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

import development_lab as lab
import school_cycle as school
import school_publish as publisher

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
CYCLE = "123456-1"


class SchoolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "tests").mkdir()
        (self.root / "aprendizado").mkdir()
        for name in lab.TARGETS + (lab.CONTRACT,):
            shutil.copyfile(ROOT / name, self.root / name)
        self.config = self.root / "aprendizado/config.json"
        self.config.write_text('{"ativo":true,"propor_codigo":true}', encoding="utf-8")
        self.answers = self.root / "aprendizado/respostas.json"
        self.answers.write_text("[]", encoding="utf-8")
        self.sources = [{"id": ident, "url": url, "status": "read", "text": "Public Python documentation"}
                        for ident, url in school.SOURCES.items()]

    def tearDown(self):
        self.temporary.cleanup()

    def study(self, target="language_quality.py"):
        return {"observacao": "Os testes devem conferir o resultado observável e preservar a linguagem natural.",
                "perguntas": [{"pergunta": "Qual tarefa repetitiva você quer que eu aprenda primeiro?",
                               "motivo": "Preciso de um exemplo concreto para escolher a próxima melhoria."}],
                "melhoria": {"arquivo": target, "objetivo": "Acrescentar um auxiliar de texto verificável"}}

    def candidate(self):
        original = (self.root / lab.TARGETS[0]).read_text(encoding="utf-8")
        return {"summary": "Adiciona um auxiliar mínimo para validar o ciclo público de estudo.",
                "source": original + "\n\ndef school_fixture():\n    return 42\n",
                "tests": "import unittest\nfrom language_quality import school_fixture\n"
                         "class ExtraTests(unittest.TestCase):\n"
                         "    def test_fixture(self):\n        self.assertEqual(school_fixture(), 42)\n"}

    def bundle(self, target="language_quality.py", failed=False):
        study = self.study(target)
        ask = Mock(side_effect=[json.dumps(study), json.dumps(self.candidate()), json.dumps(self.candidate())])
        runner = Mock()
        runner.prepare.return_value = True
        runner.run.side_effect = [lab.TestResult("passed", "base", 9),
            lab.TestResult("failed" if failed else "passed", "candidate", 10),
            lab.TestResult("failed", "retry", 10)]
        return school.generate(self.root, SHA, CYCLE, ask=ask, sources=self.sources, runner=runner)

    def api(self):
        def call(path, *, data=None, token=None, method=None):
            if path == "":
                return {"private": False}
            if path == "/git/ref/heads/main":
                return {"object": {"sha": SHA}}
            if path.startswith("/git/commits/"):
                return {"tree": {"sha": "b" * 40}}
            if path == "/git/trees":
                return {"sha": "c" * 40}
            if path == "/git/commits":
                return {"sha": "d" * 40}
            if path == "/git/refs":
                return {"ref": data["ref"]}
            if path == "/pulls":
                return {"html_url": "https://github.com/" + school.REPO + "/pull/123"}
            raise AssertionError("Unexpected GitHub endpoint: " + path)
        return Mock(side_effect=call)

    def test_study_uses_only_public_code_sources_and_explicit_answers(self):
        (self.root / "data").mkdir()
        (self.root / "data/yuna.db").write_text("PRIVATE CONVERSATION", encoding="utf-8")
        (self.root / ".env").write_text("SECRET KEY", encoding="utf-8")
        question = "Qual tarefa repetitiva você quer que eu aprenda primeiro?"
        answer = {"id": school.question_id(question), "pergunta": question,
                  "resposta": "Conferir se uma frase contém concordância incorreta."}
        self.answers.write_text(json.dumps([answer]), encoding="utf-8")
        ask = Mock(return_value=json.dumps(self.study("nenhum")))
        bundle = school.generate(self.root, SHA, CYCLE, ask=ask, sources=self.sources)
        prompt = ask.call_args.args[0][-1]["content"]
        self.assertIn("concord", prompt)
        self.assertNotIn("PRIVATE CONVERSATION", prompt)
        self.assertNotIn("SECRET KEY", prompt)
        self.assertEqual(bundle["answers_used"], [answer["id"]])
        self.assertEqual(bundle["study"]["perguntas"], [])
        self.assertIsNone(bundle["candidate"])

    def test_generated_code_stays_in_minimal_workspace_never_installed(self):
        before = (self.root / lab.TARGETS[0]).read_bytes()
        bundle = self.bundle()
        self.assertEqual(bundle["experiment"]["status"], "tests_passed")
        self.assertEqual(bundle["candidate"]["target"], lab.TARGETS[0])
        self.assertEqual((self.root / lab.TARGETS[0]).read_bytes(), before)
        self.assertFalse((self.root / "data").exists())
        self.assertEqual(publisher.validate_bundle(self.root, bundle, SHA, CYCLE), bundle)

    def test_failed_experiment_still_produces_questions_without_publishing_source(self):
        bundle = self.bundle(failed=True)
        self.assertEqual(bundle["experiment"]["status"], "failed")
        self.assertIsNone(bundle["candidate"])
        files = publisher.publication_files(bundle)
        self.assertTrue(bundle["study"]["perguntas"])
        self.assertTrue(all(path.startswith("aprendizado/ciclos/") for path in files))

    def test_questions_only_setting_never_calls_lab(self):
        self.config.write_text('{"ativo":true,"propor_codigo":false}', encoding="utf-8")
        with patch("school_cycle.lab.develop", side_effect=AssertionError("No code")):
            bundle = self.bundle()
        self.assertIsNone(bundle["candidate"])
        self.assertEqual(bundle["experiment"]["status"], "not_requested")

    def test_answers_validated_and_empty_answers_not_presented_as_knowledge(self):
        question = "Qual tarefa repetitiva você quer que eu aprenda primeiro?"
        data = [{"id": school.question_id(question), "pergunta": question, "resposta": ""}]
        self.answers.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(school.load_answers(self.root), [])
        data[0]["id"] = "forged"
        self.answers.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            school.load_answers(self.root)

    def test_duplicate_questions_and_control_characters(self):
        data = self.study("nenhum")
        data["perguntas"] *= 2
        validated = school.validate_study(json.dumps(data), set())
        self.assertEqual(len(validated["perguntas"]), 1)
        self.assertEqual(school.validate_study(json.dumps(data), {validated["perguntas"][0]["id"]})["perguntas"], [])
        data["observacao"] += "\x1b[2J"
        with self.assertRaises(ValueError):
            school.validate_study(json.dumps(data), set())

    def test_model_cannot_choose_arbitrary_paths_or_publication_commands(self):
        for target in ("../yuna.py", "yuna_governance.py", ".github/workflows/testes.yml", "computer.py"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                school.validate_study(json.dumps(self.study(target)), set())
        data = self.study()
        data["shell"] = "echo do-not-execute"
        with self.assertRaises(ValueError):
            school.validate_study(json.dumps(data), set())

    def test_preflight_pauses_disabled_private_and_pending_branch(self):
        api = Mock()
        self.config.write_text('{"ativo":false,"propor_codigo":true}', encoding="utf-8")
        self.assertFalse(school.preflight(self.root, api=api)[0])
        api.assert_not_called()
        self.config.write_text('{"ativo":true,"propor_codigo":true}', encoding="utf-8")
        api.side_effect = [{"private": True}]
        self.assertFalse(school.preflight(self.root, api=api)[0])
        api.side_effect = [{"private": False}, [{"ref": "refs/heads/yuna/estudo-123-1"}], []]
        self.assertFalse(school.preflight(self.root, api=api)[0])
        api.side_effect = [{"private": False}, [{"ref": "refs/heads/yuna/estudo-123-1"}],
            [{"state": "closed", "head": {"ref": "yuna/estudo-123-1", "repo": {"full_name": school.REPO}}}]]
        self.assertTrue(school.preflight(self.root, api=api)[0])

    def test_pending_questions_limit(self):
        for index in range(4):
            folder = self.root / "aprendizado/ciclos" / (str(index + 1) + "-1")
            folder.mkdir(parents=True)
            questions = []
            for offset in range(3):
                question = "Qual comportamento devo testar no exemplo " + str(index * 3 + offset) + "?"
                questions.append({"id": school.question_id(question), "pergunta": question})
            (folder / "perguntas.json").write_text(json.dumps(questions), encoding="utf-8")
        api = Mock(side_effect=AssertionError("No need to consult GitHub"))
        self.assertFalse(school.preflight(self.root, api=api)[0])

    def test_publish_new_branch_and_draft_pr_only_no_generated_code_execution(self):
        bundle = self.bundle()
        marker = self.root / "NEVER_EXECUTE"
        bundle["candidate"]["source"] += "\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n"
        api = self.api()
        result = publisher.publish(self.root, bundle, SHA, CYCLE, token="fake-test-token", api=api)
        self.assertTrue(result["pr_created"])
        self.assertFalse(marker.exists())
        writes = [(call.args[0], call.kwargs) for call in api.call_args_list if call.kwargs.get("method")]
        self.assertEqual([path for path, _ in writes], ["/git/trees", "/git/commits", "/git/refs", "/pulls"])
        self.assertTrue(all(kwargs["method"] == "POST" for _, kwargs in writes))
        self.assertEqual(writes[2][1]["data"]["ref"], "refs/heads/yuna/estudo-" + CYCLE)
        self.assertIs(writes[3][1]["data"]["draft"], True)
        paths = [item["path"] for item in writes[0][1]["data"]["tree"]]
        self.assertIn(lab.TARGETS[0], paths)
        self.assertFalse(any(path.startswith((".github/", "data/", "tests/")) for path in paths))

    def test_private_repo_or_changed_main_never_written(self):
        bundle = self.bundle()
        for results in ([{"private": True}], [{"private": False}, {"object": {"sha": "b" * 40}}]):
            api = Mock(side_effect=results)
            with self.assertRaises(ValueError):
                publisher.publish(self.root, bundle, SHA, CYCLE, token="fake", api=api)
            self.assertTrue(all(not call.kwargs.get("method") for call in api.call_args_list))

    def test_pr_setting_block_retains_branch_and_returns_review_link(self):
        bundle = self.bundle()
        api = self.api()
        original = api.side_effect
        def call(path, **kwargs):
            if path == "/pulls":
                raise urllib.error.HTTPError("https://api.github.com", 403, "Forbidden", {}, None)
            return original(path, **kwargs)
        api.side_effect = call
        result = publisher.publish(self.root, bundle, SHA, CYCLE, token="fake", api=api)
        self.assertFalse(result["pr_created"])
        self.assertIn("/compare/main...yuna/estudo-", result["pr_url"])
        self.assertEqual(sum(call.args[0] == "/git/refs" for call in api.call_args_list), 1)

    def test_mismatched_base_cycle_targets_and_test_counts_never_publish(self):
        original = self.bundle()
        changes = [("base_sha", "b" * 40), ("cycle", "../main"), ("model", "paid-cloud")]
        for key, value in changes:
            bundle = copy.deepcopy(original)
            bundle[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                publisher.validate_bundle(self.root, bundle, SHA, CYCLE)
        for count in (0, 9, True):
            bundle = copy.deepcopy(original)
            bundle["experiment"]["attempts"][-1]["tests"] = count
            with self.subTest(count=count), self.assertRaises(ValueError):
                publisher.validate_bundle(self.root, bundle, SHA, CYCLE)
        bundle = copy.deepcopy(original)
        bundle["candidate"]["target"] = ".github/workflows/escape.yml"
        with self.assertRaises(ValueError):
            publisher.validate_bundle(self.root, bundle, SHA, CYCLE)

    def test_markdown_treats_model_text_as_data_and_has_only_fixed_source_links(self):
        bundle = self.bundle(target="nenhum")
        bundle["study"]["observacao"] = "<script>alert(1)</script> ![tracker](https://example.com) @someone"
        files = publisher.publication_files(bundle)
        markdown = files["aprendizado/ciclos/" + CYCLE + "/README.md"]
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("![tracker]", markdown)
        self.assertNotIn("@someone", markdown)
        self.assertIn("respostas.json", markdown)

    def test_no_token_redirects_and_ollama_uses_fixed_local_model(self):
        with self.assertRaises(ValueError):
            school.request_json("https://example.com", token="fake")
        with self.assertRaises(ValueError):
            school.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com")
        result = {"done": True, "done_reason": "stop", "message": {"content": "{}"}}
        with patch("school_cycle.request_json", return_value=result) as request:
            self.assertEqual(school.ask_local([], schema=school.STUDY_SCHEMA), "{}")
        self.assertEqual(request.call_args.args[0], "http://127.0.0.1:11434/api/chat")
        self.assertEqual(request.call_args.kwargs["data"]["model"], school.MODEL)
        self.assertNotIn("tools", request.call_args.kwargs["data"])
        result["done_reason"] = "length"
        with patch("school_cycle.request_json", return_value=result), self.assertRaises(ValueError):
            school.ask_local([])


if __name__ == "__main__":
    unittest.main()
