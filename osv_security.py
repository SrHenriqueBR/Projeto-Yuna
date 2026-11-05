"""Consulta pública OSV.dev para pacotes Python ou npm, sob comando do usuário."""
import json
import re
import urllib.error
import urllib.request

URL = "https://api.osv.dev/v1/query"
ECOSYSTEMS = {"PyPI", "npm"}


class DenyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("O serviço OSV não pode redirecionar esta consulta.")


def validate(ecosystem, name, version):
    if ecosystem not in ECOSYSTEMS:
        raise ValueError("Escolha PyPI ou npm.")
    if not isinstance(name, str) or not isinstance(version, str):
        raise ValueError("Nome e versão precisam ser textos.")
    pattern = r"(?:@[a-z0-9_.-]+/)?[a-z0-9_.-]{1,100}" if ecosystem == "npm" else r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}"
    if not re.fullmatch(pattern, name) or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.+_~:-]{0,59}", version):
        raise ValueError("Nome ou versão inválidos.")
    return {"package": {"ecosystem": ecosystem, "name": name}, "version": version}


def check_package(ecosystem, name, version, *, opener=None):
    payload = validate(ecosystem, name, version)
    request = urllib.request.Request(
        URL, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "Projeto-Yuna/0.54"})
    client = opener or urllib.request.build_opener(
        urllib.request.ProxyHandler({}), DenyRedirect())
    try:
        with client.open(request, timeout=15) as response:
            raw = response.read(100001)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("OSV respondeu HTTP " + str(exc.code)) from None
    except (OSError, urllib.error.URLError, TimeoutError):
        raise RuntimeError("OSV indisponível no momento.") from None
    if len(raw) > 100000:
        raise ValueError("Resposta OSV grande demais.")
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Resposta OSV inválida.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("vulns", []), list):
        raise ValueError("Resposta OSV inválida.")
    vulns = data.get("vulns", [])
    lines = [f"OSV.dev · {ecosystem}: {name}@{version}",
             "Consulta por nome/versão, sem enviar arquivos ou credenciais."]
    if not vulns:
        lines.append("Nenhuma vulnerabilidade listada. Isso não prova segurança.")
    for item in vulns[:10]:
        if isinstance(item, dict):
            lines.append("• " + str(item.get("id", ""))[:65].replace("\n", " ")
                         + ": " + str(item.get("summary") or "Sem resumo.")[:200].replace("\n", " "))
    if len(vulns) > 10 or data.get("next_page_token"):
        lines.append("Há mais resultados; consulta resumida.")
    lines.append("Fonte: https://osv.dev/; confirme atualizações na fonte oficial.")
    return "\n".join(lines)
