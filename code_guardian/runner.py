#!/usr/bin/env python3
"""
Code Guardian Runner — Orquestrador CLI completo.

Executa análise estática (rule_engine + metrics) e opcionalmente análise de IA
em arquivos C# alterados no git ou em um arquivo específico.

Uso:
    python runner.py                          # diff vs origin/main
    python runner.py --staged                 # apenas staged
    python runner.py --file Services/X.cs     # arquivo específico
    python runner.py --scan                   # varre diretório atual recursivamente
    python runner.py --scan --dir C:/projeto  # varre diretório específico
    python runner.py --rules-only             # sem IA
    python runner.py --severity error         # somente critical/error
    python runner.py --format json            # saída JSON (para CI)
    python runner.py --output relatorio.html  # salva relatório HTML
    python runner.py --timeout 90             # timeout por subprocess (padrão: 60s)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json
import os
import subprocess
import tempfile
import argparse
import time
from datetime import datetime
from pathlib import Path

# Caminho base dos scripts
_SCRIPT_DIR = Path(__file__).parent

_RULE_ENGINE = _SCRIPT_DIR / "rule_engine.py"
_METRICS     = _SCRIPT_DIR / "metrics.py"
_DIFF_PARSER = _SCRIPT_DIR / "diff_parser.py"
_AI_CLIENT   = _SCRIPT_DIR / "ai_client.py"

# Padrões de exclusão para scan de diretório (mesmos do diff_parser)
_EXCLUDE_PATTERNS = [
    "/Migrations/",
    ".Designer.cs",
    "/obj/",
    "/bin/",
    "/packages/",
    "AssemblyInfo.cs",
    ".g.cs",
    ".g.i.cs",
    "TemporaryGeneratedFile",
    "/node_modules/",
    "/.vs/",
    "/TestResults/",
]

_SCORE_MAP = {"critical": 25, "error": 10, "warning": 3, "info": 1}
_ICONS     = {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "🔵"}

# Cores HTML por severidade
_HTML_COLORS = {
    "critical": "#dc3545",
    "error":    "#fd7e14",
    "warning":  "#ffc107",
    "info":     "#0d6efd",
    "ok":       "#198754",
}


def _find_guardian_dir() -> Path:
    """Retorna o diretório .guardian/ na raiz do repositório git (ou CWD)."""
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        ).stdout.strip()
        if root:
            return Path(root) / ".guardian"
    except Exception:
        pass
    return Path.cwd() / ".guardian"


def _resolve_file(name: str) -> str:
    """Resolve o caminho do arquivo.

    Tenta, em ordem:
    1. Caminho exato como passado
    2. Busca recursiva a partir do diretório atual
    3. Busca recursiva a partir do git root
    """
    p = Path(name)
    if p.exists():
        return str(p)

    # Busca pelo nome do arquivo (ou fragmento de caminho) no diretório atual
    cwd = Path.cwd()
    matches = list(cwd.rglob(name)) or list(cwd.rglob(p.name))
    if matches:
        if len(matches) == 1:
            return str(matches[0])
        # Mais de um — preferir o que contém o fragmento original
        for m in matches:
            if name.replace("\\", "/") in m.as_posix():
                return str(m)
        print(f"⚠️  Múltiplos arquivos encontrados para '{name}':")
        for i, m in enumerate(matches, 1):
            print(f"   {i}. {m}")
        print(f"   Usando: {matches[0]}")
        return str(matches[0])

    # Tenta a partir do git root
    try:
        git_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
        ).stdout.strip()
        if git_root:
            git_matches = list(Path(git_root).rglob(name)) or list(Path(git_root).rglob(p.name))
            if git_matches:
                return str(git_matches[0])
    except Exception:
        pass

    return name  # devolve original — erro será reportado pelo script filho


def _run_script(script: Path, args: list[str], timeout: int = 60) -> dict | list | None:
    """Executa um script Python e retorna o JSON parseado.

    Usa arquivo temporário em vez de PIPE para evitar o bug de UnicodeDecodeError
    no _readerthread do Python 3.14 no Windows.

    Parâmetros:
        script:  Caminho do script Python a executar.
        args:    Argumentos adicionais para o script.
        timeout: Tempo máximo de espera em segundos (padrão: 60).
                 Se excedido, retorna None e imprime aviso em stderr.
    """
    cmd = [sys.executable, str(script)] + args
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8:replace"

    try:
        with tempfile.TemporaryFile() as stdout_tmp, tempfile.TemporaryFile() as stderr_tmp:
            proc = subprocess.Popen(
                cmd,
                stdout=stdout_tmp,
                stderr=stderr_tmp,
                env=env,
            )
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                print(
                    f"[guardian] Aviso: timeout ({timeout}s) ao executar {script.name} -- resultado ignorado.",
                    file=sys.stderr,
                )
                return None

            stdout_tmp.seek(0)
            raw = stdout_tmp.read()

            if proc.returncode != 0:
                stderr_tmp.seek(0)
                err = stderr_tmp.read().decode("utf-8", errors="replace").strip()
                if err:
                    print(f"[guardian] {script.name} (exit {proc.returncode}): {err[:300]}", file=sys.stderr)

        stdout = raw.decode("utf-8", errors="replace") if raw else ""
        if stdout.strip():
            return json.loads(stdout)
        return None
    except json.JSONDecodeError as e:
        print(f"[guardian] Erro ao parsear JSON de {script.name}: {e}", file=sys.stderr)
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
        print(f"[guardian] Erro ao executar {script.name}: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def _should_exclude(file_path: str) -> bool:
    """Verifica se o arquivo deve ser excluído da análise."""
    posix_path = file_path.replace("\\", "/")
    return any(pattern in posix_path for pattern in _EXCLUDE_PATTERNS)


def _scan_directory(directory: str) -> list[str]:
    """Varre o diretório recursivamente buscando arquivos .cs."""
    root = Path(directory)
    if not root.exists():
        print(f"⚠️  Diretório não encontrado: {directory}")
        return []

    cs_files = []
    for f in sorted(root.rglob("*.cs")):
        path_str = str(f)
        if not _should_exclude(path_str):
            cs_files.append(path_str)

    return cs_files


def _get_changed_files(staged: bool, base: str) -> list[str]:
    """Retorna lista de arquivos .cs alterados."""
    args = ["--files-only", "--format", "json"]
    if staged:
        args.append("--staged")
    else:
        args += ["--base", base]
    result = _run_script(_DIFF_PARSER, args)
    if isinstance(result, list):
        return result
    return []


def _run_rule_engine(file_path: str, severity: str, timeout: int = 60) -> list[dict]:
    """Executa rule_engine.py e retorna issues."""
    args = [file_path, "--format", "json", "--severity", severity]
    result = _run_script(_RULE_ENGINE, args, timeout=timeout)
    return result if isinstance(result, list) else []


def _run_metrics(file_path: str, timeout: int = 60) -> dict | None:
    """Executa metrics.py e retorna métricas."""
    result = _run_script(_METRICS, [file_path, "--format", "json"], timeout=timeout)
    return result if isinstance(result, dict) else None


def _run_ai(file_path: str, timeout: int = 120) -> str | None:
    """Executa ai_client.py e retorna texto da análise.

    A IA recebe timeout mais generoso (padrão: 120s) pois pode envolver
    chamadas de rede a APIs externas como Gemini.
    Usa TemporaryFile para evitar o bug de _readerthread no Python 3.14/Windows.
    """
    cmd = [sys.executable, str(_AI_CLIENT), file_path]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8:replace"

    fname = Path(file_path).name
    try:
        with tempfile.TemporaryFile() as stdout_tmp:
            proc = subprocess.Popen(
                cmd,
                stdout=stdout_tmp,
                stderr=sys.stderr,  # mensagens de provedor vão direto ao terminal
                env=env,
            )
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                print(
                    f"[guardian] Aviso: timeout ({timeout}s) na análise de IA para {fname} -- ignorado.",
                    file=sys.stderr,
                )
                return None

            stdout_tmp.seek(0)
            raw = stdout_tmp.read()

        output = raw.decode("utf-8", errors="replace").strip() if raw else ""
        if output and not output.startswith("[guardian] Erro"):
            return output
        return None
    except (subprocess.SubprocessError, OSError) as e:
        print(f"[guardian] Erro ao executar ai_client para {fname}: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def _calculate_risk_score(all_issues: list[dict]) -> tuple[int, str]:
    """Calcula o Risk Score e retorna (score, classificação)."""
    score = sum(_SCORE_MAP.get(i.get("severity", ""), 0) for i in all_issues)
    if score <= 10:
        label = "✅ Baixo Risco"
    elif score <= 30:
        label = "⚠️ Risco Moderado"
    elif score <= 60:
        label = "🔴 Alto Risco"
    else:
        label = "🚫 Risco Crítico"
    return score, label


def _risk_score_html_color(score: int) -> str:
    """Retorna a cor de fundo HTML para o card de Risk Score."""
    if score <= 10:
        return "#d1e7dd"   # verde claro
    if score <= 30:
        return "#fff3cd"   # amarelo claro
    if score <= 60:
        return "#f8d7da"   # vermelho claro
    return "#842029"       # crítico (fundo escuro)


def _risk_score_html_text_color(score: int) -> str:
    """Retorna a cor do texto para o card de Risk Score."""
    if score > 60:
        return "#ffffff"
    return "#212529"


def _format_text_report(
    files: list[str],
    issues_by_file: dict[str, list[dict]],
    metrics_by_file: dict[str, dict],
    ai_by_file: dict[str, str],
    risk_score: int,
    risk_label: str,
) -> str:
    """Formata o relatório final em texto."""
    all_issues = [i for issues in issues_by_file.values() for i in issues]

    counts = {sev: 0 for sev in ("critical", "error", "warning", "info")}
    for issue in all_issues:
        sev = issue.get("severity", "info")
        if sev in counts:
            counts[sev] += 1

    lines = [
        "# 🛡️ Code Guardian - Review",
        "",
        f"**Arquivos analisados**: {len(files)}",
        f"**Risk Score**: {risk_score} — {risk_label}",
        "",
        "| Severidade | Qtd |",
        "|-----------|-----|",
        f"| 🔴 Critical | {counts['critical']} |",
        f"| 🟠 Error    | {counts['error']} |",
        f"| 🟡 Warning  | {counts['warning']} |",
        f"| 🔵 Info     | {counts['info']} |",
        "",
        "---",
        "",
    ]

    for file in files:
        issues  = issues_by_file.get(file, [])
        metrics = metrics_by_file.get(file)
        ai_text = ai_by_file.get(file)

        lines.append(f"## 📁 `{file}`")
        lines.append("")

        if issues:
            lines.append("### Issues Detectadas")
            lines.append("")
            for issue in issues:
                sev      = issue.get("severity", "info")
                icon     = _ICONS.get(sev, "⚪")
                cat      = issue.get("category", "")
                line_no  = issue.get("line", "?")
                msg      = issue.get("message", "")
                source   = issue.get("source", "")
                source_tag = f" *[{source}]*" if source else ""
                lines.append(f"- {icon} **L{line_no}** [{cat}]{source_tag} {msg}")
            lines.append("")
        else:
            lines.append("✅ Nenhuma issue encontrada pelo Rule Engine.")
            lines.append("")

        if metrics:
            m_issues    = metrics.get("issues", [])
            total_lines = metrics.get("total_lines", 0)

            # Agregar valores das classes (métricas ficam dentro de classes[])
            classes    = metrics.get("classes", [])
            max_method = max(
                (max((m["line_count"] for m in cls.get("methods", [])), default=0) for cls in classes),
                default=0,
            )
            max_nesting = max((cls.get("max_nesting", 0) for cls in classes), default=0)
            deps        = max((cls.get("constructor_deps", 0) for cls in classes), default=0)

            lines.append("### Métricas")
            lines.append("")
            lines.append("| Métrica | Valor | Status |")
            lines.append("|---------|-------|--------|")
            lines.append(f"| Linhas totais | {total_lines} | {'🟡' if total_lines > 300 else '✅'} |")
            lines.append(f"| Maior método | {max_method} L | {'🟠' if max_method > 30 else '✅'} |")
            lines.append(f"| Nesting máximo | {max_nesting} | {'🟠' if max_nesting > 3 else '✅'} |")
            lines.append(f"| Dependências | {deps} | {'🟡' if deps > 5 else '✅'} |")

            if m_issues:
                lines.append("")
                for mi in m_issues:
                    sev  = mi.get("severity", "warning")
                    icon = _ICONS.get(sev, "⚪")
                    lines.append(f"- {icon} {mi.get('message', '')}")
            lines.append("")

        if ai_text:
            lines.append("### Análise de IA")
            lines.append("")
            lines.append(ai_text)
            lines.append("")

        lines.append("---")
        lines.append("")

    # ── Plano de Correção ──────────────────────────────────────────────────
    blockers = [i for i in all_issues if i.get("severity") in ("critical", "error")]
    improvements = [i for i in all_issues if i.get("severity") in ("warning",)]

    if blockers or improvements:
        lines.append("## 📋 Plano de Correção")
        lines.append("")

        total_fixes = len(blockers) + len(improvements)
        lines.append(
            f"> {total_fixes} correções | "
            f"{len(blockers)} bloqueiam merge | "
            f"{len(improvements)} melhorias recomendadas"
        )
        lines.append("")

        if blockers:
            lines.append("### 🚫 Correções Obrigatórias (bloqueiam merge)")
            lines.append("")
            for idx, issue in enumerate(blockers, 1):
                sev   = issue.get("severity", "error")
                icon  = _ICONS.get(sev, "🔴")
                cat   = issue.get("category", "")
                msg   = issue.get("message", "")
                fname = issue.get("file", "?")
                lno   = issue.get("line", "?")
                lines.append(f"| {idx} | `{Path(fname).name}:{lno}` | {icon} {cat} | {msg} |")
            lines.append("")

        if improvements:
            lines.append("### ⚠️ Melhorias Recomendadas")
            lines.append("")
            for idx, issue in enumerate(improvements, len(blockers) + 1):
                cat   = issue.get("category", "")
                msg   = issue.get("message", "")
                fname = issue.get("file", "?")
                lno   = issue.get("line", "?")
                lines.append(f"| {idx} | `{Path(fname).name}:{lno}` | 🟡 {cat} | {msg} |")
            lines.append("")

        lines.append("> Após corrigir, revalide: `python code_guardian/runner.py --staged --rules-only`")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("> 🛡️ Code Guardian | Scripts: rule_engine.py, metrics.py, diff_parser.py, ai_client.py")

    return "\n".join(lines)


def _format_json_report(
    files: list[str],
    issues_by_file: dict[str, list[dict]],
    metrics_by_file: dict[str, dict],
    risk_score: int,
    risk_label: str,
) -> str:
    """Formata o relatório em JSON (para CI/CD)."""
    all_issues   = [i for issues in issues_by_file.values() for i in issues]
    has_blockers = any(i.get("severity") in ("critical", "error") for i in all_issues)

    report = {
        "risk_score":    risk_score,
        "risk_label":    risk_label,
        "has_blockers":  has_blockers,
        "files_analyzed": files,
        "summary": {
            "critical": sum(1 for i in all_issues if i.get("severity") == "critical"),
            "error":    sum(1 for i in all_issues if i.get("severity") == "error"),
            "warning":  sum(1 for i in all_issues if i.get("severity") == "warning"),
            "info":     sum(1 for i in all_issues if i.get("severity") == "info"),
        },
        "files": [
            {
                "file":    f,
                "issues":  issues_by_file.get(f, []),
                "metrics": metrics_by_file.get(f),
            }
            for f in files
        ],
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


def _format_html_report(
    files: list[str],
    issues_by_file: dict[str, list[dict]],
    metrics_by_file: dict[str, dict],
    ai_by_file: dict[str, str],
    risk_score: int,
    risk_label: str,
    elapsed_seconds: float,
) -> str:
    """Gera relatório HTML com Design System da empresa (Prosoft), CSS inline."""
    all_issues = [i for issues in issues_by_file.values() for i in issues]

    counts = {sev: 0 for sev in ("critical", "error", "warning", "info")}
    for issue in all_issues:
        sev = issue.get("severity", "info")
        if sev in counts:
            counts[sev] += 1

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Cores do Risk Score (DS: Danger/Warning/Success)
    if risk_score <= 10:
        score_bg, score_fg, score_border = "#D4EDDA", "#155724", "#28A745"
        score_label = "Baixo Risco"
    elif risk_score <= 30:
        score_bg, score_fg, score_border = "#FFF3CD", "#856404", "#FFC107"
        score_label = "Risco Moderado"
    elif risk_score <= 60:
        score_bg, score_fg, score_border = "#F8D7DA", "#721C24", "#DC3545"
        score_label = "Alto Risco"
    else:
        score_bg, score_fg, score_border = "#DC3545", "#FFFFFF", "#C82333"
        score_label = "Risco Cr&#237;tico"

    # Fórmula do Risk Score para o tooltip
    formula_parts = []
    if counts["critical"]: formula_parts.append(f"{counts['critical']} critical &times; 25")
    if counts["error"]:    formula_parts.append(f"{counts['error']} error &times; 10")
    if counts["warning"]:  formula_parts.append(f"{counts['warning']} warning &times; 3")
    if counts["info"]:     formula_parts.append(f"{counts['info']} info &times; 1")
    formula_str = " + ".join(formula_parts) if formula_parts else "0"

    # Badges de severidade (DS: badges como pílulas)
    _SEV_BADGE = {
        "critical": ('background:#F8D7DA;color:#721C24', 'Critical'),
        "error":    ('background:#FFE5D0;color:#7D3A0F', 'Error'),
        "warning":  ('background:#FFF3CD;color:#856404', 'Warning'),
        "info":     ('background:#D1ECF1;color:#0C5460', 'Info'),
    }
    _SEV_DOT = {
        "critical": "#DC3545",
        "error":    "#FD7E14",
        "warning":  "#FFC107",
        "info":     "#17A2B8",
    }

    def sev_badge(sev: str) -> str:
        style, label = _SEV_BADGE.get(sev, ('background:#E2E3E5;color:#383D41', sev.upper()))
        return (f'<span style="display:inline-block;padding:3px 8px;border-radius:10px;'
                f'font-size:11px;font-weight:600;{style}">{label}</span>')

    def dot(sev: str) -> str:
        color = _SEV_DOT.get(sev, "#6C757D")
        return (f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
                f'background:{color};margin-right:6px;vertical-align:middle"></span>')

    def status_cell(value: int | float, warn: int, err: int) -> str:
        if value > err:
            return (f'<span style="color:#DC3545;font-weight:600">{value}'
                    f'<span style="font-size:11px;margin-left:3px">&#9650;</span></span>')
        if value > warn:
            return f'<span style="color:#856404;font-weight:600">{value}</span>'
        return f'<span style="color:#155724;font-weight:500">{value} &#10003;</span>'

    # Seções por arquivo
    file_sections: list[str] = []
    for file in files:
        issues  = issues_by_file.get(file, [])
        metrics = metrics_by_file.get(file)
        ai_text = ai_by_file.get(file)
        parts: list[str] = []

        # Issues
        if issues:
            rows = []
            for iss in issues:
                sev     = iss.get("severity", "info")
                line_no = iss.get("line", "?")
                cat     = iss.get("category", "")
                msg     = iss.get("message", "").replace("<", "&lt;").replace(">", "&gt;")
                source  = iss.get("source", "")
                src_tag = (f'<span style="font-size:10px;color:#6C757D;margin-right:4px">[{source}]</span>'
                           if source else "")
                rows.append(
                    f'<tr style="border-bottom:1px solid #E9ECEF">'
                    f'<td style="padding:8px 12px;color:#6C757D;font-size:12px;white-space:nowrap">{line_no}</td>'
                    f'<td style="padding:8px 12px">{sev_badge(sev)}</td>'
                    f'<td style="padding:8px 12px;font-size:12px;color:#495057">{cat}</td>'
                    f'<td style="padding:8px 12px;font-size:13px">{src_tag}{msg}</td>'
                    f'</tr>'
                )
            parts.append(
                '<p style="font-size:11px;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.06em;color:#6C757D;margin:0 0 8px">Issues Detectadas</p>'
                '<table style="width:100%;border-collapse:collapse;margin-bottom:16px">'
                '<thead><tr style="background:#F8F9FA;border-bottom:2px solid #DEE2E6">'
                '<th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;'
                'text-transform:uppercase;color:#6C757D">Linha</th>'
                '<th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;'
                'text-transform:uppercase;color:#6C757D">Severidade</th>'
                '<th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;'
                'text-transform:uppercase;color:#6C757D">Categoria</th>'
                '<th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;'
                'text-transform:uppercase;color:#6C757D">Mensagem</th>'
                '</tr></thead>'
                '<tbody>' + "".join(rows) + '</tbody></table>'
            )
        else:
            parts.append(
                '<div style="background:#D4EDDA;border:1px solid #28A745;border-radius:6px;'
                'padding:10px 14px;color:#155724;font-size:13px;font-weight:500">'
                '&#10003; Nenhuma issue encontrada pelo Rule Engine.</div>'
            )

        # Métricas
        if metrics:
            classes     = metrics.get("classes", [])
            total_lines = metrics.get("total_lines", 0)
            max_method  = max(
                (max((m["line_count"] for m in cls.get("methods", [])), default=0) for cls in classes),
                default=0,
            )
            max_nesting = max((cls.get("max_nesting", 0) for cls in classes), default=0)
            deps        = max((cls.get("constructor_deps", 0) for cls in classes), default=0)

            parts.append(
                '<p style="font-size:11px;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.06em;color:#6C757D;margin:16px 0 8px">M&#233;tricas</p>'
                '<table style="width:100%;border-collapse:collapse;margin-bottom:8px">'
                '<thead><tr style="background:#F8F9FA;border-bottom:2px solid #DEE2E6">'
                '<th style="padding:7px 12px;text-align:left;font-size:11px;font-weight:600;'
                'text-transform:uppercase;color:#6C757D">M&#233;trica</th>'
                '<th style="padding:7px 12px;text-align:left;font-size:11px;font-weight:600;'
                'text-transform:uppercase;color:#6C757D">Valor</th>'
                '<th style="padding:7px 12px;text-align:left;font-size:11px;font-weight:600;'
                'text-transform:uppercase;color:#6C757D">Limite</th>'
                '</tr></thead><tbody>'
                f'<tr style="border-bottom:1px solid #E9ECEF"><td style="padding:7px 12px;font-size:13px">Linhas totais</td>'
                f'<td style="padding:7px 12px">{status_cell(total_lines, 200, 300)}</td>'
                f'<td style="padding:7px 12px;font-size:11px;color:#ADB5BD">recomendado &lt; 300</td></tr>'
                f'<tr style="border-bottom:1px solid #E9ECEF"><td style="padding:7px 12px;font-size:13px">Maior m&#233;todo (linhas)</td>'
                f'<td style="padding:7px 12px">{status_cell(max_method, 20, 30)}</td>'
                f'<td style="padding:7px 12px;font-size:11px;color:#ADB5BD">recomendado &lt; 30</td></tr>'
                f'<tr style="border-bottom:1px solid #E9ECEF"><td style="padding:7px 12px;font-size:13px">Nesting m&#225;ximo</td>'
                f'<td style="padding:7px 12px">{status_cell(max_nesting, 2, 3)}</td>'
                f'<td style="padding:7px 12px;font-size:11px;color:#ADB5BD">recomendado &lt; 3</td></tr>'
                f'<tr><td style="padding:7px 12px;font-size:13px">Depend&#234;ncias (construtor)</td>'
                f'<td style="padding:7px 12px">{status_cell(deps, 4, 5)}</td>'
                f'<td style="padding:7px 12px;font-size:11px;color:#ADB5BD">recomendado &lt; 5</td></tr>'
                '</tbody></table>'
            )

        # IA
        if ai_text:
            ai_esc = ai_text.replace("<", "&lt;").replace(">", "&gt;")
            parts.append(
                '<p style="font-size:11px;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.06em;color:#6C757D;margin:16px 0 8px">An&#225;lise de IA</p>'
                '<div style="background:#F8F9FA;border-left:4px solid #184194;padding:12px 16px;'
                f'font-size:13px;white-space:pre-wrap;border-radius:0 4px 4px 0">{ai_esc}</div>'
            )

        file_name_display = Path(file).as_posix()
        file_sections.append(
            '<div style="margin-bottom:24px;border:1px solid #DEE2E6;border-radius:8px;'
            'overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)">'
            f'<div style="background:#184194;color:#FFFFFF;padding:10px 16px;'
            f'font-family:Consolas,\'Courier New\',monospace;font-size:13px;word-break:break-all">'
            f'&#128193; {file_name_display}</div>'
            f'<div style="background:#FFFFFF;padding:16px">{"".join(parts)}</div>'
            '</div>'
        )

    # Tabela de resumo
    summary_rows = (
        f'<tr style="border-bottom:1px solid #E9ECEF"><td style="padding:8px 16px">'
        f'{dot("critical")}<span style="font-size:13px;color:#495057">Critical</span></td>'
        f'<td style="padding:8px 16px;font-weight:700;color:#DC3545;font-size:16px">{counts["critical"]}</td></tr>'
        f'<tr style="border-bottom:1px solid #E9ECEF"><td style="padding:8px 16px">'
        f'{dot("error")}<span style="font-size:13px;color:#495057">Error</span></td>'
        f'<td style="padding:8px 16px;font-weight:700;color:#FD7E14;font-size:16px">{counts["error"]}</td></tr>'
        f'<tr style="border-bottom:1px solid #E9ECEF"><td style="padding:8px 16px">'
        f'{dot("warning")}<span style="font-size:13px;color:#495057">Warning</span></td>'
        f'<td style="padding:8px 16px;font-weight:700;color:#856404;font-size:16px">{counts["warning"]}</td></tr>'
        f'<tr><td style="padding:8px 16px">'
        f'{dot("info")}<span style="font-size:13px;color:#495057">Info</span></td>'
        f'<td style="padding:8px 16px;font-weight:700;color:#17A2B8;font-size:16px">{counts["info"]}</td></tr>'
    )

    # ── Plano de Correção (HTML) ─────────────────────────────────────────
    blockers     = [i for i in all_issues if i.get("severity") in ("critical", "error")]
    improvements = [i for i in all_issues if i.get("severity") in ("warning",)]

    if blockers or improvements:
        plan_parts: list[str] = []
        total_fixes = len(blockers) + len(improvements)
        plan_parts.append(
            '<div style="margin-bottom:24px;border:1px solid #DEE2E6;border-radius:8px;'
            'overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)">'
            '<div style="background:#184194;color:#FFFFFF;padding:10px 16px;font-size:14px;'
            'font-weight:600">&#128203; Plano de Corre&#231;&#227;o</div>'
            '<div style="background:#FFFFFF;padding:16px">'
            f'<p style="margin:0 0 12px;font-size:13px;color:#6C757D">'
            f'{total_fixes} corre&#231;&#245;es &bull; '
            f'{len(blockers)} bloqueiam merge &bull; '
            f'{len(improvements)} melhorias recomendadas</p>'
        )

        # Tabela
        plan_parts.append(
            '<table style="width:100%;border-collapse:collapse">'
            '<thead><tr style="background:#F8F9FA;border-bottom:2px solid #DEE2E6">'
            '<th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;'
            'text-transform:uppercase;color:#6C757D;width:36px">#</th>'
            '<th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;'
            'text-transform:uppercase;color:#6C757D">Arquivo</th>'
            '<th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;'
            'text-transform:uppercase;color:#6C757D">Severidade</th>'
            '<th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;'
            'text-transform:uppercase;color:#6C757D">Issue</th>'
            '<th style="padding:8px 12px;text-align:left;font-size:11px;font-weight:600;'
            'text-transform:uppercase;color:#6C757D">A&#231;&#227;o</th>'
            '</tr></thead><tbody>'
        )

        all_plan = [(i, True) for i in blockers] + [(i, False) for i in improvements]
        for idx, (issue, is_blocker) in enumerate(all_plan, 1):
            sev   = issue.get("severity", "info")
            fname = Path(issue.get("file", "")).name
            lno   = issue.get("line", "?")
            cat   = issue.get("category", "")
            msg   = issue.get("message", "").replace("<", "&lt;").replace(">", "&gt;")
            bg    = "#FFF5F5" if is_blocker else "#FFFFFF"
            plan_parts.append(
                f'<tr style="border-bottom:1px solid #E9ECEF;background:{bg}">'
                f'<td style="padding:8px 12px;font-size:12px;color:#6C757D;text-align:center">{idx}</td>'
                f'<td style="padding:8px 12px;font-family:Consolas,monospace;font-size:12px">{fname}:{lno}</td>'
                f'<td style="padding:8px 12px">{sev_badge(sev)}</td>'
                f'<td style="padding:8px 12px;font-size:12px;font-weight:600;color:#495057">{cat}</td>'
                f'<td style="padding:8px 12px;font-size:12px;color:#495057">{msg}</td>'
                f'</tr>'
            )

        plan_parts.append('</tbody></table>')
        plan_parts.append(
            '<p style="margin:12px 0 0;font-size:12px;color:#6C757D;font-style:italic">'
            'Ap&#243;s corrigir, revalide: '
            '<code style="background:#F8F9FA;padding:2px 6px;border-radius:3px;font-size:11px">'
            'python code_guardian/runner.py --staged --rules-only</code></p>'
        )
        plan_parts.append('</div></div>')
        correction_plan_html = "\n".join(plan_parts)
    else:
        correction_plan_html = (
            '<div style="margin-bottom:24px;background:#D4EDDA;border:1px solid #28A745;'
            'border-radius:8px;padding:14px 18px;color:#155724;font-size:14px;font-weight:500">'
            '&#10003; C&#243;digo aprovado &#8212; nenhuma corre&#231;&#227;o necess&#225;ria.</div>'
        )

    # Modal de informação do Risk Score (JS puro, sem dependências)
    modal_js = """
function toggleRiskInfo() {
  var m = document.getElementById('riskModal');
  m.style.display = m.style.display === 'flex' ? 'none' : 'flex';
}
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') document.getElementById('riskModal').style.display = 'none';
});
"""

    modal_html = f"""
<div id="riskModal" onclick="if(event.target===this)this.style.display='none'"
  style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;
         background:rgba(0,0,0,.45);z-index:1000;align-items:center;justify-content:center">
  <div style="background:#fff;border-radius:8px;padding:28px 32px;max-width:500px;width:90%;
              box-shadow:0 8px 32px rgba(0,0,0,.18);position:relative">
    <button onclick="document.getElementById('riskModal').style.display='none'"
      style="position:absolute;top:12px;right:16px;background:none;border:none;
             font-size:20px;cursor:pointer;color:#6C757D;line-height:1">&#215;</button>
    <h3 style="font-size:16px;font-weight:600;color:#184194;margin-bottom:16px">
      &#128737; Como o Risk Score &#233; calculado</h3>
    <p style="font-size:13px;color:#495057;margin-bottom:12px">
      O Risk Score &#233; a soma ponderada de todas as issues encontradas:</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:16px">
      <thead><tr style="background:#F8F9FA;border-bottom:2px solid #DEE2E6">
        <th style="padding:8px 12px;text-align:left;color:#6C757D;font-size:11px;text-transform:uppercase">Severidade</th>
        <th style="padding:8px 12px;text-align:center;color:#6C757D;font-size:11px;text-transform:uppercase">Peso</th>
        <th style="padding:8px 12px;text-align:center;color:#6C757D;font-size:11px;text-transform:uppercase">Qtd</th>
        <th style="padding:8px 12px;text-align:right;color:#6C757D;font-size:11px;text-transform:uppercase">Pontos</th>
      </tr></thead>
      <tbody>
        <tr style="border-bottom:1px solid #E9ECEF">
          <td style="padding:8px 12px">{dot("critical")}Critical</td>
          <td style="padding:8px 12px;text-align:center;font-weight:600">&#215; 25</td>
          <td style="padding:8px 12px;text-align:center">{counts["critical"]}</td>
          <td style="padding:8px 12px;text-align:right;font-weight:600;color:#DC3545">{counts["critical"] * 25}</td>
        </tr>
        <tr style="border-bottom:1px solid #E9ECEF">
          <td style="padding:8px 12px">{dot("error")}Error</td>
          <td style="padding:8px 12px;text-align:center;font-weight:600">&#215; 10</td>
          <td style="padding:8px 12px;text-align:center">{counts["error"]}</td>
          <td style="padding:8px 12px;text-align:right;font-weight:600;color:#FD7E14">{counts["error"] * 10}</td>
        </tr>
        <tr style="border-bottom:1px solid #E9ECEF">
          <td style="padding:8px 12px">{dot("warning")}Warning</td>
          <td style="padding:8px 12px;text-align:center;font-weight:600">&#215; 3</td>
          <td style="padding:8px 12px;text-align:center">{counts["warning"]}</td>
          <td style="padding:8px 12px;text-align:right;font-weight:600;color:#856404">{counts["warning"] * 3}</td>
        </tr>
        <tr>
          <td style="padding:8px 12px">{dot("info")}Info</td>
          <td style="padding:8px 12px;text-align:center;font-weight:600">&#215; 1</td>
          <td style="padding:8px 12px;text-align:center">{counts["info"]}</td>
          <td style="padding:8px 12px;text-align:right;font-weight:600;color:#17A2B8">{counts["info"] * 1}</td>
        </tr>
      </tbody>
      <tfoot><tr style="background:#F8F9FA;border-top:2px solid #DEE2E6">
        <td colspan="3" style="padding:8px 12px;font-weight:700;font-size:13px">Total</td>
        <td style="padding:8px 12px;text-align:right;font-weight:700;font-size:15px">{risk_score}</td>
      </tr></tfoot>
    </table>
    <p style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;
              color:#6C757D;margin-bottom:8px">Faixas de sa&#250;de do c&#243;digo</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tr style="border-bottom:1px solid #E9ECEF">
        <td style="padding:6px 10px"><span style="background:#D4EDDA;color:#155724;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">0 &ndash; 10</span></td>
        <td style="padding:6px 10px;color:#155724;font-weight:500">&#10003; Baixo Risco — c&#243;digo saud&#225;vel</td>
      </tr>
      <tr style="border-bottom:1px solid #E9ECEF">
        <td style="padding:6px 10px"><span style="background:#FFF3CD;color:#856404;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">11 &ndash; 30</span></td>
        <td style="padding:6px 10px;color:#856404;font-weight:500">&#9888; Risco Moderado — revisar antes do merge</td>
      </tr>
      <tr style="border-bottom:1px solid #E9ECEF">
        <td style="padding:6px 10px"><span style="background:#F8D7DA;color:#721C24;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">31 &ndash; 60</span></td>
        <td style="padding:6px 10px;color:#721C24;font-weight:500">&#128308; Alto Risco — corre&#231;&#245;es obrigat&#243;rias</td>
      </tr>
      <tr>
        <td style="padding:6px 10px"><span style="background:#DC3545;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">&gt; 60</span></td>
        <td style="padding:6px 10px;color:#DC3545;font-weight:500">&#128683; Risco Cr&#237;tico — bloqueia o deploy</td>
      </tr>
    </table>
    <p style="font-size:11px;color:#ADB5BD;margin-top:14px">
      F&#243;rmula: {formula_str} = <strong>{risk_score}</strong></p>
  </div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Code Guardian Report</title>
  <style>
    * {{ box-sizing:border-box;margin:0;padding:0 }}
    body {{ font-family:'Segoe UI',system-ui,sans-serif;background:#F5F5F5;
           color:#495057;padding:30px }}
    .container {{ max-width:1100px;margin:0 auto }}
    .card {{ background:#FFFFFF;border:1px solid #DEE2E6;border-radius:8px;
             padding:16px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.05) }}
    .page-title {{ font-size:24px;font-weight:600;color:#495057;margin-bottom:4px }}
    .subtitle {{ font-size:13px;color:#6C757D;margin-bottom:24px }}
    a {{ color:#184194 }} a:hover {{ color:#0F2D6B }}
  </style>
</head>
<body>
<div class="container">

  <h1 class="page-title">&#128737; Code Guardian Report</h1>
  <p class="subtitle">
    Gerado em {timestamp} &nbsp;&bull;&nbsp;
    {len(files)} arquivo(s) analisado(s) &nbsp;&bull;&nbsp;
    {elapsed_seconds:.1f}s
  </p>

  <!-- Risk Score + Resumo -->
  <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:stretch;margin-bottom:24px">

    <!-- Card Risk Score -->
    <div style="background:{score_bg};border:1px solid {score_border};border-radius:8px;
                padding:20px 24px;min-width:220px;position:relative">
      <div style="display:flex;align-items:flex-start;justify-content:space-between">
        <div>
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                      letter-spacing:.08em;color:{score_fg};opacity:.75;margin-bottom:6px">
            Risk Score
          </div>
          <div style="font-size:52px;font-weight:700;line-height:1;color:{score_fg}">{risk_score}</div>
          <div style="font-size:14px;font-weight:600;color:{score_fg};margin-top:6px">{score_label}</div>
        </div>
        <!-- Ícone de informação -->
        <button onclick="toggleRiskInfo()" title="Como &#233; calculado?"
          style="background:rgba(0,0,0,.1);border:none;border-radius:50%;width:28px;height:28px;
                 cursor:pointer;font-size:14px;color:{score_fg};font-weight:700;
                 display:flex;align-items:center;justify-content:center;flex-shrink:0;
                 margin-left:8px;opacity:.8">&#9432;</button>
      </div>
    </div>

    <!-- Tabela de severidades -->
    <div class="card" style="flex:1;min-width:200px;padding:0;overflow:hidden">
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="background:#F8F9FA;border-bottom:2px solid #DEE2E6">
          <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;
                     text-transform:uppercase;color:#6C757D;letter-spacing:.05em">Severidade</th>
          <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;
                     text-transform:uppercase;color:#6C757D;letter-spacing:.05em">Total</th>
        </tr></thead>
        <tbody>{summary_rows}</tbody>
      </table>
    </div>

  </div>

  <!-- Plano de Correção -->
  {correction_plan_html}

  <!-- Seções por arquivo -->
  {"".join(file_sections)}

  <footer style="text-align:center;color:#ADB5BD;font-size:12px;margin-top:32px;
                 padding-top:16px;border-top:1px solid #DEE2E6">
    Code Guardian &nbsp;&bull;&nbsp; rule_engine + metrics + AI &nbsp;&bull;&nbsp; {timestamp}
  </footer>

</div>

{modal_html}
<script>{modal_js}</script>
</body>
</html>"""


def run_review(
    files: list[str],
    severity: str = "info",
    rules_only: bool = False,
    output_format: str = "text",
    timeout: int = 60,
) -> dict:
    """
    Executa o review completo nos arquivos fornecidos.

    Imprime progresso em stderr durante a execução para não poluir stdout
    (importante para --format json e para hooks do git).

    Parâmetros:
        files:         Lista de caminhos de arquivos .cs a analisar.
        severity:      Severidade mínima a reportar.
        rules_only:    Se True, pula análise de IA.
        output_format: 'text' ou 'json'.
        timeout:       Timeout em segundos para cada subprocess (padrão: 60).

    Returns:
        dict com chaves: report, has_blockers, all_issues, issues_by_file,
                         metrics_by_file, ai_by_file, risk_score, risk_label, elapsed
    """
    issues_by_file:  dict[str, list[dict]] = {}
    metrics_by_file: dict[str, dict]       = {}
    ai_by_file:      dict[str, str]        = {}

    total = len(files)
    start = time.monotonic()

    for idx, file in enumerate(files, 1):
        # Progresso em stderr — visível no Visual Studio e terminais, não polui stdout
        print(
            f"[guardian] Analisando ({idx}/{total}): {Path(file).name}...",
            file=sys.stderr,
            flush=True,
        )

        # Rule Engine
        issues = _run_rule_engine(file, severity, timeout=timeout)
        issues_by_file[file] = issues

        # Métricas
        metrics = _run_metrics(file, timeout=timeout)
        if metrics:
            metrics_by_file[file] = metrics
            # Adicionar issues de métricas à lista geral para o Risk Score
            for mi in metrics.get("issues", []):
                issues_by_file[file].append({
                    "file":     file,
                    "line":     mi.get("line", 1),
                    "severity": mi.get("severity", "warning"),
                    "category": "Metrics",
                    "rule_id":  "METRICS",
                    "message":  mi.get("message", ""),
                    "source":   "metrics",
                })

        # IA (opcional — pulada no modo JSON para não atrasar pipelines CI)
        if not rules_only and output_format != "json":
            ai_result = _run_ai(file, timeout=timeout * 2)
            if ai_result:
                ai_by_file[file] = ai_result

    elapsed = time.monotonic() - start
    print(
        f"[guardian] Analise concluida em {elapsed:.1f}s",
        file=sys.stderr,
        flush=True,
    )

    all_issues = [i for issues in issues_by_file.values() for i in issues]
    risk_score, risk_label = _calculate_risk_score(all_issues)
    has_blockers = any(i.get("severity") in ("critical", "error") for i in all_issues)

    if output_format == "json":
        report = _format_json_report(files, issues_by_file, metrics_by_file, risk_score, risk_label)
    else:
        report = _format_text_report(
            files, issues_by_file, metrics_by_file, ai_by_file, risk_score, risk_label
        )

    return {
        "report":          report,
        "has_blockers":    has_blockers,
        "all_issues":      all_issues,
        "issues_by_file":  issues_by_file,
        "metrics_by_file": metrics_by_file,
        "ai_by_file":      ai_by_file,
        "risk_score":      risk_score,
        "risk_label":      risk_label,
        "elapsed":         elapsed,
        "files":           files,
    }


def _build_html_from_review(
    files: list[str],
    issues_by_file: dict[str, list[dict]],
    metrics_by_file: dict[str, dict],
    ai_by_file: dict[str, str],
    risk_score: int,
    risk_label: str,
    elapsed_seconds: float,
) -> str:
    """Wrapper para gerar HTML a partir dos dados já coletados em run_review."""
    return _format_html_report(
        files, issues_by_file, metrics_by_file, ai_by_file,
        risk_score, risk_label, elapsed_seconds,
    )


def _detect_base_branch() -> str:
    """Detecta o branch base do repositório (origin/master ou origin/main)."""
    try:
        result = subprocess.run(
            ["git", "branch", "-r"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        )
        remote_branches = result.stdout
        if "origin/master" in remote_branches:
            return "origin/master"
        if "origin/main" in remote_branches:
            return "origin/main"
    except Exception:
        pass
    return "origin/main"  # fallback


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Code Guardian — Review automatizado de código C#",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python runner.py                              # diff vs origin/master (ou origin/main)
  python runner.py --staged                     # apenas staged
  python runner.py --file Services/UserService.cs
  python runner.py --scan                       # varre diretório atual
  python runner.py --scan --dir C:/meu/projeto  # varre diretório específico
  python runner.py --scan --rules-only          # scan sem IA
  python runner.py --rules-only                 # sem IA
  python runner.py --format json                # saída JSON (CI/CD)
  python runner.py --severity error             # somente critical/error
  python runner.py --output relatorio.html      # salva relatório HTML
  python runner.py --timeout 90                 # timeout por subprocess
        """,
    )
    parser.add_argument("--file",  metavar="ARQUIVO",    help="Analisar arquivo específico")
    parser.add_argument("--scan",  action="store_true",  help="Varrer diretório recursivamente buscando .cs")
    parser.add_argument("--dir",   metavar="DIRETÓRIO",  default=".", help="Diretório raiz para --scan (padrão: diretório atual)")
    parser.add_argument("--staged", action="store_true", help="Analisar apenas arquivos staged")
    parser.add_argument("--base",  default=None, help="Branch base (padrão: detectado automaticamente: origin/master ou origin/main)")
    parser.add_argument("--rules-only", action="store_true", help="Apenas Rule Engine, sem IA")
    parser.add_argument(
        "--severity",
        choices=["critical", "error", "warning", "info"],
        default="info",
        help="Severidade mínima a reportar (padrão: info)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Formato de saída (padrão: text)",
    )
    parser.add_argument(
        "--fail-on",
        choices=["critical", "error", "warning"],
        default="error",
        help="Exit 1 se houver issues neste nível ou acima (padrão: error)",
    )
    parser.add_argument(
        "--output",
        metavar="ARQUIVO",
        help="Salvar relatório em arquivo (ex: relatorio.html, relatorio.txt)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        metavar="SEGUNDOS",
        help="Timeout por subprocess em segundos (padrão: 60; IA usa o dobro)",
    )
    parser.add_argument(
        "--summary-file",
        metavar="ARQUIVO",
        help="Gravar resumo de uma linha (trailer git) para uso pelo hook prepare-commit-msg",
    )

    args = parser.parse_args()

    # Resolver branch base: usar o informado ou detectar automaticamente
    if args.base is None:
        args.base = _detect_base_branch()

    # Determinar arquivos a analisar
    if args.file:
        files = [_resolve_file(args.file)]
    elif args.scan:
        files = _scan_directory(args.dir)
    else:
        files = _get_changed_files(staged=args.staged, base=args.base)

    if not files:
        if args.format == "json":
            print(json.dumps({"files_analyzed": [], "summary": {}, "has_blockers": False}))
        else:
            print("ℹ️  Nenhum arquivo .cs encontrado para analisar.")
        sys.exit(0)

    # Verificar se a saída solicitada é HTML
    output_is_html = args.output and args.output.lower().endswith(".html")

    # Executar review — run_review retorna dict com todos os dados coletados
    result = run_review(
        files=files,
        severity=args.severity,
        rules_only=args.rules_only,
        output_format=args.format,
        timeout=args.timeout,
    )
    report      = result["report"]
    has_blockers = result["has_blockers"]
    all_issues  = result["all_issues"]

    # Gerar HTML — sempre (exceto --format json) para ter relatório visual disponível
    def _write_html(dest: Path) -> None:
        html_content = _format_html_report(
            files=files,
            issues_by_file=result["issues_by_file"],
            metrics_by_file=result["metrics_by_file"],
            ai_by_file=result["ai_by_file"],
            risk_score=result["risk_score"],
            risk_label=result["risk_label"],
            elapsed_seconds=result["elapsed"],
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_content, encoding="utf-8")
        print(f"[guardian] Relatorio HTML: {dest.resolve()}", file=sys.stderr)

    if output_is_html:
        # --output especificado com .html — usa o caminho dado
        _write_html(Path(args.output))
    elif args.format != "json":
        # Geração automática em .guardian/last-runner-report.html
        _write_html(_find_guardian_dir() / "last-runner-report.html")

    # Escrever relatório texto/JSON — em arquivo ou stdout
    if args.output and not output_is_html:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"[guardian] Relatorio salvo em: {output_path.resolve()}", file=sys.stderr)
    else:
        print(report)

    # Determinar exit code para CI/CD — sem re-execução de scripts
    fail_severities = {"critical"}
    if args.fail_on in ("error", "warning"):
        fail_severities.add("error")
    if args.fail_on == "warning":
        fail_severities.add("warning")

    has_fail = any(i.get("severity") in fail_severities for i in all_issues)

    # Gravar resumo de uma linha para o hook prepare-commit-msg (trailer git).
    # Gravado apenas quando não há blockers — se houver, o hook já faz rm -f.
    if args.summary_file and not has_fail:
        counts = {s: 0 for s in ("critical", "error", "warning", "info")}
        for issue in all_issues:
            sev = issue.get("severity", "info")
            if sev in counts:
                counts[sev] += 1
        trailer = (
            f"Guardian-Review: ✅ Passou | "
            f"Score: {result['risk_score']} | "
            f"Critical: {counts['critical']} | "
            f"Error: {counts['error']} | "
            f"Warning: {counts['warning']} | "
            f"Arquivos: {len(result['files'])}"
        )
        summary_path = Path(args.summary_file)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(trailer + "\n", encoding="utf-8")

    if has_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
