"""
Script de automacao dos testes do Code Guardian.

Executa todos os 92 casos de teste definidos no plano e reporta PASS/FAIL.

Uso:
    python tests/run_tests.py              # todos os testes
    python tests/run_tests.py --script re  # apenas rule_engine
    python tests/run_tests.py --script me  # apenas metrics
    python tests/run_tests.py --script dp  # apenas diff_parser
    python tests/run_tests.py --script ai  # apenas ai_client
    python tests/run_tests.py --script ru  # apenas runner
"""
import sys
import io
import os
import json
import subprocess
import argparse
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = Path(__file__).parent.parent          # code_guardian/
FIXTURES = Path(__file__).parent / "fixtures"
PY = sys.executable

RULE_ENGINE = str(BASE / "rule_engine.py")
METRICS     = str(BASE / "metrics.py")
DIFF_PARSER = str(BASE / "diff_parser.py")
AI_CLIENT   = str(BASE / "ai_client.py")
RUNNER      = str(BASE / "runner.py")

# ---------------------------------------------------------------------------
# Infraestrutura
# ---------------------------------------------------------------------------

_results = []

def run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Executa comando e retorna (exit_code, stdout, stderr)."""
    r = subprocess.run(cmd, capture_output=True, cwd=cwd or str(BASE))
    stdout = r.stdout.decode("utf-8", errors="replace")
    stderr = r.stderr.decode("utf-8", errors="replace")
    return r.returncode, stdout, stderr


def f(name: str) -> str:
    """Retorna caminho absoluto da fixture."""
    return str(FIXTURES / name)


def check(tc_id: str, desc: str, passed: bool, detail: str = ""):
    icon = "✅" if passed else "❌"
    _results.append((tc_id, desc, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"  {icon} {tc_id}: {desc}")
    if not passed and detail:
        print(f"       >>> {detail}")


def json_ok(stdout: str) -> tuple[bool, object]:
    try:
        return True, json.loads(stdout)
    except Exception:
        return False, None


def contains_rule(data: list, rule_id: str) -> bool:
    return any(i.get("rule_id") == rule_id for i in data)


def contains_severity(data: list, severity: str) -> bool:
    return any(i.get("severity") == severity for i in data)


def all_severity(data: list, severity: str) -> bool:
    return all(i.get("severity") == severity for i in data)


# ---------------------------------------------------------------------------
# TC-RE — rule_engine.py
# ---------------------------------------------------------------------------

def test_rule_engine():
    print("\n── TC-RE  rule_engine.py ──────────────────────────────────────────")

    # TC-RE-001/002 — SQL Injection
    code, out, _ = run([PY, RULE_ENGINE, f("sql_injection.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-001", "SQL Injection por concatenacao (+)",
          ok and contains_rule(data, "SQL_INJECTION_CONCAT"),
          f"exit={code} json={ok} rules={[i.get('rule_id') for i in (data or [])]}")
    check("TC-RE-002", "Exit code 1 quando ha critical",
          code == 1, f"exit={code}")

    # TC-RE-003/004 — Deadlocks
    code, out, _ = run([PY, RULE_ENGINE, f("deadlock.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-003", "Detecta .Result (TASK_RESULT_DEADLOCK)",
          ok and contains_rule(data, "TASK_RESULT_DEADLOCK"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")
    check("TC-RE-004", "Detecta .Wait() (TASK_WAIT_DEADLOCK)",
          ok and contains_rule(data, "TASK_WAIT_DEADLOCK"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")

    # TC-RE-005 — async void (nao event handler)
    code, out, _ = run([PY, RULE_ENGINE, f("async_void.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-005", "Detecta async void em metodo comum",
          ok and contains_rule(data, "ASYNC_VOID"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")

    # TC-RE-006 — async void em event handler NAO deve disparar
    code, out, _ = run([PY, RULE_ENGINE, f("event_handler.cs"), "--format", "json"])
    ok, data = json_ok(out)
    has_async_void = ok and any(i.get("rule_id") == "ASYNC_VOID" for i in (data or []))
    check("TC-RE-006", "async void em event handler nao dispara (falso positivo)",
          ok and not has_async_void,
          f"ASYNC_VOID encontrado={has_async_void}")

    # TC-RE-007/008 — Secrets
    code, out, _ = run([PY, RULE_ENGINE, f("secrets.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-007", "Detecta senha hardcoded (HARDCODED_PASSWORD)",
          ok and contains_rule(data, "HARDCODED_PASSWORD"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")
    check("TC-RE-008", "Detecta API key hardcoded (HARDCODED_API_KEY)",
          ok and contains_rule(data, "HARDCODED_API_KEY"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")

    # TC-RE-009/010 — Empty catch
    code, out, _ = run([PY, RULE_ENGINE, f("empty_catch.cs"), "--format", "json"])
    ok, data = json_ok(out)
    empty_catches = [i for i in (data or []) if i.get("rule_id") == "EMPTY_CATCH"]
    check("TC-RE-009", "Detecta catch {} vazio",
          ok and len(empty_catches) >= 1,
          f"EMPTY_CATCH count={len(empty_catches)}")
    check("TC-RE-010", "Detecta catch(Exception ex) {} vazio",
          ok and len(empty_catches) >= 2,
          f"EMPTY_CATCH count={len(empty_catches)}")

    # TC-RE-011/012 — Console.Write
    code, out, _ = run([PY, RULE_ENGINE, f("console_warning.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-011", "Detecta Console.WriteLine (warning)",
          ok and contains_rule(data, "CONSOLE_WRITELINE"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")
    check("TC-RE-012", "Detecta Console.Write (warning)",
          ok and contains_rule(data, "CONSOLE_WRITE"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")
    check("TC-RE-012b", "Console warnings nao causam exit 1",
          code == 0, f"exit={code}")

    # TC-RE-013/014/015 — TODO/FIXME/HACK
    code, out, _ = run([PY, RULE_ENGINE, f("todo_comment.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-013", "Detecta TODO_COMMENT",
          ok and contains_rule(data, "TODO_COMMENT"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")
    check("TC-RE-014", "Detecta FIXME_COMMENT",
          ok and contains_rule(data, "FIXME_COMMENT"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")
    check("TC-RE-015", "Detecta HACK_COMMENT",
          ok and contains_rule(data, "HACK_COMMENT"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")

    # TC-RE-016 — HttpClient new
    code, out, _ = run([PY, RULE_ENGINE, f("httpclient_new.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-016", "Detecta new HttpClient() (HTTPCLIENT_NEW)",
          ok and contains_rule(data, "HTTPCLIENT_NEW"),
          f"rules={[i.get('rule_id') for i in (data or [])]}")

    # TC-RE-017 — --severity error filtra info/warning
    code, out, _ = run([PY, RULE_ENGINE, f("todo_comment.cs"), "--format", "json", "--severity", "error"])
    ok, data = json_ok(out)
    check("TC-RE-017", "--severity error filtra TODO/FIXME (info)",
          ok and data == [],
          f"data={data}")

    # TC-RE-018 — --severity critical retorna apenas criticals
    code, out, _ = run([PY, RULE_ENGINE, f("secrets.cs"), "--format", "json", "--severity", "critical"])
    ok, data = json_ok(out)
    only_critical = ok and len(data) > 0 and all_severity(data, "critical")
    check("TC-RE-018", "--severity critical retorna apenas criticals",
          only_critical,
          f"severities={[i.get('severity') for i in (data or [])]}")

    # TC-RE-019 — --severity warning inclui warning e acima
    code, out, _ = run([PY, RULE_ENGINE, f("console_warning.cs"), "--format", "json", "--severity", "warning"])
    ok, data = json_ok(out)
    check("TC-RE-019", "--severity warning inclui warnings",
          ok and len(data) > 0,
          f"count={len(data or [])}")

    # TC-RE-020 — arquivo limpo
    code, out, _ = run([PY, RULE_ENGINE, f("clean.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-020", "Arquivo limpo retorna [] e exit 0",
          ok and data == [] and code == 0,
          f"exit={code} data={data}")

    # TC-RE-021 — arquivo inexistente
    code, out, _ = run([PY, RULE_ENGINE, f("nao_existe.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-021", "Arquivo inexistente retorna FILE_NOT_FOUND e exit 1",
          ok and contains_rule(data, "FILE_NOT_FOUND") and code == 1,
          f"exit={code} rules={[i.get('rule_id') for i in (data or [])]}")

    # TC-RE-022 — comentarios nao disparam (falso positivo)
    code, out, _ = run([PY, RULE_ENGINE, f("comment_false_positive.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RE-022", "Matches em comentarios nao disparam issues",
          ok and data == [],
          f"data={data}")

    # TC-RE-024 — formato text contem icone correto
    code, out, _ = run([PY, RULE_ENGINE, f("secrets.cs"), "--format", "text"])
    check("TC-RE-024", "Formato text mostra icone correto (critical = vermelho)",
          "🔴" in out or "critical" in out.lower(),
          f"saida={out[:200]}")

    # TC-RE-025 — formato text mostra numero de linha
    code, out, _ = run([PY, RULE_ENGINE, f("deadlock.cs"), "--format", "text"])
    check("TC-RE-025", "Formato text mostra L{numero} de linha",
          "L" in out and any(c.isdigit() for c in out),
          f"saida={out[:200]}")


# ---------------------------------------------------------------------------
# TC-ME — metrics.py
# ---------------------------------------------------------------------------

def test_metrics():
    print("\n── TC-ME  metrics.py ──────────────────────────────────────────────")

    # TC-ME-001 — arquivo limpo
    code, out, _ = run([PY, METRICS, f("clean.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-ME-001", "Arquivo limpo: issues vazio e exit 0",
          ok and isinstance(data, dict) and data.get("issues") == [] and code == 0,
          f"exit={code} issues={data.get('issues') if data else '?'}")

    # TC-ME-002/003 — metodo longo
    code, out, _ = run([PY, METRICS, f("long_methods.cs"), "--format", "json"])
    ok, data = json_ok(out)
    issues = data.get("issues", []) if data else []
    has_long = any("ongo" in i.get("category", "") or "ongo" in i.get("message", "") for i in issues)
    check("TC-ME-002", "Metodo com > 30 linhas dispara issue Metodo Longo",
          ok and has_long and code == 1,
          f"exit={code} issues={[(i.get('category'), i.get('message', '')[:60]) for i in issues]}")
    has_method_name = ok and any("GenerateFullReport" in i.get("message", "") for i in issues)
    check("TC-ME-003", "Mensagem menciona nome do metodo (GenerateFullReport)",
          has_method_name,
          f"messages={[i.get('message', '')[:80] for i in issues]}")

    # TC-ME-004/005 — deep nesting
    code, out, _ = run([PY, METRICS, f("deep_nesting.cs"), "--format", "json"])
    ok, data = json_ok(out)
    issues = data.get("issues", []) if data else []
    classes = data.get("classes", []) if data else []
    has_nesting_issue = any("esting" in i.get("category", "") or "esting" in i.get("message", "") for i in issues)
    max_nest = max((c.get("max_nesting", 0) for c in classes), default=0)
    check("TC-ME-004", "Nesting > 5 dispara issue Deep Nesting",
          ok and has_nesting_issue and code == 1,
          f"exit={code} issues={[(i.get('category'), i.get('message','')[:60]) for i in issues]}")
    check("TC-ME-005", "max_nesting reportado > 5 no JSON",
          ok and max_nest > 5,
          f"max_nesting={max_nest}")

    # TC-ME-006/007 — God Class por deps
    code, out, _ = run([PY, METRICS, f("god_class.cs"), "--format", "json"])
    ok, data = json_ok(out)
    issues = data.get("issues", []) if data else []
    classes = data.get("classes", []) if data else []
    has_god_class = any("od" in i.get("category", "") or "od" in i.get("message", "") or
                        "ep" in i.get("category", "") for i in issues)
    deps = max((c.get("constructor_deps", 0) for c in classes), default=0)
    check("TC-ME-006", "Mais de 5 deps dispara issue God Class",
          ok and has_god_class and code == 1,
          f"exit={code} issues={[(i.get('category'), i.get('message','')[:60]) for i in issues]}")
    check("TC-ME-007", "constructor_deps >= 7 no JSON",
          ok and deps >= 7,
          f"constructor_deps={deps}")

    # TC-ME-008/009 — God Class por metodos publicos
    public_count = max((c.get("public_method_count", 0) for c in classes), default=0)
    check("TC-ME-008", "Mais de 10 metodos publicos gera issue God Class",
          ok and public_count > 10,
          f"public_method_count={public_count}")
    check("TC-ME-009", "public_method_count >= 12 reportado no JSON",
          ok and public_count >= 12,
          f"public_method_count={public_count}")

    # TC-ME-010 — formato text
    code, out, _ = run([PY, METRICS, f("god_class.cs"), "--format", "text"])
    check("TC-ME-010", "Formato text mostra sumario legivel",
          "Dep" in out or "dep" in out or "nesting" in out.lower() or "Issues" in out,
          f"saida={out[:300]}")

    # TC-ME-011 — arquivo limpo formato text
    code, out, _ = run([PY, METRICS, f("clean.cs"), "--format", "text"])
    check("TC-ME-011", "Arquivo limpo exibe mensagem positiva no text",
          "padr" in out.lower() or "recomend" in out.lower() or "✅" in out,
          f"saida={out[:300]}")

    # TC-ME-012 — arquivo inexistente
    code, out, _ = run([PY, METRICS, f("nao_existe.cs"), "--format", "json"])
    ok, data = json_ok(out)
    issues = data.get("issues", []) if data else []
    check("TC-ME-012", "Arquivo inexistente retorna issue e exit 1",
          ok and len(issues) > 0 and code == 1,
          f"exit={code} issues={issues}")

    # TC-ME-013/014 — estrutura JSON obrigatoria
    code, out, _ = run([PY, METRICS, f("clean.cs"), "--format", "json"])
    ok, data = json_ok(out)
    has_fields = ok and all(k in data for k in ["file", "total_lines", "classes", "issues"])
    classes = data.get("classes", []) if data else []
    class_fields_ok = ok and len(classes) > 0 and all(
        k in classes[0] for k in ["name", "methods", "constructor_deps", "public_method_count", "max_nesting"]
    ) if classes else False
    check("TC-ME-013", "JSON contem campos obrigatorios (file, total_lines, classes, issues)",
          has_fields,
          f"campos={list(data.keys()) if data else '?'}")
    check("TC-ME-014", "Cada classe contem methods, constructor_deps, public_method_count, max_nesting",
          class_fields_ok,
          f"campos_classe={list(classes[0].keys()) if classes else '?'}")


# ---------------------------------------------------------------------------
# TC-DP — diff_parser.py
# ---------------------------------------------------------------------------

def test_diff_parser():
    print("\n── TC-DP  diff_parser.py ──────────────────────────────────────────")

    # TC-DP-001 a TC-DP-005 — _should_include via script auxiliar
    test_script = str(Path(__file__).parent / "test_should_include.py")
    code, out, err = run([PY, test_script])
    check("TC-DP-001..005", "Funcao _should_include filtra corretamente",
          code == 0 and "PASSOU" in out,
          f"exit={code} out={out.strip()} err={err.strip()}")

    # TC-DP-006 — --staged sem staged retorna []
    code, out, _ = run([PY, DIFF_PARSER, "--staged", "--format", "json"])
    ok, data = json_ok(out)
    check("TC-DP-006", "--staged sem staged retorna [] e exit 0",
          ok and isinstance(data, list) and code == 0,
          f"exit={code} data={data}")

    # TC-DP-007 — --staged --files-only sem staged retorna exit 1
    code, out, _ = run([PY, DIFF_PARSER, "--staged", "--files-only", "--format", "json"])
    check("TC-DP-007", "--staged --files-only sem staged retorna exit 1",
          code == 1,
          f"exit={code}")

    # TC-DP-008 — --format json retorna lista
    code, out, _ = run([PY, DIFF_PARSER, "--staged", "--format", "json"])
    ok, data = json_ok(out)
    check("TC-DP-008", "Saida JSON e uma lista",
          ok and isinstance(data, list),
          f"type={type(data).__name__ if data is not None else 'None'}")

    # TC-DP-009 — sem argumentos nao explode
    code, out, err = run([PY, DIFF_PARSER, "--format", "json"])
    ok, data = json_ok(out)
    check("TC-DP-009", "Sem argumentos executa sem erro de execucao",
          ok and isinstance(data, list),
          f"exit={code} err={err[:100]}")

    # TC-DP-010 — --format text produz saida legivel
    code, out, _ = run([PY, DIFF_PARSER, "--staged", "--format", "text"])
    check("TC-DP-010", "Formato text nao explode",
          code in (0, 1),
          f"exit={code}")

    # TC-DP-011 — --for-ai nao explode
    code, out, err = run([PY, DIFF_PARSER, "--staged", "--for-ai"])
    check("TC-DP-011", "--for-ai executa sem excecao",
          code in (0, 1),
          f"exit={code} err={err[:100]}")


# ---------------------------------------------------------------------------
# TC-AI — ai_client.py
# ---------------------------------------------------------------------------

def test_ai_client():
    print("\n── TC-AI  ai_client.py ────────────────────────────────────────────")
    print("  (Testes marcados [SEM API] funcionam sem chave configurada)\n")

    # TC-AI-001 — --list-providers nao explode (requer arquivo posicional dummy)
    code, out, err = run([PY, AI_CLIENT, f("clean.cs"), "--list-providers"])
    check("TC-AI-001", "--list-providers lista provedores e exit 0",
          code == 0 and len(out) > 0,
          f"exit={code} out={out[:200]}")

    # TC-AI-002 — arquivo inexistente retorna exit 1
    code, out, err = run([PY, AI_CLIENT, f("nao_existe.cs")])
    check("TC-AI-002", "Arquivo inexistente retorna exit 1",
          code == 1,
          f"exit={code} err={err[:100]}")

    # TC-AI-003 — sem API key retorna JSON com ai_available
    code, out, err = run([PY, AI_CLIENT, f("clean.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-AI-003", "[SEM API] Retorna JSON com campo ai_available",
          ok and "ai_available" in (data or {}),
          f"exit={code} campos={list(data.keys()) if data else '?'}")
    check("TC-AI-004", "[SEM API] Exit code sempre 0 (mesmo sem IA)",
          code == 0,
          f"exit={code}")

    # TC-AI-005 — JSON contem campos obrigatorios
    if ok and data:
        campos_ok = all(k in data for k in ["file", "ai_available", "provider", "model", "analysis"])
        check("TC-AI-005", "JSON contem file, ai_available, provider, model, analysis",
              campos_ok,
              f"campos={list(data.keys())}")
    else:
        check("TC-AI-005", "JSON contem campos obrigatorios", False, "JSON invalido ou vazio")

    # TC-AI-006 — formato text nao explode
    code, out, err = run([PY, AI_CLIENT, f("clean.cs"), "--format", "text"])
    check("TC-AI-006", "[SEM API] Formato text nao explode",
          code == 0,
          f"exit={code} err={err[:100]}")

    # TC-AI-007 — campo analysis presente mesmo sem IA
    code, out, _ = run([PY, AI_CLIENT, f("clean.cs"), "--format", "json"])
    ok, data = json_ok(out)
    check("TC-AI-007", "[SEM API] Campo analysis presente no JSON",
          ok and "analysis" in (data or {}),
          f"campos={list(data.keys()) if data else '?'}")

    # TC-AI-008 — campo warning presente quando sem IA
    check("TC-AI-008", "[SEM API] Campo warning ou ai_available=false quando sem IA",
          ok and (not data.get("ai_available") or "warning" in (data or {})),
          f"ai_available={data.get('ai_available') if data else '?'}")


# ---------------------------------------------------------------------------
# TC-RU — runner.py
# ---------------------------------------------------------------------------

def test_runner():
    print("\n── TC-RU  runner.py ───────────────────────────────────────────────")

    # TC-RU-001 — --file com caminho completo
    code, out, err = run([PY, RUNNER, "--file", f("clean.cs"), "--rules-only", "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RU-001", "--file com caminho completo funciona",
          ok and "risk_score" in (data or {}),
          f"exit={code} campos={list(data.keys()) if data else '?'} err={err[:100]}")

    # TC-RU-002 — --file com apenas nome do arquivo (busca automatica)
    code, out, err = run([PY, RUNNER, "--file", "clean.cs", "--rules-only", "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RU-002", "--file com so o nome (busca automatica por rglob)",
          ok and "risk_score" in (data or {}),
          f"exit={code} campos={list(data.keys()) if data else '?'} err={err[:100]}")

    # TC-RU-003 — arquivo limpo nao gera bloqueio
    code, out, _ = run([PY, RUNNER, "--file", f("clean.cs"), "--rules-only"])
    check("TC-RU-003", "Arquivo limpo nao causa exit 1 (sem blockers)",
          code == 0,
          f"exit={code}")

    # TC-RU-004 — arquivo com critical causa exit 1
    code, out, _ = run([PY, RUNNER, "--file", f("secrets.cs"), "--rules-only"])
    check("TC-RU-004", "Arquivo com critical causa exit 1",
          code == 1,
          f"exit={code}")

    # TC-RU-005 — --fail-on critical: warning nao bloqueia
    code, out, _ = run([PY, RUNNER, "--file", f("console_warning.cs"), "--rules-only", "--fail-on", "critical"])
    check("TC-RU-005", "--fail-on critical: apenas warnings nao bloqueia (exit 0)",
          code == 0,
          f"exit={code}")

    # TC-RU-006 — --fail-on warning: warning bloqueia
    code, out, _ = run([PY, RUNNER, "--file", f("console_warning.cs"), "--rules-only", "--fail-on", "warning"])
    check("TC-RU-006", "--fail-on warning: warning causa exit 1",
          code == 1,
          f"exit={code}")

    # TC-RU-007 — --format json retorna estrutura valida
    code, out, _ = run([PY, RUNNER, "--file", f("secrets.cs"), "--rules-only", "--format", "json"])
    ok, data = json_ok(out)
    campos_ok = ok and all(k in (data or {}) for k in ["risk_score", "risk_label", "has_blockers", "files_analyzed"])
    check("TC-RU-007", "--format json retorna risk_score, risk_label, has_blockers, files_analyzed",
          campos_ok,
          f"campos={list(data.keys()) if data else '?'}")

    # TC-RU-008 — risk_score > 0 para arquivo com critical
    code, out, _ = run([PY, RUNNER, "--file", f("secrets.cs"), "--rules-only", "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RU-008", "risk_score > 0 para arquivo com critical",
          ok and (data or {}).get("risk_score", 0) > 0,
          f"risk_score={data.get('risk_score') if data else '?'}")

    # TC-RU-009 — risk_score 0 para arquivo limpo
    code, out, _ = run([PY, RUNNER, "--file", f("clean.cs"), "--rules-only", "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RU-009", "risk_score 0 para arquivo limpo",
          ok and (data or {}).get("risk_score", -1) == 0,
          f"risk_score={data.get('risk_score') if data else '?'}")

    # TC-RU-010 — --severity error filtra warnings do relatorio
    code, out, _ = run([PY, RUNNER, "--file", f("console_warning.cs"), "--rules-only",
                        "--severity", "error", "--format", "json"])
    ok, data = json_ok(out)
    files = (data or {}).get("files", [])  # "files" contem dicts; "files_analyzed" contem strings
    issues_count = sum(len(fi.get("issues", [])) for fi in files if isinstance(fi, dict))
    check("TC-RU-010", "--severity error: nenhuma issue de warning no relatorio",
          ok and issues_count == 0,
          f"issues_count={issues_count}")

    # TC-RU-011 — --rules-only: campo ai ausente ou vazio
    code, out, _ = run([PY, RUNNER, "--file", f("clean.cs"), "--rules-only", "--format", "json"])
    ok, data = json_ok(out)
    file_dicts = [fi for fi in (data or {}).get("files", []) if isinstance(fi, dict)]
    ai_present = any(fi.get("ai_analysis") for fi in file_dicts)
    check("TC-RU-011", "--rules-only: sem analise de IA no resultado",
          ok and not ai_present,
          f"ai_present={ai_present}")

    # TC-RU-012 — arquivo inexistente
    code, out, err = run([PY, RUNNER, "--file", "arquivo_que_nao_existe_xyz.cs", "--rules-only"])
    check("TC-RU-012", "Arquivo totalmente inexistente nao explode o runner",
          code in (0, 1),
          f"exit={code} err={err[:100]}")

    # TC-RU-013 — metricas corretas na tabela JSON (nao zeradas)
    code, out, _ = run([PY, RUNNER, "--file", f("deep_nesting.cs"), "--rules-only", "--format", "json"])
    ok, data = json_ok(out)
    files = [fi for fi in (data or {}).get("files", []) if isinstance(fi, dict)]
    metrics = files[0].get("metrics", {}) if files else {}
    classes = metrics.get("classes", [])
    max_nest = max((c.get("max_nesting", 0) for c in classes), default=0)
    check("TC-RU-013", "Metricas nao zeradas: max_nesting > 0 para deep_nesting.cs",
          ok and max_nest > 0,
          f"max_nesting={max_nest} classes={classes}")

    # TC-RU-014 — risk_label correto
    code, out, _ = run([PY, RUNNER, "--file", f("secrets.cs"), "--rules-only", "--format", "json"])
    ok, data = json_ok(out)
    label = (data or {}).get("risk_label", "")
    check("TC-RU-014", "risk_label nao vazio para arquivo com issues",
          ok and len(label) > 0,
          f"risk_label='{label}'")

    # TC-RU-015 — formato text contem secoes esperadas
    code, out, _ = run([PY, RUNNER, "--file", f("secrets.cs"), "--rules-only"])
    check("TC-RU-015", "Formato text contem secao Issues Detectadas",
          "Issues" in out or "issue" in out.lower(),
          f"saida={out[:300]}")

    # TC-RU-016 — formato text contem tabela de metricas
    check("TC-RU-016", "Formato text contem secao Metricas",
          "trica" in out.lower() or "Linhas" in out,
          f"saida={out[:300]}")

    # TC-RU-017 — sem arquivos nao explode
    code, out, err = run([PY, RUNNER, "--staged", "--rules-only", "--format", "json"])
    check("TC-RU-017", "Sem arquivos staged nao explode (exit 0)",
          code == 0,
          f"exit={code} err={err[:100]}")

    # TC-RU-018 — has_blockers correto
    code, out, _ = run([PY, RUNNER, "--file", f("secrets.cs"), "--rules-only", "--format", "json"])
    ok, data = json_ok(out)
    check("TC-RU-018", "has_blockers=true para arquivo com critical/error",
          ok and (data or {}).get("has_blockers") is True,
          f"has_blockers={data.get('has_blockers') if data else '?'}")


# ---------------------------------------------------------------------------
# Relatorio final
# ---------------------------------------------------------------------------

def _find_guardian_dir() -> Path:
    """Retorna .guardian/ na raiz do repositório git, ou próximo ao script."""
    try:
        import subprocess as _sp
        root = _sp.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if root:
            return Path(root) / ".guardian"
    except Exception:
        pass
    return BASE.parent.parent.parent / ".guardian"  # raiz do repo estimada


def generate_html_report(elapsed: float) -> None:
    """Gera relatório HTML dos testes em .guardian/last-test-report.html."""
    from datetime import datetime

    total  = len(_results)
    passed = sum(1 for _, _, ok, _ in _results if ok)
    failed = total - passed

    pct = int(passed / total * 100) if total else 0
    score_color = "#198754" if failed == 0 else ("#ffc107" if failed <= 3 else "#dc3545")
    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    rows_failed = ""
    rows_passed = ""
    for tc_id, desc, ok, detail in _results:
        icon   = "✅" if ok else "❌"
        status = "PASS" if ok else "FAIL"
        color  = "#198754" if ok else "#dc3545"
        det    = f'<br><small style="color:#6c757d">{detail}</small>' if detail and not ok else ""
        row    = (f'<tr><td style="font-family:monospace;font-size:.85rem">{tc_id}</td>'
                  f'<td>{icon} {desc}{det}</td>'
                  f'<td><span style="color:{color};font-weight:600">{status}</span></td></tr>\n')
        if ok:
            rows_passed += row
        else:
            rows_failed += row

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Code Guardian — Testes</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background:#f1f3f5; margin:0; padding:24px; color:#212529; }}
  .container {{ max-width:900px; margin:0 auto; }}
  h1 {{ font-size:1.6rem; margin-bottom:4px; }}
  .subtitle {{ color:#6c757d; font-size:.9rem; margin-bottom:20px; }}
  .card {{ background:#fff; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,.1);
           padding:20px; margin-bottom:20px; }}
  .score-card {{ background:{score_color}; color:#fff; border-radius:8px;
                 padding:20px 28px; display:inline-block; margin-bottom:20px; }}
  .score-card .num {{ font-size:2.8rem; font-weight:700; line-height:1; }}
  .score-card .lbl {{ font-size:1rem; margin-top:4px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.88rem; }}
  th, td {{ padding:7px 12px; border-bottom:1px solid #dee2e6; text-align:left; vertical-align:top; }}
  th {{ background:#f8f9fa; font-weight:600; }}
  tr:last-child td {{ border-bottom:none; }}
  h2 {{ font-size:1rem; font-weight:700; margin:0 0 12px; color:#495057; }}
  footer {{ text-align:center; color:#adb5bd; font-size:.8rem; margin-top:28px; }}
</style>
</head>
<body>
<div class="container">
  <h1>🛡️ Code Guardian — Suite de Testes</h1>
  <p class="subtitle">Executado em {ts} &nbsp;|&nbsp; {elapsed:.1f}s</p>

  <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start;margin-bottom:8px">
    <div class="score-card">
      <div class="num">{passed}/{total}</div>
      <div class="lbl">{"✅ Todos passaram" if failed == 0 else f"❌ {failed} falharam"} &nbsp;({pct}%)</div>
    </div>
    <div class="card" style="flex:1;min-width:200px;padding:16px 20px">
      <table>
        <tr><th>Status</th><th>Qtd</th></tr>
        <tr><td>✅ PASS</td><td style="font-weight:700;color:#198754">{passed}</td></tr>
        <tr><td>❌ FAIL</td><td style="font-weight:700;color:#dc3545">{failed}</td></tr>
        <tr><td>Total</td><td style="font-weight:700">{total}</td></tr>
      </table>
    </div>
  </div>

  {"" if not rows_failed else f'''
  <div class="card">
    <h2>❌ Casos que falharam ({failed})</h2>
    <table>
      <thead><tr><th style="width:120px">ID</th><th>Descrição</th><th style="width:70px">Status</th></tr></thead>
      <tbody>{rows_failed}</tbody>
    </table>
  </div>'''}

  <div class="card">
    <h2>✅ Casos que passaram ({passed})</h2>
    <table>
      <thead><tr><th style="width:120px">ID</th><th>Descrição</th><th style="width:70px">Status</th></tr></thead>
      <tbody>{rows_passed}</tbody>
    </table>
  </div>

  <footer>Code Guardian Tests &nbsp;|&nbsp; {ts}</footer>
</div>
</body>
</html>"""

    guardian_dir = _find_guardian_dir()
    guardian_dir.mkdir(parents=True, exist_ok=True)
    out_path = guardian_dir / "last-test-report.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"\n📄 Relatorio HTML: {out_path.resolve()}")


def print_report():
    total = len(_results)
    passed = sum(1 for _, _, ok, _ in _results if ok)
    failed = total - passed

    print("\n" + "=" * 65)
    print(f"  RESULTADO FINAL: {passed}/{total} PASSOU  |  {failed} FALHOU")
    print("=" * 65)

    if failed > 0:
        print("\nCasos que falharam:")
        for tc_id, desc, ok, detail in _results:
            if not ok:
                print(f"  ❌ {tc_id}: {desc}")
                if detail:
                    print(f"     {detail}")

    print()
    return failed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Executa testes do Code Guardian")
    parser.add_argument("--script", choices=["re", "me", "dp", "ai", "ru"],
                        help="Executar apenas o script especificado")
    args = parser.parse_args()

    inicio = time.time()
    print("Code Guardian — Suite de Testes Automatizados")
    print(f"Base: {BASE}")
    print(f"Fixtures: {FIXTURES}")

    if not FIXTURES.exists():
        print(f"\nERRO: Diretorio de fixtures nao encontrado: {FIXTURES}")
        print("Execute primeiro: mkdir -p tests/fixtures (e crie as fixtures)")
        sys.exit(1)

    script = args.script
    if not script or script == "re":
        test_rule_engine()
    if not script or script == "me":
        test_metrics()
    if not script or script == "dp":
        test_diff_parser()
    if not script or script == "ai":
        test_ai_client()
    if not script or script == "ru":
        test_runner()

    elapsed = time.time() - inicio
    print(f"\nTempo total: {elapsed:.1f}s")
    failed = print_report()
    generate_html_report(elapsed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
