#!/usr/bin/env python3
"""
VB6 Compare — Compara duas pastas VB6 e executa code review nos arquivos alterados.

Uso:
    python vb6_compare.py --base <pasta_base> --review <pasta_revisao>
    python vb6_compare.py --base C:/GPS/atual --review C:/GPS/pdp --output relatorio.html
    python vb6_compare.py --base C:/GPS/atual --review C:/GPS/pdp --format text
    python vb6_compare.py --base C:/GPS/atual --review C:/GPS/pdp --severity error

Exemplos:
    python vb6_compare.py \\
        --base ".folder.ignore/GPS022000/Código-Fonte" \\
        --review ".folder.ignore/GPS022000/Código-Fonte-PDP-63606"

    python vb6_compare.py \\
        --base ".folder.ignore/GPS022000/Código-Fonte" \\
        --review ".folder.ignore/GPS022000/Código-Fonte-PDP-63606" \\
        --output relatorio-gps022000.html
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import argparse
from pathlib import Path

# Garante que o diretório do script está no path para importar vb6_rule_engine
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))

from vb6_rule_engine import (
    compare_directories,
    generate_html,
    print_summary,
    _find_guardian_dir,
    _write_or_print,
)
from datetime import datetime


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compara duas pastas VB6 e executa code review nos arquivos alterados.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--base",     required=True, help="Pasta com o código atual (destino/baseline)")
    parser.add_argument("--review",   required=True, help="Pasta com o código revisado (branch/PDP)")
    parser.add_argument("--output",   default=None,  help="Caminho do relatório HTML de saída (opcional)")
    parser.add_argument("--format",   default="html", choices=["html", "text", "json"], help="Formato de saída (padrão: html)")
    parser.add_argument("--severity",  default="info", choices=["info", "warning", "error", "critical"], help="Severidade mínima a reportar (padrão: info)")
    parser.add_argument("--diff-only", action="store_true", help="Reportar apenas issues nas linhas efetivamente alteradas (usa difflib)")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    base_dir   = args.base
    review_dir = args.review
    output_fmt = args.format
    severity   = args.severity
    diff_only  = args.diff_only
    output_path: str | None = args.output

    diff_tag = " | Modo: apenas linhas alteradas" if diff_only else ""
    print(f"\n{'═' * 60}", file=sys.stderr)
    print(f"  VB6 Compare — Code Review de Diferenças", file=sys.stderr)
    print(f"{'═' * 60}", file=sys.stderr)
    print(f"  Base   : {base_dir}", file=sys.stderr)
    print(f"  Review : {review_dir}", file=sys.stderr)
    print(f"  Formato: {output_fmt} | Severidade mín.: {severity}{diff_tag}", file=sys.stderr)
    print(f"{'─' * 60}\n", file=sys.stderr, flush=True)

    compare_results = compare_directories(base_dir, review_dir, severity, output_fmt, diff_only)

    if not compare_results:
        print("\n✅ Nenhuma diferença encontrada entre as pastas.", file=sys.stderr)
        sys.exit(0)

    n_modified = sum(1 for _, _, ct in compare_results if ct == "modified")
    n_added    = sum(1 for _, _, ct in compare_results if ct == "added")
    plain_results = [(fp, res) for fp, res, _ in compare_results]
    ct_map = {fp: ct for fp, _, ct in compare_results}

    title = f"VB6 Code Review — Diff ({n_modified} modificado(s), {n_added} adicionado(s))"

    if output_fmt == "json":
        import json
        payload = {
            "title": title,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_files": len(compare_results),
                "modified": n_modified,
                "added": n_added,
            },
            "files": [
                {
                    "path": fp,
                    "change_type": ct_map.get(fp, "modified"),
                    "score": res.score.value,
                    "score_label": res.score.label,
                    "issues_count": len(res.issues),
                    "issues": [
                        {
                            "line": i.line,
                            "severity": i.severity,
                            "category": i.category,
                            "rule_id": i.rule_id,
                            "message": i.message,
                        }
                        for i in res.issues
                    ],
                }
                for fp, res, _ in compare_results
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if output_fmt == "html":
        html_content = generate_html(plain_results, title=title, change_types=ct_map)

        # Se não foi especificado --output, salva automaticamente em .guardian/
        if output_path is None:
            ts = datetime.now().strftime("%Y-%m-%d-%H%M")
            guardian = _find_guardian_dir()
            output_path = str(guardian / f"code-review-{ts} - VB6-Compare.html")

        _write_or_print(html_content, output_path)
    else:
        # Formato texto: compare_directories já imprimiu cada arquivo; só exibe resumo
        print_summary(plain_results)

    print(f"\n{'═' * 60}", file=sys.stderr)
    print(f"  Resumo: {n_modified} modificado(s) | {n_added} adicionado(s)", file=sys.stderr)
    if output_path:
        print(f"  Relatório: {output_path}", file=sys.stderr)
    print(f"{'═' * 60}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
