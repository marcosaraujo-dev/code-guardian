#!/usr/bin/env python3
"""
Rule Engine - Detecta padrões problemáticos em arquivos C#.
Execução rápida sem IA, baseada em regex e padrões de texto.

Uso:
    python rule_engine.py <arquivo.cs>
    python rule_engine.py <arquivo.cs> --format json
    python rule_engine.py <arquivo.cs> --format text
    python rule_engine.py <arquivo.cs> --severity error  # apenas error+critical
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json
import re
from dataclasses import dataclass, asdict

RULES = [
    # ── CRITICAL ──────────────────────────────────────────────────────────────
    {
        "id": "SQL_INJECTION_CONCAT",
        "pattern_regex": r'(?:"\s*(?:SELECT|INSERT|UPDATE|DELETE|WHERE)[^"]*"\s*\+|'
                         r'\$"\s*(?:SELECT|INSERT|UPDATE|DELETE)[^"]*\{)',
        "message": "Possível SQL Injection: query construída por concatenação/interpolação. Use queries parametrizadas.",
        "severity": "critical",
        "category": "SQL Injection"
    },
    {
        "id": "SQL_INJECTION_FROMSQLRAW",
        "pattern_regex": r'FromSqlRaw\s*\(\s*\$"',
        "message": "SQL Injection via EF Core FromSqlRaw com interpolação. Use FromSqlInterpolated ou parâmetros.",
        "severity": "critical",
        "category": "SQL Injection"
    },
    {
        "id": "HARDCODED_PASSWORD",
        "pattern_regex": r'(?:password|senha|pwd)\s*=\s*"[^"]{6,}"',
        "message": "Possível senha hardcoded. Use variáveis de ambiente ou Secret Manager.",
        "severity": "critical",
        "category": "Secrets Hardcoded"
    },
    {
        "id": "HARDCODED_API_KEY",
        "pattern_regex": r'(?:apiKey|api_key|apikey|token|secret)\s*=\s*"[A-Za-z0-9+/=_\-\.]{16,}"',
        "message": "Possível API key/token hardcoded. Use variáveis de ambiente ou Secret Manager.",
        "severity": "critical",
        "category": "Secrets Hardcoded"
    },
    {
        "id": "HARDCODED_CONNECTION_STRING",
        "pattern_regex": r'(?:connectionString|ConnectionString|Data Source)\s*=\s*"[^"]{20,}"',
        "message": "Possível connection string hardcoded. Use IConfiguration / variáveis de ambiente.",
        "severity": "critical",
        "category": "Secrets Hardcoded"
    },

    # ── ERROR ──────────────────────────────────────────────────────────────────
    {
        "id": "TASK_RESULT_DEADLOCK",
        "pattern_regex": r'(?<!\w)\.Result\b(?!\s*=)',
        "message": "Task.Result pode causar deadlock (captura SynchronizationContext em ASP.NET/WPF). Use await. "
                   "Exceção: em interfaces síncronas/COM (IProxy), use Task.Run(() => MetodoAsync()).GetAwaiter().GetResult() para evitar captura do contexto.",
        "severity": "error",
        "category": "Deadlock Async"
    },
    {
        "id": "TASK_WAIT_DEADLOCK",
        "pattern_regex": r'(?<!\w)\.Wait\(\)',
        "message": "Task.Wait() pode causar deadlock. Use await.",
        "severity": "error",
        "category": "Deadlock Async"
    },
    {
        "id": "ASYNC_VOID",
        "pattern_regex": r'\basync\s+void\s+(?!.*(?:EventHandler|_Click|_Load|_Changed|_Loaded))',
        "message": "async void perde exceções sem possibilidade de tratamento. Use async Task.",
        "severity": "error",
        "category": "Async Incorreto"
    },
    {
        "id": "EMPTY_CATCH",
        "pattern_regex": r'catch\s*(?:\(\s*\w+(?:\s+\w+)?\s*\))?\s*\{\s*\}',
        "message": "Catch vazio engole exceções silenciosamente. Sempre logar ou re-throw.",
        "severity": "error",
        "category": "Exception Handling"
    },
    {
        "id": "NOT_IMPLEMENTED_EXCEPTION",
        "pattern_regex": r'new\s+NotImplementedException',
        "message": "NotImplementedException encontrada. Nenhum método deve conter NotImplementedException em produção — "
                   "implemente a lógica, use uma abstração adequada ou remova o método. "
                   "Em Dispose(), implemente corretamente: libere recursos gerenciados e não-gerenciados.",
        "severity": "error",
        "category": "Implementação Incompleta"
    },
    {
        "id": "INFINITE_WHILE",
        "pattern": "while(true)",
        "message": "Loop while(true) detectado. Verificar se há condição de saída (break/return) acessível.",
        "severity": "error",
        "category": "Loop Infinito"
    },
    {
        "id": "THREAD_SLEEP",
        "pattern": "Thread.Sleep",
        "message": "Thread.Sleep bloqueia a thread. Em async, use await Task.Delay(ms).",
        "severity": "error",
        "category": "Performance"
    },

    # ── WARNING ────────────────────────────────────────────────────────────────
    {
        "id": "CONSOLE_WRITELINE",
        "pattern": "Console.WriteLine",
        "message": "Console.WriteLine em produção polui stdout. Use ILogger com nível apropriado.",
        "severity": "warning",
        "category": "Logging"
    },
    {
        "id": "CONSOLE_WRITE",
        "pattern": "Console.Write(",
        "message": "Console.Write em produção. Use ILogger.",
        "severity": "warning",
        "category": "Logging"
    },
    {
        "id": "MAGIC_NUMBER_COMPARISON",
        "pattern_regex": r'[=!<>]=?\s*\d{3,}(?!\s*(?:px|em|ms|MB|GB|KB|%|,|\)))',
        "message": "Possível magic number em comparação. Extrair para constante nomeada (ex: const int PRAZO_MAXIMO_DIAS = 365).",
        "severity": "warning",
        "category": "Magic Numbers"
    },
    {
        "id": "MAGIC_STRING_COMPARISON",
        "pattern_regex": r'(?:==|!=)\s*"(?:[A-Za-zÀ-ú][A-Za-zÀ-ú0-9 _\-]{2,30}|20[0-9]{2}|19[0-9]{2})"',
        "message": "String literal hardcoded em comparação. Extrair para constante ou enum "
                   "(ex: const string CATEGORIA_FINANCEIRO = \"Financeiro\"). "
                   "Strings em regras de negócio devem ter nome semântico para facilitar manutenção.",
        "severity": "warning",
        "category": "Magic Strings"
    },
    {
        "id": "GETAWAITER_GETRESULT",
        "pattern": ".GetAwaiter().GetResult()",
        "message": "GetAwaiter().GetResult() tem risco de deadlock igual ao .Result quando há SynchronizationContext. "
                   "Correto apenas como Task.Run(() => MetodoAsync()).GetAwaiter().GetResult() (padrão COM/IProxy). "
                   "Fora desse contexto, use await.",
        "severity": "warning",
        "category": "Deadlock Async"
    },
    {
        "id": "OBJECT_DISPOSABLE_NOUSE",
        "pattern_regex": r'new\s+(?:SqlConnection|SqlCommand|OleDbConnection|OracleConnection|NpgsqlConnection)\s*\(',
        "message": "Conexão de banco criada sem using. Pode causar connection leak. Use using var conn = new ...",
        "severity": "warning",
        "category": "IDisposable"
    },
    {
        "id": "HTTPCLIENT_NEW",
        "pattern_regex": r'new\s+HttpClient\s*\(',
        "message": "HttpClient criado com new causa socket exhaustion. Use IHttpClientFactory via DI.",
        "severity": "warning",
        "category": "IDisposable"
    },

    # ── INFO ───────────────────────────────────────────────────────────────────
    {
        "id": "PUBLIC_SETTER_ENTITY",
        "pattern_regex": r'public\s+\w[\w<>?,\[\] ]*\s+\w+\s*\{\s*get;\s*set;\s*\}',
        "message": "Setter público detectado. Verifique se este campo pertence a uma entidade de domínio — "
                   "entidades devem usar 'private set' ou 'init' para proteger invariantes. "
                   "Exponha comportamento por métodos (ex: Aprovar(), Cancelar()) em vez de setters. "
                   "Exceção legítima: DTOs, Requests, Responses, ViewModels e entidades de ORM.",
        "severity": "info",
        "category": "Domain Model"
    },
    {
        "id": "TODO_COMMENT",
        "pattern": "// TODO",
        "message": "TODO encontrado. Resolver antes de mergear ou criar issue no backlog.",
        "severity": "info",
        "category": "Code Quality",
        "skip_comment_filter": True
    },
    {
        "id": "FIXME_COMMENT",
        "pattern": "// FIXME",
        "message": "FIXME encontrado. Este ponto precisa ser corrigido antes do merge.",
        "severity": "info",
        "category": "Code Quality",
        "skip_comment_filter": True
    },
    {
        "id": "HACK_COMMENT",
        "pattern": "// HACK",
        "message": "HACK encontrado. Documentar contexto e criar issue para refatoração futura.",
        "severity": "info",
        "category": "Code Quality",
        "skip_comment_filter": True
    },
    {
        "id": "NO_RESULT_PATTERN",
        "pattern_regex": r'public\s+(?:async\s+)?Task<(?!Result<|IActionResult|ActionResult)',
        "message": "Método async retornando Task<T> sem Result<T>. Considere usar Result Pattern para erros de negócio.",
        "severity": "info",
        "category": "Padrões do Projeto"
    },
]


@dataclass
class Issue:
    file: str
    line: int
    severity: str
    category: str
    rule_id: str
    message: str
    source: str = "rule_engine"


def _is_comment_or_string(line: str, match_start: int) -> bool:
    """Verifica se o match está dentro de comentário ou string."""
    stripped = line.strip()
    # Linha inteira é comentário
    if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
        return True
    # Match está após // na mesma linha
    comment_idx = line.find("//")
    if comment_idx != -1 and comment_idx < match_start:
        return True
    return False


def analyze_file(file_path: str, min_severity: str = "info") -> list[Issue]:
    """Analisa um arquivo C# e retorna issues encontradas."""
    severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
    min_level = severity_order.get(min_severity, 3)

    issues: list[Issue] = []

    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return [Issue(
            file=file_path, line=0, severity="error",
            category="File", rule_id="FILE_NOT_FOUND",
            message=f"Arquivo não encontrado: {file_path}"
        )]
    except Exception as e:
        return [Issue(
            file=file_path, line=0, severity="error",
            category="File", rule_id="FILE_READ_ERROR",
            message=f"Erro ao ler arquivo: {e}"
        )]

    content = "".join(lines)

    for rule in RULES:
        if severity_order.get(rule["severity"], 3) > min_level:
            continue

        if "pattern_regex" in rule:
            try:
                for match in re.finditer(rule["pattern_regex"], content, re.IGNORECASE | re.MULTILINE):
                    line_num = content[:match.start()].count("\n") + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                    col_in_line = match.start() - content.rfind("\n", 0, match.start()) - 1

                    if _is_comment_or_string(line_content, col_in_line):
                        continue

                    # Evitar duplicatas na mesma linha para a mesma regra
                    if any(i.line == line_num and i.rule_id == rule["id"] for i in issues):
                        continue

                    issues.append(Issue(
                        file=file_path,
                        line=line_num,
                        severity=rule["severity"],
                        category=rule["category"],
                        rule_id=rule["id"],
                        message=rule["message"]
                    ))
            except re.error:
                pass  # regex inválida, pular regra

        elif "pattern" in rule:
            for i, line in enumerate(lines, 1):
                if not rule.get("skip_comment_filter") and _is_comment_or_string(line, line.find(rule["pattern"])):
                    continue
                if rule["pattern"] in line:
                    issues.append(Issue(
                        file=file_path,
                        line=i,
                        severity=rule["severity"],
                        category=rule["category"],
                        rule_id=rule["id"],
                        message=rule["message"]
                    ))

    return issues


def _severity_icon(severity: str) -> str:
    return {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")


def print_text(issues: list[Issue], file_path: str) -> None:
    if not issues:
        print(f"✅ {file_path}: Nenhum problema encontrado pelo Rule Engine.")
        return

    print(f"\n📁 {file_path}")
    for issue in sorted(issues, key=lambda i: i.line):
        icon = _severity_icon(issue.severity)
        print(f"  {icon} L{issue.line:3d} [{issue.category}] {issue.message}")


def print_summary(issues: list[Issue]) -> None:
    from collections import Counter
    counts = Counter(i.severity for i in issues)
    total = sum(counts.values())
    if total == 0:
        print("\n✅ Rule Engine: Nenhum problema encontrado.")
        return
    print(f"\nRule Engine: {total} issue(s) encontrada(s) — "
          f"🔴 {counts.get('critical', 0)} critical  "
          f"🟠 {counts.get('error', 0)} error  "
          f"🟡 {counts.get('warning', 0)} warning  "
          f"🔵 {counts.get('info', 0)} info")


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    file_path = args[0]
    output_format = "json"
    min_severity = "info"

    if "--format" in args:
        idx = args.index("--format")
        if idx + 1 < len(args):
            output_format = args[idx + 1]

    if "--severity" in args:
        idx = args.index("--severity")
        if idx + 1 < len(args):
            min_severity = args[idx + 1]

    issues = analyze_file(file_path, min_severity)

    if output_format == "json":
        print(json.dumps([asdict(i) for i in issues], ensure_ascii=False, indent=2))
    else:
        print_text(issues, file_path)
        print_summary(issues)

    has_blocker = any(i.severity in ("critical", "error") for i in issues)
    sys.exit(1 if has_blocker else 0)


if __name__ == "__main__":
    main()
