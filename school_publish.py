"""Publicador determinístico. Recebe dados do job de estudo e nunca os executa.

Só cria uma branch nova yuna/estudo-ID e um PR rascunho. Não altera main,
não faz merge, não aprova PR e não pode publicar workflows ou credenciais.
"""
import base64
import html
import json
import os
from pathlib import Path
import re
import urllib.error

import development_lab as lab
from school_cycle import (MAX_BUNDLE, MODEL, REPO, SOURCES, clean_text, github,
                          load_config, question_id, validate_study)


def validate_bundle(root, bundle, base_sha, cycle):
    if not isinstance(bundle, dict) or set(bundle) != {
            "version", "base_sha", "cycle", "model", "created_at", "study",
            "sources", "answers_used", "experiment", "candidate"}:
        raise ValueError("Formato de publicação inválido.")
    if (bundle["version"] != 1 or bundle["base_sha"] != base_sha or bundle["cycle"] != cycle
            or not re.fullmatch(r"[a-f0-9]{40}", base_sha)
            or not re.fullmatch(r"[0-9]{1,20}-[0-9]{1,3}", cycle) or bundle["model"] != MODEL):
        raise ValueError("A publicação não corresponde a esta execução.")
    config = load_config(root)
    if not config["ativo"]:
        raise ValueError("Escola pausada.")
    study = bundle["study"]
    # Retirar IDs atribuídos pelo código para revalidar os campos do modelo.
    raw = {**study, "perguntas": [{key: row.get(key) for key in ("pergunta", "motivo")}
                                  for row in study.get("perguntas", [])]}
    validated = validate_study(json.dumps(raw, ensure_ascii=False), set())
    if validated != study:
        raise ValueError("Perguntas inconsistentes ou duplicadas.")
    if not isinstance(bundle["sources"], list) or len(bundle["sources"]) != len(SOURCES):
        raise ValueError("Fontes públicas inconsistentes.")
    for source, (ident, url) in zip(bundle["sources"], SOURCES.items()):
        if (not isinstance(source, dict) or set(source) != {"id", "url", "status"}
                or source["id"] != ident or source["url"] != url
                or source["status"] not in ("read", "unavailable")):
            raise ValueError("Destino de fonte não permitido.")
    answers = bundle["answers_used"]
    if (not isinstance(answers, list) or len(answers) > 50
            or any(not isinstance(item, str) or not re.fullmatch(r"p-[a-f0-9]{16}", item) for item in answers)):
        raise ValueError("Referências a respostas inválidas.")
    clean_text(bundle["created_at"], 20, 40)
    experiment = bundle["experiment"]
    if not isinstance(experiment, dict) or experiment.get("status") not in (
            "not_requested", "tests_passed", "not_run", "failed", "baseline_failed",
            "invalid", "cancelled", "error", "rejected_limits"):
        raise ValueError("Estado de teste inválido.")
    candidate = bundle["candidate"]
    if candidate is not None:
        if not isinstance(candidate, dict) or set(candidate) != {"target", "source", "tests", "summary"}:
            raise ValueError("Proposta de código inválida.")
        target = candidate["target"]
        if (not config["propor_codigo"] or target not in lab.TARGETS
                or target != study["melhoria"]["arquivo"] or experiment["status"] != "tests_passed"):
            raise ValueError("Código sem teste aprovado ou fora dos módulos permitidos.")
        baseline = experiment.get("baseline", {})
        attempts = experiment.get("attempts", [])
        if (not isinstance(baseline, dict) or baseline.get("status") != "passed"
                or type(baseline.get("tests")) is not int or baseline["tests"] < 1
                or not isinstance(attempts, list) or not 1 <= len(attempts) <= 2
                or not isinstance(attempts[-1], dict) or attempts[-1].get("status") != "passed"
                or type(attempts[-1].get("tests")) is not int
                or attempts[-1]["tests"] <= baseline["tests"]):
            raise ValueError("Comprovante de execução dos testes incompleto.")
        lab._validate(json.dumps({key: candidate[key] for key in ("summary", "source", "tests")},
                                ensure_ascii=False), target, lab._read_source(root, target))
        if len(candidate["source"].encode("utf-8")) > lab.MAX_SOURCE:
            raise ValueError("Código maior que o limite da instalação.")
    if len(json.dumps(bundle, ensure_ascii=False).encode("utf-8")) > MAX_BUNDLE:
        raise ValueError("Publicação maior que o limite.")
    return bundle


def escaped(value):
    value = html.escape(str(value)).replace("@", "@\u200b")
    return re.sub(r"([\\`*_{}\[\]()#+!|])", r"\\\1", value)


def publication_files(bundle):
    cycle = bundle["cycle"]
    folder = "aprendizado/ciclos/" + cycle
    questions = bundle["study"]["perguntas"]
    lines = ["# Estudo da Yuna — " + cycle, "", "**Estado: aguardando revisão humana.**",
             "Ollama no GitHub Actions; não usa o notebook nem dados pessoais.", "",
             "## Nota de estudo", "", escaped(bundle["study"]["observacao"]), "",
             "Nota gerada pelo modelo: pode conter erros e ainda precisa ser conferida.", "",
             "## Perguntas para os mentores", ""]
    for question in questions:
        lines += ["### " + question["id"], "", escaped(question["pergunta"]), "",
                  "Motivo: " + escaped(question["motivo"]), ""]
    if not questions:
        lines += ["Nenhuma pergunta nova nesta rodada.", ""]
    lines += ["Para responder: depois da revisão, copie a pergunta e seu ID para",
              "[`aprendizado/respostas.json`](../../respostas.json) no main e preencha `resposta`.",
              "As respostas são públicas e serão lidas na próxima rodada.", "",
              "## Experimento de código", "",
              "Resultado: **" + escaped(bundle["experiment"]["status"]) + "**.", "",
              "Objetivo proposto: " + escaped(bundle["study"]["melhoria"]["objetivo"]), ""]
    candidate = bundle["candidate"]
    if candidate:
        lines += ["Arquivo proposto: `" + candidate["target"] + "`.",
                  "Os contratos fixos e testes adicionais passaram em Docker sem rede.",
                  "A suíte completa do Windows e a revisão humana continuam necessárias.", ""]
    else:
        lines += ["Nenhum arquivo de código foi alterado neste ciclo.", ""]
    lines += ["## Leituras públicas", ""]
    for source in bundle["sources"]:
        status = "trecho consultado" if source["status"] == "read" else "indisponível nesta rodada"
        lines.append("- [" + source["id"] + "](" + source["url"] + ") — " + status)
    lines += ["", "Respostas de mentores usadas: " + str(len(bundle["answers_used"])) + ".",
              "Este ciclo não treina pesos, não faz merge e não amplia permissões.", ""]
    # Código gerado adicional fica em .txt: nunca é coletado pelo unittest host.
    files = {folder + "/README.md": "\n".join(lines),
             folder + "/perguntas.json": json.dumps(questions, ensure_ascii=False, indent=2) + "\n",
             folder + "/relatorio.json": json.dumps({key: value for key, value in bundle.items()
                                                      if key != "candidate"}, ensure_ascii=False, indent=2) + "\n"}
    if candidate:
        files[candidate["target"]] = candidate["source"]
        files[folder + "/teste_gerado.txt"] = candidate["tests"]
    return files


def publish(root, bundle, base_sha, cycle, *, token=None, api=github):
    validate_bundle(root, bundle, base_sha, cycle)
    if not token:
        raise ValueError("Credencial temporária do workflow ausente.")
    metadata = api("", token=token)
    if metadata.get("private") is not False:
        raise ValueError("Publicação automática limitada ao repositório público.")
    if api("/git/ref/heads/main", token=token)["object"]["sha"] != base_sha:
        raise ValueError("O main mudou durante o estudo; rode novamente sobre a versão atual.")
    branch = "yuna/estudo-" + cycle
    files = publication_files(bundle)
    base = api("/git/commits/" + base_sha, token=token)
    tree = api("/git/trees", data={"base_tree": base["tree"]["sha"], "tree": [
        {"path": path, "mode": "100644", "type": "blob", "content": content}
        for path, content in files.items()]}, token=token, method="POST")
    commit = api("/git/commits", data={"message": "Yuna: estudo e perguntas " + cycle,
                 "tree": tree["sha"], "parents": [base_sha]}, token=token, method="POST")
    if api("/git/ref/heads/main", token=token)["object"]["sha"] != base_sha:
        raise ValueError("O main mudou antes de publicar; nenhum branch foi criado.")
    # POST cria; nunca PATCH/force/merge. Reexecução com mesmo ID não substitui nada.
    api("/git/refs", data={"ref": "refs/heads/" + branch, "sha": commit["sha"]}, token=token, method="POST")
    url = "https://github.com/" + REPO + "/tree/" + branch + "/aprendizado/ciclos/" + cycle
    body = ("Estudo automático da Yuna para revisão dos mentores.\n\n"
            "[Ler estudo e perguntas](" + url + ").\n\n"
            "Resultado do laboratório: `" + bundle["experiment"]["status"] + "`. "
            "Os testes do código proposto ocorreram somente em contêiner sem rede. "
            "A publicação não executa o código gerado.\n\n"
            "Revise o diff e as perguntas; responda em `aprendizado/respostas.json` no main. "
            "Não há merge nem aprovação automática. O GitHub pode pedir aprovação "
            "para executar os demais workflows deste PR.")
    try:
        pr = api("/pulls", data={"title": "Yuna: estudo e perguntas " + cycle,
                 "body": body, "head": branch, "base": "main", "draft": True}, token=token, method="POST")
        return {"branch": branch, "commit": commit["sha"], "study_url": url,
                "pr_url": pr["html_url"], "pr_created": True}
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 422):
            raise
        # A preferência de criação de PRs pode estar desabilitada. O estudo já
        # está no branch; não pedir PAT, não alterar settings nem duplicar commits.
        return {"branch": branch, "commit": commit["sha"], "study_url": url,
                "pr_url": "https://github.com/" + REPO + "/compare/main..." + branch + "?expand=1",
                "pr_created": False}


def main():
    if os.environ.get("GITHUB_REPOSITORY") != REPO or os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("Publicação só no workflow do main do Projeto Yuna.")
    encoded = os.environ.get("YUNA_STUDY_BUNDLE", "")
    if not encoded or len(encoded) > 100000:
        raise ValueError("Resultado ausente ou extenso demais.")
    bundle = json.loads(base64.b64decode(encoded, validate=True))
    cycle = os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"]
    result = publish(Path(__file__).resolve().parent, bundle, os.environ["GITHUB_SHA"], cycle,
                     token=os.environ.get("YUNA_GH_TOKEN"))
    print("Estudo publicado:", result["study_url"])
    print("Revisão:", result["pr_url"])
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write("## Estudo da Yuna\n\n[Ver perguntas e resultados](" + result["study_url"]
                       + ") · [Revisar no GitHub](" + result["pr_url"] + ")\n")
            if not result["pr_created"]:
                file.write("\nO commit foi criado, mas o GitHub recusou a abertura automática do PR. "
                           "Use o link acima para abrir a revisão manualmente.\n")


if __name__ == "__main__":
    main()
