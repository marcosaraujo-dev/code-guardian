#!/usr/bin/env python3
"""
VB6 Rule Engine - Detecta padrões problemáticos em arquivos VB6 (.bas, .cls, .frm, .ctl).
Execução rápida sem IA, baseada em regex, análise de blocos e sistema de score (0-100).

Uso:
    python vb6_rule_engine.py <arquivo.bas|.cls|.frm>                    # padrão: texto no terminal + HTML salvo em .guardian/
    python vb6_rule_engine.py <arquivo> --format html --output rel.html  # HTML salvo em arquivo específico
    python vb6_rule_engine.py <arquivo> --format json                    # JSON para integração (sem HTML)
    python vb6_rule_engine.py <arquivo> --output relatorio.html          # HTML salvo em arquivo específico
    python vb6_rule_engine.py <arquivo> --severity warning
    python vb6_rule_engine.py --scan [--dir <caminho>]
    python vb6_rule_engine.py --scan --dir ./MeuProjeto
    python vb6_rule_engine.py --scan --dir ./MeuProjeto --format html --output relatorio.html

    # Modo comparação: analisa apenas arquivos modificados/adicionados entre duas pastas
    python vb6_rule_engine.py --compare --base C:/projetos/Sistema --review C:/temp/revisao
    python vb6_rule_engine.py --compare --base C:/projetos/Sistema --review C:/temp/revisao --output diff.html
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json
import re
import os
import time
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path


# ── Sistema de Log do Code Guardian ───────────────────────────────────────────
def _setup_guardian_logger() -> logging.Logger:
    """Configura logger com handler de arquivo em .guardian/logs/."""
    logger = logging.getLogger("code_guardian.vb6")
    if logger.handlers:
        return logger  # Já configurado

    logger.setLevel(logging.DEBUG)

    # Diretório de logs: .guardian/logs/ ao lado do script ou cwd
    script_dir = Path(__file__).parent
    candidate = script_dir.parent.parent / ".guardian" / "logs"
    if not candidate.exists():
        candidate = Path.cwd() / ".guardian" / "logs"
    candidate.mkdir(parents=True, exist_ok=True)

    log_file = candidate / f"vb6-{datetime.now().strftime('%Y-%m-%d')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    ))
    logger.addHandler(fh)
    return logger


_LOG = _setup_guardian_logger()


# ── Extensões VB6 suportadas ───────────────────────────────────────────────────
VB6_EXTENSIONS = (".bas", ".cls", ".frm", ".ctl")

# ── Mapeamento de penalidades por regra ────────────────────────────────────────
RULE_PENALTIES: dict[str, int] = {
    # Crítico
    "VB6_MISSING_OPTION_EXPLICIT":     15,
    "VB6_FORBIDDEN_DECLARATION":       15,
    "VB6_SQL_INJECTION_CONCAT":        20,
    # Erro
    "VB6_MISSING_ERROR_HANDLER":       15,
    "VB6_ON_ERROR_RESUME_NEXT_UNSAFE": 15,
    "VB6_INFINITE_LOOP":               15,
    "VB6_FUNCTION_TOO_LONG":           10,   # -10 ou -20 dependendo do tamanho
    "VB6_FUNCTION_TOO_LONG_CRITICAL":  20,
    "VB6_FORM_SQL_DIRECT":             15,
    "VB6_CLN_SQL_DIRECT":              15,
    # Warning
    "VB6_VARIANT_OVERUSE":             10,
    "VB6_MAGIC_NUMBER":                 5,
    "VB6_UBOUND_IN_LOOP":               5,
    "VB6_STRING_PLUS_CONCAT":           5,
    "VB6_EMPTY_STRING_CHECK":           5,
    "VB6_STRING_CONCAT_IN_LOOP":       10,
    "VB6_SQL_IN_LOOP":                 10,
    "VB6_OBJECT_NOT_RELEASED":         10,
    "VB6_GENERIC_VARIABLE_NAME":        5,
    # Info (sem penalidade)
    "VB6_TODO_COMMENT":                 0,
    "VB6_MISSING_ROTINA_NOME":          0,
}

# ── Labels de score ────────────────────────────────────────────────────────────
def _score_label(score: int) -> str:
    """Retorna o label textual correspondente ao score."""
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good — minor improvements"
    if score >= 60:
        return "Moderate technical debt"
    if score >= 40:
        return "High technical debt"
    return "Critical — do not approve"


# ── Dataclasses ────────────────────────────────────────────────────────────────
@dataclass
class Issue:
    file: str
    line: int
    severity: str
    category: str
    rule_id: str
    message: str
    source: str = "vb6_rule_engine"


@dataclass
class ScorePenalty:
    rule_id: str
    penalty: int
    count: int


@dataclass
class Score:
    value: int
    label: str
    penalties: list[ScorePenalty] = field(default_factory=list)


@dataclass
class AnalysisResult:
    issues: list[Issue]
    score: Score


# ── Detecção de comentário VB6 ─────────────────────────────────────────────────
def _is_vb6_comment(line: str, match_start: int) -> bool:
    """Verifica se o match está dentro de um comentário VB6 (após aspas simples)."""
    in_string = False
    for idx, ch in enumerate(line):
        if ch == '"':
            in_string = not in_string
        elif ch == "'" and not in_string:
            # comentário começa antes da posição do match
            return idx < match_start
    return False


# ── Extração de blocos Sub/Function ───────────────────────────────────────────
def _extract_methods(lines: list[str]) -> list[tuple[str, int, int]]:
    """
    Extrai blocos Sub/Function do arquivo.
    Retorna lista de (nome_método, linha_início, linha_fim) com base 1.
    """
    methods: list[tuple[str, int, int]] = []
    method_start: int | None = None
    method_name = ""

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Detectar início de Sub ou Function (com modificadores opcionais)
        if method_start is None:
            match = re.match(
                r'^\s*(?:Public\s+|Private\s+|Friend\s+)?'
                r'(?:Static\s+)?(?:Sub|Function)\s+(\w+)',
                stripped,
                re.IGNORECASE,
            )
            if match:
                method_name = match.group(1)
                method_start = i
        else:
            # Detectar fim de Sub ou Function
            if re.match(r'^\s*End\s+(?:Sub|Function)\s*$', stripped, re.IGNORECASE):
                methods.append((method_name, method_start, i))
                method_start = None
                method_name = ""

    return methods


# ── Detecção de contexto de loop ───────────────────────────────────────────────
def _build_loop_line_set(lines: list[str]) -> set[int]:
    """
    Retorna o conjunto de números de linha (base 1) que estão dentro de
    blocos For/Do/While.  Usado para detectar padrões problemáticos em loops.
    """
    loop_lines: set[int] = set()
    # Pilha de linhas de início dos loops abertos
    loop_stack: list[int] = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip().upper()

        # Entrar em loop
        is_for = re.match(r'^\s*For\s+\w+', line.strip(), re.IGNORECASE)
        is_do = re.match(r'^\s*Do\b', line.strip(), re.IGNORECASE)
        is_while = re.match(r'^\s*While\b', line.strip(), re.IGNORECASE)

        if is_for or is_do or is_while:
            loop_stack.append(i)

        # Sair de loop
        is_next = re.match(r'^\s*Next\b', line.strip(), re.IGNORECASE)
        is_loop = re.match(r'^\s*Loop\b', line.strip(), re.IGNORECASE)
        is_wend = re.match(r'^\s*Wend\b', line.strip(), re.IGNORECASE)

        if (is_next or is_loop or is_wend) and loop_stack:
            loop_stack.pop()

        # Marcar linha como dentro de loop se a pilha não estiver vazia
        if loop_stack:
            loop_lines.add(i)

    return loop_lines


# ── Cálculo de score ───────────────────────────────────────────────────────────
def _calculate_score(issues: list[Issue]) -> Score:
    """
    Calcula o score (0–100) com base nas penalidades das issues encontradas.
    Cada tipo de regra é penalizado apenas uma vez, independente do número de ocorrências.
    Exceção: VB6_FUNCTION_TOO_LONG e VB6_FUNCTION_TOO_LONG_CRITICAL são contados separadamente.
    """
    # Agrupar issues por rule_id para contar ocorrências
    rule_counts: dict[str, int] = {}
    for issue in issues:
        rule_counts[issue.rule_id] = rule_counts.get(issue.rule_id, 0) + 1

    penalties_applied: list[ScorePenalty] = []
    total_penalty = 0

    for rule_id, count in rule_counts.items():
        penalty = RULE_PENALTIES.get(rule_id, 0)
        if penalty > 0:
            penalties_applied.append(ScorePenalty(
                rule_id=rule_id,
                penalty=penalty,
                count=count,
            ))
            total_penalty += penalty

    score_value = max(0, 100 - total_penalty)
    return Score(
        value=score_value,
        label=_score_label(score_value),
        penalties=penalties_applied,
    )


# ── Análise principal ──────────────────────────────────────────────────────────
def analyze_file(file_path: str, min_severity: str = "info") -> AnalysisResult:
    """
    Analisa um arquivo VB6 e retorna issues e score.

    Parâmetros:
        file_path: caminho para o arquivo .bas/.cls/.frm/.ctl
        min_severity: nível mínimo de severidade a reportar ('info', 'warning', 'error', 'critical')
    """
    severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
    min_level = severity_order.get(min_severity, 3)

    # Determinar extensão do arquivo para regras específicas
    ext = os.path.splitext(file_path)[1].lower()
    basename = os.path.basename(file_path)

    issues: list[Issue] = []

    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        error_issue = Issue(
            file=file_path,
            line=0,
            severity="error",
            category="File",
            rule_id="FILE_NOT_FOUND",
            message=f"Arquivo não encontrado: {file_path}",
        )
        return AnalysisResult(issues=[error_issue], score=Score(value=0, label="Critical — do not approve"))
    except Exception as exc:
        error_issue = Issue(
            file=file_path,
            line=0,
            severity="error",
            category="File",
            rule_id="FILE_READ_ERROR",
            message=f"Erro ao ler arquivo: {exc}",
        )
        return AnalysisResult(issues=[error_issue], score=Score(value=0, label="Critical — do not approve"))

    content = "".join(lines)
    methods = _extract_methods(lines)
    loop_lines = _build_loop_line_set(lines)

    # Índice de posições de newline para converter match.start() → linha em O(log N).
    import bisect
    _newline_positions: list[int] = [-1]
    for _i, _ch in enumerate(content):
        if _ch == "\n":
            _newline_positions.append(_i)

    def _line_of(match_start: int) -> int:
        """Retorna o número de linha (1-based) para uma posição no content em O(log N)."""
        return bisect.bisect_right(_newline_positions, match_start)

    def add_issue(
        line: int,
        severity: str,
        category: str,
        rule_id: str,
        message: str,
    ) -> None:
        """Adiciona uma issue ao resultado se a severidade for suficiente."""
        if severity_order.get(severity, 3) <= min_level:
            issues.append(Issue(
                file=file_path,
                line=line,
                severity=severity,
                category=category,
                rule_id=rule_id,
                message=message,
            ))

    def already_reported(rule_id: str, line: int) -> bool:
        """Verifica se já existe issue para a mesma regra e linha (evita duplicatas)."""
        return any(i.rule_id == rule_id and i.line == line for i in issues)

    # ── CRITICAL: VB6_MISSING_OPTION_EXPLICIT ─────────────────────────────────
    # Verificação no nível do arquivo: ausência de 'Option Explicit'
    has_option_explicit = bool(re.search(
        r'^\s*Option\s+Explicit\s*$', content, re.IGNORECASE | re.MULTILINE
    ))
    if not has_option_explicit:
        add_issue(
            line=1,
            severity="critical",
            category="Declarações Obrigatórias",
            rule_id="VB6_MISSING_OPTION_EXPLICIT",
            message=(
                "Option Explicit ausente. Todo módulo VB6 deve ter "
                "'Option Explicit' como primeira declaração."
            ),
        )

    # ── CRITICAL: VB6_FORBIDDEN_DECLARATION ───────────────────────────────────
    forbidden_pattern = re.compile(
        r'^\s*(?:Option\s+Base|DefInt|DefStr|DefVar|On\s+Local\s+Error)\b',
        re.IGNORECASE | re.MULTILINE,
    )
    for match in forbidden_pattern.finditer(content):
        line_num = _line_of(match.start())
        if not already_reported("VB6_FORBIDDEN_DECLARATION", line_num):
            add_issue(
                line=line_num,
                severity="critical",
                category="Declarações Obrigatórias",
                rule_id="VB6_FORBIDDEN_DECLARATION",
                message=(
                    "Declaração proibida detectada. "
                    "Não usar Option Base, DefInt, DefStr, DefVar ou On Local Error."
                ),
            )

    # ── CRITICAL: VB6_SQL_INJECTION_CONCAT ────────────────────────────────────
    sql_inject_pattern = re.compile(
        r'(?:\.Execute|\.Open)\s*\(?\s*"[^"]*"\s*&',
        re.IGNORECASE,
    )
    for i, line in enumerate(lines, 1):
        match = sql_inject_pattern.search(line)
        if match and not _is_vb6_comment(line, match.start()):
            if not already_reported("VB6_SQL_INJECTION_CONCAT", i):
                add_issue(
                    line=i,
                    severity="critical",
                    category="SQL Injection",
                    rule_id="VB6_SQL_INJECTION_CONCAT",
                    message=(
                        "Possível SQL Injection: query construída por concatenação de strings. "
                        "Use queries parametrizadas via ADODB.Command e parâmetros."
                    ),
                )

    # ── ERROR: VB6_MISSING_ERROR_HANDLER ──────────────────────────────────────
    for method_name, start, end in methods:
        method_lines = lines[start - 1 : end]
        method_content = "".join(method_lines)
        has_on_error_goto = bool(re.search(
            r'On\s+Error\s+GoTo\s+\w+', method_content, re.IGNORECASE
        ))
        if not has_on_error_goto:
            add_issue(
                line=start,
                severity="error",
                category="Tratamento de Erro",
                rule_id="VB6_MISSING_ERROR_HANDLER",
                message=(
                    f"Sub/Function '{method_name}' sem tratamento de erro. "
                    "Todo método deve ter 'On Error GoTo ErrNomeMetodo'."
                ),
            )

    # ── ERROR: VB6_ON_ERROR_RESUME_NEXT_UNSAFE ────────────────────────────────
    resume_next_pattern = re.compile(r'On\s+Error\s+Resume\s+Next', re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        if resume_next_pattern.search(line) and not _is_vb6_comment(line, 0):
            # Verificar se a próxima linha não-em-branco contém 'If Err.Number'
            next_code_line = ""
            for j in range(i, min(i + 5, len(lines))):
                candidate = lines[j].strip() if j < len(lines) else ""
                if candidate and not candidate.startswith("'"):
                    next_code_line = candidate
                    break
            if not re.match(r'If\s+Err\.Number\b', next_code_line, re.IGNORECASE):
                if not already_reported("VB6_ON_ERROR_RESUME_NEXT_UNSAFE", i):
                    add_issue(
                        line=i,
                        severity="error",
                        category="Tratamento de Erro",
                        rule_id="VB6_ON_ERROR_RESUME_NEXT_UNSAFE",
                        message=(
                            "On Error Resume Next sem verificação imediata de Err.Number. "
                            "Após cada operação com Resume Next, verificar 'If Err.Number <> 0'."
                        ),
                    )

    # ── ERROR: VB6_INFINITE_LOOP ───────────────────────────────────────────────
    infinite_loop_pattern = re.compile(
        r'(?:Do\s+While\s+True\b|^\s*Do\s*$)',
        re.IGNORECASE | re.MULTILINE,
    )
    for match in infinite_loop_pattern.finditer(content):
        line_num = _line_of(match.start())
        line_content = lines[line_num - 1] if line_num <= len(lines) else ""
        col = match.start() - content.rfind("\n", 0, match.start()) - 1
        if not _is_vb6_comment(line_content, col):
            if not already_reported("VB6_INFINITE_LOOP", line_num):
                add_issue(
                    line=line_num,
                    severity="error",
                    category="Loop Infinito",
                    rule_id="VB6_INFINITE_LOOP",
                    message=(
                        "Possível loop infinito detectado. "
                        "Verificar se há 'Exit Do' acessível dentro do loop."
                    ),
                )

    # ── ERROR: VB6_FUNCTION_TOO_LONG ──────────────────────────────────────────
    for method_name, start, end in methods:
        line_count = end - start + 1
        if line_count > 300:
            add_issue(
                line=start,
                severity="error",
                category="Tamanho de Método",
                rule_id="VB6_FUNCTION_TOO_LONG_CRITICAL",
                message=(
                    f"Sub/Function '{method_name}' CRÍTICA com {line_count} linhas (>300). "
                    "Refatorar urgentemente."
                ),
            )
        elif line_count > 150:
            add_issue(
                line=start,
                severity="error",
                category="Tamanho de Método",
                rule_id="VB6_FUNCTION_TOO_LONG",
                message=(
                    f"Sub/Function '{method_name}' com {line_count} linhas (>150). "
                    "Extrair em métodos menores com responsabilidade única."
                ),
            )

    # ── ERROR: VB6_FORM_SQL_DIRECT (apenas .frm) ──────────────────────────────
    if ext == ".frm":
        form_sql_pattern = re.compile(
            r'(?:\.Execute\s*\(|\.Open\s*\()',
            re.IGNORECASE,
        )
        for i, line in enumerate(lines, 1):
            match = form_sql_pattern.search(line)
            if match and not _is_vb6_comment(line, match.start()):
                if not already_reported("VB6_FORM_SQL_DIRECT", i):
                    add_issue(
                        line=i,
                        severity="error",
                        category="Arquitetura",
                        rule_id="VB6_FORM_SQL_DIRECT",
                        message=(
                            "Form executando SQL diretamente. "
                            "Forms devem delegar para classes de negócio (clsN) ou dados (clsD)."
                        ),
                    )

    # ── ERROR: VB6_CLN_SQL_DIRECT (apenas .cls com prefixo clsN) ──────────────
    if ext == ".cls" and basename.lower().startswith("clsn"):
        cln_sql_pattern = re.compile(
            r'(?:\.Execute\s*\(|p_rs\w+\.Open\s*\()',
            re.IGNORECASE,
        )
        for i, line in enumerate(lines, 1):
            match = cln_sql_pattern.search(line)
            if match and not _is_vb6_comment(line, match.start()):
                if not already_reported("VB6_CLN_SQL_DIRECT", i):
                    add_issue(
                        line=i,
                        severity="error",
                        category="Arquitetura",
                        rule_id="VB6_CLN_SQL_DIRECT",
                        message=(
                            "Classe de negócio (clsN) executando SQL diretamente. "
                            "Delegar para classe de dados (clsD)."
                        ),
                    )

    # ── WARNING: VB6_VARIANT_OVERUSE ──────────────────────────────────────────
    variant_pattern = re.compile(r'\bAs\s+Variant\b', re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        match = variant_pattern.search(line)
        if match and not _is_vb6_comment(line, match.start()):
            if not already_reported("VB6_VARIANT_OVERUSE", i):
                add_issue(
                    line=i,
                    severity="warning",
                    category="Tipagem",
                    rule_id="VB6_VARIANT_OVERUSE",
                    message=(
                        "Uso de Variant detectado. "
                        "Prefira tipos específicos (String, Long, Integer, Boolean, Date) "
                        "para melhor performance e detecção de erros em compilação."
                    ),
                )

    # ── WARNING: VB6_MAGIC_NUMBER ─────────────────────────────────────────────
    magic_number_pattern = re.compile(
        r'(?:=|<|>|<=|>=|<>)\s*\d{2,}',
        re.IGNORECASE,
    )
    for i, line in enumerate(lines, 1):
        # Ignorar linhas que são só declarações de constantes
        stripped = line.strip()
        if re.match(r'^\s*Const\s+', stripped, re.IGNORECASE):
            continue
        match = magic_number_pattern.search(line)
        if match and not _is_vb6_comment(line, match.start()):
            if not already_reported("VB6_MAGIC_NUMBER", i):
                add_issue(
                    line=i,
                    severity="warning",
                    category="Magic Numbers",
                    rule_id="VB6_MAGIC_NUMBER",
                    message=(
                        "Magic number detectado. "
                        "Extrair para constante nomeada: "
                        "'Const NOME_CONSTANTE As Long = valor'."
                    ),
                )

    # ── WARNING: VB6_UBOUND_IN_LOOP ───────────────────────────────────────────
    ubound_in_for_pattern = re.compile(
        r'For\s+\w+\s*=\s*\w+\s+To\s+UBound\s*\(',
        re.IGNORECASE,
    )
    for i, line in enumerate(lines, 1):
        match = ubound_in_for_pattern.search(line)
        if match and not _is_vb6_comment(line, match.start()):
            if not already_reported("VB6_UBOUND_IN_LOOP", i):
                add_issue(
                    line=i,
                    severity="warning",
                    category="Performance",
                    rule_id="VB6_UBOUND_IN_LOOP",
                    message=(
                        "UBound() chamado diretamente no For...Next. "
                        "Cachear em variável antes do loop para melhor performance."
                    ),
                )

    # ── WARNING: VB6_STRING_PLUS_CONCAT ───────────────────────────────────────
    # Detecta concatenação de strings usando '+' em variáveis com prefixo 's'
    string_plus_pattern = re.compile(
        r'\bs\w+\s*=\s*.*\+',
        re.IGNORECASE,
    )
    for i, line in enumerate(lines, 1):
        match = string_plus_pattern.search(line)
        if match and not _is_vb6_comment(line, match.start()):
            if not already_reported("VB6_STRING_PLUS_CONCAT", i):
                add_issue(
                    line=i,
                    severity="warning",
                    category="Performance",
                    rule_id="VB6_STRING_PLUS_CONCAT",
                    message=(
                        "Concatenação de strings com '+'. "
                        "Usar '&' para evitar erros silenciosos com valores Null."
                    ),
                )

    # ── WARNING: VB6_EMPTY_STRING_CHECK ───────────────────────────────────────
    empty_string_pattern = re.compile(
        r'\bIf\s+\w+\s*=\s*""\s*Then\b',
        re.IGNORECASE,
    )
    for i, line in enumerate(lines, 1):
        match = empty_string_pattern.search(line)
        if match and not _is_vb6_comment(line, match.start()):
            if not already_reported("VB6_EMPTY_STRING_CHECK", i):
                add_issue(
                    line=i,
                    severity="warning",
                    category="Performance",
                    rule_id="VB6_EMPTY_STRING_CHECK",
                    message=(
                        'Comparação com string vazia usando \'= ""\'. '
                        "Preferir 'If Len(variavel) = 0 Then' por ser mais rápido."
                    ),
                )

    # ── WARNING: VB6_STRING_CONCAT_IN_LOOP ────────────────────────────────────
    # Detecta padrão 'var = var &' dentro de linhas em contexto de loop
    string_concat_loop_pattern = re.compile(
        r'\w+\s*=\s*\w+\s*&',
        re.IGNORECASE,
    )
    for i, line in enumerate(lines, 1):
        if i not in loop_lines:
            continue
        match = string_concat_loop_pattern.search(line)
        if match and not _is_vb6_comment(line, match.start()):
            if not already_reported("VB6_STRING_CONCAT_IN_LOOP", i):
                add_issue(
                    line=i,
                    severity="warning",
                    category="Performance",
                    rule_id="VB6_STRING_CONCAT_IN_LOOP",
                    message=(
                        "Concatenação de strings dentro de loop. "
                        "Usar array com ReDim e Join() no final para melhor performance."
                    ),
                )

    # ── WARNING: VB6_SQL_IN_LOOP ──────────────────────────────────────────────
    sql_in_loop_pattern = re.compile(
        r'(?:\.Execute\s*\(|\.Open\s*\()',
        re.IGNORECASE,
    )
    for i, line in enumerate(lines, 1):
        if i not in loop_lines:
            continue
        match = sql_in_loop_pattern.search(line)
        if match and not _is_vb6_comment(line, match.start()):
            if not already_reported("VB6_SQL_IN_LOOP", i):
                add_issue(
                    line=i,
                    severity="warning",
                    category="Performance",
                    rule_id="VB6_SQL_IN_LOOP",
                    message=(
                        "Query SQL executada dentro de loop. "
                        "Unificar em query única com cláusula IN ou JOIN."
                    ),
                )

    # ── WARNING: VB6_OBJECT_NOT_RELEASED ──────────────────────────────────────
    # Detecta objetos com prefixo p_ criados com 'New' sem correspondente Nothing.
    # Pré-calcula o conjunto de variáveis liberadas (O(N)) para evitar regex-por-objeto (O(N²)).
    nothing_vars: set[str] = {
        m.group(1).lower()
        for m in re.finditer(r'Set\s+(p_\w+)\s*=\s*Nothing', content, re.IGNORECASE)
    }
    object_new_pattern = re.compile(
        r'Set\s+(p_\w+)\s*=\s*New\s+\w+',
        re.IGNORECASE,
    )
    for match in object_new_pattern.finditer(content):
        var_name = match.group(1)
        line_num = _line_of(match.start())
        line_content = lines[line_num - 1] if line_num <= len(lines) else ""
        col = match.start() - content.rfind("\n", 0, match.start()) - 1

        if _is_vb6_comment(line_content, col):
            continue

        if var_name.lower() not in nothing_vars:
            if not already_reported("VB6_OBJECT_NOT_RELEASED", line_num):
                add_issue(
                    line=line_num,
                    severity="warning",
                    category="Gerenciamento de Memória",
                    rule_id="VB6_OBJECT_NOT_RELEASED",
                    message=(
                        f"Objeto '{var_name}' criado mas possivelmente não liberado. "
                        "Usar 'Set obj = Nothing' no bloco ExitNomeMetodo."
                    ),
                )

    # ── WARNING: VB6_GENERIC_VARIABLE_NAME ────────────────────────────────────
    generic_name_pattern = re.compile(
        r'\bDim\s+(?:tmp|temp|var|data|valor|resultado|retorno)\s+As\b',
        re.IGNORECASE,
    )
    for i, line in enumerate(lines, 1):
        match = generic_name_pattern.search(line)
        if match and not _is_vb6_comment(line, match.start()):
            if not already_reported("VB6_GENERIC_VARIABLE_NAME", i):
                add_issue(
                    line=i,
                    severity="warning",
                    category="Nomenclatura",
                    rule_id="VB6_GENERIC_VARIABLE_NAME",
                    message=(
                        "Nome de variável genérico detectado. "
                        "Usar prefixo de escopo+tipo (ex: p_sNomeCliente, v_lCodigo)."
                    ),
                )

    # ── INFO: VB6_TODO_COMMENT ────────────────────────────────────────────────
    todo_pattern = re.compile(r"'\s*TODO\b", re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        if todo_pattern.search(line):
            if not already_reported("VB6_TODO_COMMENT", i):
                add_issue(
                    line=i,
                    severity="info",
                    category="Code Quality",
                    rule_id="VB6_TODO_COMMENT",
                    message="TODO encontrado. Resolver antes de mergear ou criar issue no backlog.",
                )

    # ── INFO: VB6_MISSING_ROTINA_NOME ─────────────────────────────────────────
    # Métodos que têm 'On Error GoTo' mas não declaram 'Const sROTINA_NOME'
    for method_name, start, end in methods:
        method_content = "".join(lines[start - 1 : end])
        has_on_error = bool(re.search(
            r'On\s+Error\s+GoTo\s+\w+', method_content, re.IGNORECASE
        ))
        has_rotina_nome = bool(re.search(
            r'Const\s+sROTINA_NOME\b', method_content, re.IGNORECASE
        ))
        if has_on_error and not has_rotina_nome:
            if not already_reported("VB6_MISSING_ROTINA_NOME", start):
                add_issue(
                    line=start,
                    severity="info",
                    category="Tratamento de Erro",
                    rule_id="VB6_MISSING_ROTINA_NOME",
                    message=(
                        f"Constante sROTINA_NOME ausente em '{method_name}'. "
                        "Todo método com tratamento de erro deve declarar "
                        "'Const sROTINA_NOME As String = \"NomeMetodo\"'."
                    ),
                )

    score = _calculate_score(issues)
    return AnalysisResult(issues=issues, score=score)


# ── Utilitários de saída ───────────────────────────────────────────────────────
def _severity_icon(severity: str) -> str:
    """Retorna o ícone Unicode correspondente à severidade."""
    return {
        "critical": "🔴",
        "error": "🟠",
        "warning": "🟡",
        "info": "🔵",
    }.get(severity, "⚪")


def print_text(result: AnalysisResult, file_path: str) -> None:
    """Imprime o resultado em formato legível para humanos."""
    if not result.issues:
        print(f"✅ {file_path}: Nenhum problema encontrado pelo VB6 Rule Engine.")
        print(f"   Score: {result.score.value} / 100 — {result.score.label}")
        return

    print(f"\n📁 {file_path}")
    for issue in sorted(result.issues, key=lambda i: i.line):
        icon = _severity_icon(issue.severity)
        print(f"  {icon} L{issue.line:3d} [{issue.category}] {issue.message}")

    print(f"\n  Score: {result.score.value} / 100 — {result.score.label}")


def print_summary(all_results: list[tuple[str, AnalysisResult]]) -> None:
    """Imprime o resumo global de um scan de múltiplos arquivos."""
    from collections import Counter

    total_issues: list[Issue] = []
    for _, result in all_results:
        total_issues.extend(result.issues)

    counts = Counter(i.severity for i in total_issues)
    total = sum(counts.values())
    scores = [r.score.value for _, r in all_results]
    avg_score = int(sum(scores) / len(scores)) if scores else 100

    print(f"\n{'─' * 60}")
    print(f"VB6 Rule Engine — {len(all_results)} arquivo(s) analisado(s)")
    print(
        f"Total: {total} issue(s) — "
        f"🔴 {counts.get('critical', 0)} critical  "
        f"🟠 {counts.get('error', 0)} error  "
        f"🟡 {counts.get('warning', 0)} warning  "
        f"🔵 {counts.get('info', 0)} info"
    )
    print(f"Score médio: {avg_score} / 100 — {_score_label(avg_score)}")


# ── Geração HTML ──────────────────────────────────────────────────────────────
def _score_color(score: int) -> tuple[str, str]:
    """Retorna (background, border) para o card de score."""
    if score >= 90:
        return "#28A745", "#1E7E34"
    if score >= 75:
        return "#184194", "#0F2D6B"
    if score >= 60:
        return "#FD7E14", "#E06500"
    if score >= 40:
        return "#DC3545", "#C82333"
    return "#6F1F2A", "#561720"


def _sev_badge(severity: str) -> str:
    """Retorna HTML de badge colorido para a severidade."""
    styles = {
        "critical": ("background:#F8D7DA;color:#721C24", "Critical"),
        "error":    ("background:#FFE5D0;color:#7D3A0F", "Error"),
        "warning":  ("background:#FFF3CD;color:#856404", "Warning"),
        "info":     ("background:#D1ECF1;color:#0C5460", "Info"),
    }
    style, label = styles.get(severity, ("background:#E9ECEF;color:#495057", severity.title()))
    return (
        f'<span style="display:inline-block;padding:3px 8px;border-radius:10px;'
        f'font-size:11px;font-weight:600;{style}">{label}</span>'
    )


def _row_bg(severity: str) -> str:
    return "#FFF5F5" if severity in ("critical", "error") else "#FFFFFF"


def generate_html(
    all_results: list[tuple[str, AnalysisResult]],
    title: str = "VB6 Code Review",
    change_types: dict[str, str] | None = None,
) -> str:
    """
    Gera relatório HTML completo no mesmo estilo visual do runner.py.

    Parâmetros:
        all_results:  lista de (caminho_arquivo, AnalysisResult)
        title:        título exibido no cabeçalho do relatório
        change_types: dict opcional mapeando caminho_arquivo → "modified"|"added"
                      Quando fornecido, exibe badge de mudança na tabela de arquivos.
    """
    from collections import Counter
    from datetime import datetime

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    n_files = len(all_results)

    # Agregar todas as issues
    all_issues: list[tuple[str, Issue]] = []
    for fp, res in all_results:
        for iss in res.issues:
            all_issues.append((fp, iss))

    counts = Counter(i.severity for _, i in all_issues)
    scores = [res.score.value for _, res in all_results]
    avg_score = int(sum(scores) / len(scores)) if scores else 100
    avg_label = _score_label(avg_score)
    score_bg, score_border = _score_color(avg_score)

    # ── Tabela de issues ──────────────────────────────────────────────────────
    rows_html = ""
    order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
    sorted_issues = sorted(all_issues, key=lambda x: (order.get(x[1].severity, 9), x[0], x[1].line))

    for idx, (fp, iss) in enumerate(sorted_issues, 1):
        bg = _row_bg(iss.severity)
        badge = _sev_badge(iss.severity)
        file_ref = f"{os.path.basename(fp)}:{iss.line}"
        msg = iss.message.replace("<", "&lt;").replace(">", "&gt;")
        rows_html += (
            f'<tr style="border-bottom:1px solid #E9ECEF;background:{bg}">'
            f'<td style="padding:8px 12px;font-size:12px;color:#6C757D;text-align:center">{idx}</td>'
            f'<td style="padding:8px 12px;font-family:Consolas,monospace;font-size:12px">{file_ref}</td>'
            f'<td style="padding:8px 12px">{badge}</td>'
            f'<td style="padding:8px 12px;font-size:12px;font-weight:600;color:#495057">{iss.category}</td>'
            f'<td style="padding:8px 12px;font-size:12px;color:#495057">{msg}</td>'
            f'</tr>\n'
        )

    # ── Tabela de scores por arquivo ──────────────────────────────────────────
    show_change_col = change_types is not None
    file_scores_html = ""
    for fp, res in sorted(all_results, key=lambda x: x[1].score.value):
        bg_s, _ = _score_color(res.score.value)
        n_critical = sum(1 for i in res.issues if i.severity == "critical")
        n_error    = sum(1 for i in res.issues if i.severity == "error")
        n_warning  = sum(1 for i in res.issues if i.severity == "warning")
        blocker_style = "color:#DC3545;font-weight:700" if n_critical + n_error > 0 else "color:#495057"

        change_cell = ""
        if show_change_col:
            ct = (change_types or {}).get(fp, "")
            if ct == "modified":
                change_cell = '<td style="padding:8px 12px"><span style="background:#FFF3CD;color:#856404;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;border:1px solid #FFEEBA">✏️ MODIFICADO</span></td>'
            elif ct == "added":
                change_cell = '<td style="padding:8px 12px"><span style="background:#D4EDDA;color:#155724;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;border:1px solid #C3E6CB">🆕 NOVO</span></td>'
            else:
                change_cell = '<td style="padding:8px 12px"></td>'

        file_scores_html += (
            f'<tr style="border-bottom:1px solid #E9ECEF">'
            f'{change_cell}'
            f'<td style="padding:8px 12px;font-family:Consolas,monospace;font-size:12px">{os.path.basename(fp)}</td>'
            f'<td style="padding:8px 12px;text-align:center">'
            f'<span style="display:inline-block;padding:4px 12px;border-radius:12px;'
            f'background:{bg_s};color:#FFFFFF;font-weight:700;font-size:13px">'
            f'{res.score.value}</span></td>'
            f'<td style="padding:8px 12px;font-size:12px;color:#6C757D">{res.score.label}</td>'
            f'<td style="padding:8px 12px;font-size:12px;{blocker_style}">'
            f'🔴 {n_critical} &nbsp; 🟠 {n_error} &nbsp; 🟡 {n_warning}</td>'
            f'</tr>\n'
        )

    # ── Penalidades do score médio (agregadas) ────────────────────────────────
    all_penalties: Counter = Counter()
    for _, res in all_results:
        for p in res.score.penalties:
            all_penalties[p.rule_id] += p.penalty

    penalty_rows = ""
    for rule_id, total_pen in sorted(all_penalties.items(), key=lambda x: -x[1]):
        penalty_rows += (
            f'<tr style="border-bottom:1px solid #E9ECEF">'
            f'<td style="padding:6px 12px;font-family:Consolas,monospace;font-size:12px">{rule_id}</td>'
            f'<td style="padding:6px 12px;font-size:12px;color:#DC3545;font-weight:600">−{total_pen}</td>'
            f'</tr>\n'
        )

    blockers = sum(1 for _, i in all_issues if i.severity in ("critical", "error"))
    improvements = sum(1 for _, i in all_issues if i.severity in ("warning", "info"))

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>VB6 Code Review</title>
  <style>
    * {{ box-sizing:border-box;margin:0;padding:0 }}
    body {{ font-family:'Segoe UI',system-ui,sans-serif;background:#F5F5F5;color:#495057;padding:30px }}
    .container {{ max-width:1100px;margin:0 auto }}
    .card {{ background:#FFFFFF;border:1px solid #DEE2E6;border-radius:8px;padding:16px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.05) }}
    .page-title {{ font-size:24px;font-weight:600;color:#495057;margin-bottom:4px }}
    .subtitle {{ font-size:13px;color:#6C757D;margin-bottom:24px }}
    a {{ color:#184194 }} a:hover {{ color:#0F2D6B }}
    table {{ width:100%;border-collapse:collapse }}
    th {{ padding:10px 12px;text-align:left;font-size:11px;font-weight:600;text-transform:uppercase;
          color:#6C757D;letter-spacing:.05em;background:#F8F9FA;border-bottom:2px solid #DEE2E6 }}
  </style>
</head>
<body>
<div class="container">

  <h1 class="page-title">&#128270; {title}</h1>
  <p class="subtitle">
    Gerado em {now} &nbsp;&bull;&nbsp;
    {n_files} arquivo(s) analisado(s) &nbsp;&bull;&nbsp;
    {len(all_issues)} issue(s) encontrada(s)
  </p>

  <!-- Score + Resumo -->
  <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:stretch;margin-bottom:24px">

    <!-- Card Score -->
    <div style="background:{score_bg};border:1px solid {score_border};border-radius:8px;
                padding:20px 24px;min-width:220px">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                  letter-spacing:.08em;color:#FFFFFF;opacity:.75;margin-bottom:6px">Score Médio</div>
      <div style="font-size:52px;font-weight:700;line-height:1;color:#FFFFFF">{avg_score}</div>
      <div style="font-size:14px;font-weight:600;color:#FFFFFF;margin-top:6px">{avg_label}</div>
    </div>

    <!-- Tabela de severidades -->
    <div class="card" style="flex:1;min-width:200px;padding:0;overflow:hidden">
      <table>
        <thead><tr>
          <th>Severidade</th><th>Total</th>
        </tr></thead>
        <tbody>
          <tr style="border-bottom:1px solid #E9ECEF">
            <td style="padding:8px 16px"><span style="display:inline-block;width:9px;height:9px;
              border-radius:50%;background:#DC3545;margin-right:6px;vertical-align:middle"></span>
              <span style="font-size:13px">Critical</span></td>
            <td style="padding:8px 16px;font-weight:700;color:#DC3545;font-size:16px">{counts.get("critical", 0)}</td>
          </tr>
          <tr style="border-bottom:1px solid #E9ECEF">
            <td style="padding:8px 16px"><span style="display:inline-block;width:9px;height:9px;
              border-radius:50%;background:#FD7E14;margin-right:6px;vertical-align:middle"></span>
              <span style="font-size:13px">Error</span></td>
            <td style="padding:8px 16px;font-weight:700;color:#FD7E14;font-size:16px">{counts.get("error", 0)}</td>
          </tr>
          <tr style="border-bottom:1px solid #E9ECEF">
            <td style="padding:8px 16px"><span style="display:inline-block;width:9px;height:9px;
              border-radius:50%;background:#FFC107;margin-right:6px;vertical-align:middle"></span>
              <span style="font-size:13px">Warning</span></td>
            <td style="padding:8px 16px;font-weight:700;color:#856404;font-size:16px">{counts.get("warning", 0)}</td>
          </tr>
          <tr>
            <td style="padding:8px 16px"><span style="display:inline-block;width:9px;height:9px;
              border-radius:50%;background:#17A2B8;margin-right:6px;vertical-align:middle"></span>
              <span style="font-size:13px">Info</span></td>
            <td style="padding:8px 16px;font-weight:700;color:#17A2B8;font-size:16px">{counts.get("info", 0)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Score por arquivo -->
  <div style="margin-bottom:24px;border:1px solid #DEE2E6;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)">
    <div style="background:#184194;color:#FFFFFF;padding:10px 16px;font-size:14px;font-weight:600">
      &#128196; Score por Arquivo
    </div>
    <div style="background:#FFFFFF">
      <table>
        <thead><tr>
          {'<th>Mudança</th>' if show_change_col else ''}<th>Arquivo</th><th style="text-align:center">Score</th><th>Qualidade</th><th>Issues</th>
        </tr></thead>
        <tbody>
{file_scores_html}        </tbody>
      </table>
    </div>
  </div>

  <!-- Issues -->
  <div style="margin-bottom:24px;border:1px solid #DEE2E6;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)">
    <div style="background:#184194;color:#FFFFFF;padding:10px 16px;font-size:14px;font-weight:600">
      &#128203; Issues Encontradas
    </div>
    <div style="background:#FFFFFF;padding:16px">
      <p style="margin:0 0 12px;font-size:13px;color:#6C757D">
        {len(all_issues)} issue(s) &bull; {blockers} bloqueiam aprovação &bull; {improvements} melhorias recomendadas
      </p>
      <table>
        <thead><tr>
          <th style="width:36px">#</th>
          <th>Arquivo</th>
          <th>Severidade</th>
          <th>Categoria</th>
          <th>Mensagem</th>
        </tr></thead>
        <tbody>
{rows_html}        </tbody>
      </table>
      <p style="margin:12px 0 0;font-size:12px;color:#6C757D;font-style:italic">
        Após corrigir, revalide:
        <code style="background:#F8F9FA;padding:2px 6px;border-radius:3px;font-size:11px">
          python code_guardian/vb6_rule_engine.py &lt;arquivo&gt; --format text
        </code>
      </p>
    </div>
  </div>

  <!-- Penalidades aplicadas -->
  <div style="margin-bottom:24px;border:1px solid #DEE2E6;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)">
    <div style="background:#495057;color:#FFFFFF;padding:10px 16px;font-size:14px;font-weight:600">
      &#128200; Penalidades Aplicadas no Score
    </div>
    <div style="background:#FFFFFF">
      <table>
        <thead><tr><th>Regra</th><th>Penalidade Total</th></tr></thead>
        <tbody>
{penalty_rows}          <tr style="background:#F8F9FA;border-top:2px solid #DEE2E6">
            <td style="padding:8px 12px;font-weight:700;font-size:13px">Score Final (média)</td>
            <td style="padding:8px 12px;font-weight:700;font-size:16px;color:{score_bg}">{avg_score} / 100</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

</div>
</body>
</html>"""
    return html


# ── Scan de diretório ──────────────────────────────────────────────────────────
def scan_directory(
    directory: str,
    min_severity: str = "info",
    output_format: str = "text",
) -> list[tuple[str, AnalysisResult]]:
    """
    Varre recursivamente um diretório em busca de arquivos VB6 e analisa cada um.

    Retorna lista de (caminho_arquivo, AnalysisResult).
    """
    t_start = time.time()
    _LOG.info("scan_directory iniciado | dir=%s", directory)
    print(f"⏳ Coletando arquivos VB6 em: {directory}", file=sys.stderr, flush=True)

    # Coletar lista completa antes de analisar (para mostrar progresso)
    all_files: list[str] = []
    for root, _dirs, files in os.walk(directory):
        for filename in sorted(files):
            if os.path.splitext(filename)[1].lower() in VB6_EXTENSIONS:
                all_files.append(os.path.join(root, filename))

    total = len(all_files)
    _LOG.info("scan_directory | %d arquivo(s) encontrado(s)", total)
    print(f"🔍 {total} arquivo(s) VB6 encontrado(s) para analisar", file=sys.stderr, flush=True)

    results: list[tuple[str, AnalysisResult]] = []

    import threading

    for idx, file_path in enumerate(all_files, start=1):
        filename = os.path.basename(file_path)
        file_size_kb = os.path.getsize(file_path) // 1024
        size_tag = f" ({file_size_kb} KB)" if file_size_kb > 100 else ""
        print(f"  [{idx}/{total}] {filename}{size_tag} ...", file=sys.stderr, flush=True)
        _LOG.debug("[%d/%d] Analisando %s (%d KB)", idx, total, file_path, file_size_kb)

        # Heartbeat: imprime "ainda processando..." a cada 10s para arquivos lentos
        _stop_heartbeat = threading.Event()
        _t_file_start = time.time()

        def _heartbeat(fname: str, stop: threading.Event) -> None:
            interval = 10
            while not stop.wait(interval):
                elapsed = time.time() - _t_file_start
                print(
                    f"       ⏳ ainda processando {fname}... ({elapsed:.0f}s)",
                    file=sys.stderr, flush=True,
                )
                _LOG.warning("Heartbeat: %s ainda em análise após %.0fs", fname, elapsed)

        hb = threading.Thread(target=_heartbeat, args=(filename, _stop_heartbeat), daemon=True)
        hb.start()

        t_file = time.time()
        result = analyze_file(file_path, min_severity)
        elapsed = time.time() - t_file

        _stop_heartbeat.set()

        _LOG.debug(
            "[%d/%d] Concluído %s | score=%d | issues=%d | %.1fs",
            idx, total, filename, result.score.value, len(result.issues), elapsed,
        )
        print(
            f"       ✓ score={result.score.value}/100 | {len(result.issues)} issue(s) | {elapsed:.1f}s",
            file=sys.stderr, flush=True,
        )

        results.append((file_path, result))

        if output_format == "text":
            print_text(result, file_path)

    total_elapsed = time.time() - t_start
    _LOG.info("scan_directory concluído | %d arquivo(s) | %.1fs total", total, total_elapsed)
    print(f"\n✅ Varredura concluída em {total_elapsed:.1f}s", file=sys.stderr, flush=True)

    return results


# ── Análise de diff entre arquivos ────────────────────────────────────────────
def _get_changed_lines(base_path: str, review_path: str, context: int = 0) -> set[int]:
    """
    Retorna o conjunto de números de linha (1-based) que foram adicionadas ou
    modificadas no review_path em relação ao base_path, usando difflib.

    context: linhas de contexto ao redor de cada mudança (padrão 0 = só as linhas alteradas).
    """
    import difflib

    def _read(path: str) -> list[str]:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return f.readlines()
        except OSError:
            return []

    base_lines   = _read(base_path)
    review_lines = _read(review_path)

    changed: set[int] = set()

    matcher = difflib.SequenceMatcher(None, base_lines, review_lines, autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            # j1..j2 são os índices (0-based) no review — converter para 1-based
            for ln in range(j1 + 1, j2 + 1):
                for ctx in range(-context, context + 1):
                    target = ln + ctx
                    if 1 <= target <= len(review_lines):
                        changed.add(target)

    return changed


def _filter_to_changed(result: AnalysisResult, changed_lines: set[int]) -> AnalysisResult:
    """
    Retorna um novo AnalysisResult com apenas os issues cujas linhas estão
    em changed_lines. Recalcula o score com base nos issues filtrados.
    """
    filtered = [i for i in result.issues if i.line in changed_lines]

    # Recalcular score somando penalidades apenas dos issues filtrados
    total_penalty = 0
    from collections import defaultdict
    penalty_count: dict[str, int] = defaultdict(int)
    for issue in filtered:
        p = RULE_PENALTIES.get(issue.rule_id, 0)
        if p > 0:
            total_penalty += p
            penalty_count[issue.rule_id] += 1

    score_value = max(0, 100 - total_penalty)
    penalties = [
        ScorePenalty(rule_id=rid, penalty=RULE_PENALTIES.get(rid, 0), count=cnt)
        for rid, cnt in penalty_count.items()
    ]
    new_score = Score(value=score_value, label=_score_label(score_value), penalties=penalties)
    return AnalysisResult(issues=filtered, score=new_score)


# ── Comparação entre diretórios ────────────────────────────────────────────────
def compare_directories(
    base_dir: str,
    review_dir: str,
    min_severity: str = "info",
    output_format: str = "html",
    diff_only: bool = False,
) -> list[tuple[str, AnalysisResult, str]]:
    """
    Compara dois diretórios VB6 e analisa apenas arquivos modificados ou adicionados.

    Útil para source control que copia a branch de revisão em pasta temporária:
      base_dir   → pasta com o código atual (branch de destino)
      review_dir → pasta temporária com o código da branch revisada

    diff_only: se True, reporta apenas issues nas linhas efetivamente alteradas
               (usa difflib para calcular o delta linha a linha).

    Retorna lista de (caminho_no_review, AnalysisResult, change_type).
    change_type: "modified" | "added"
    """
    import hashlib

    t_start = time.time()
    _LOG.info("compare_directories iniciado | base=%s | review=%s", base_dir, review_dir)
    print(f"⏳ Indexando arquivos em: {base_dir}", file=sys.stderr, flush=True)

    def _hash(path: str) -> str:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    # Indexar arquivos VB6 do diretório base por caminho relativo (case-insensitive)
    base_index: dict[str, str] = {}
    for root, _dirs, files in os.walk(base_dir):
        for filename in files:
            if os.path.splitext(filename)[1].lower() in VB6_EXTENSIONS:
                abs_path = os.path.join(root, filename)
                rel = os.path.relpath(abs_path, base_dir).lower()
                base_index[rel] = abs_path

    _LOG.info("Indexação concluída | %d arquivo(s) VB6 na base", len(base_index))
    print(f"📂 {len(base_index)} arquivo(s) VB6 na base | verificando diferenças em: {review_dir}", file=sys.stderr, flush=True)

    # Coletar lista de arquivos VB6 a processar na review
    review_files: list[tuple[str, str, str]] = []  # (review_path, rel, change_type)
    for root, _dirs, files in os.walk(review_dir):
        for filename in sorted(files):
            if os.path.splitext(filename)[1].lower() not in VB6_EXTENSIONS:
                continue

            review_path = os.path.join(root, filename)
            rel = os.path.relpath(review_path, review_dir).lower()

            if rel in base_index:
                if _hash(review_path) == _hash(base_index[rel]):
                    continue  # Arquivo idêntico — sem mudança, pular
                review_files.append((review_path, rel, "modified"))
            else:
                review_files.append((review_path, rel, "added"))

    total = len(review_files)
    _LOG.info("Diferenças encontradas | %d arquivo(s) para analisar", total)
    print(f"🔍 {total} arquivo(s) modificado(s)/adicionado(s) para analisar", file=sys.stderr, flush=True)

    results: list[tuple[str, AnalysisResult, str]] = []

    for idx, (review_path, _rel, change_type) in enumerate(review_files, start=1):
        filename = os.path.basename(review_path)
        tag_label = "MODIFICADO" if change_type == "modified" else "NOVO"
        print(f"  [{idx}/{total}] {tag_label}: {filename} ...", file=sys.stderr, flush=True)
        _LOG.debug("[%d/%d] Analisando %s (%s)", idx, total, review_path, tag_label)

        import threading
        file_size_kb = os.path.getsize(review_path) // 1024
        if file_size_kb > 100:
            print(f"       ({file_size_kb} KB)", file=sys.stderr, flush=True)

        _stop_heartbeat = threading.Event()
        _t_file_start = time.time()

        def _heartbeat(fname: str, stop: threading.Event) -> None:
            while not stop.wait(10):
                elapsed = time.time() - _t_file_start
                print(
                    f"       ⏳ ainda processando {fname}... ({elapsed:.0f}s)",
                    file=sys.stderr, flush=True,
                )
                _LOG.warning("Heartbeat: %s ainda em análise após %.0fs", fname, elapsed)

        hb = threading.Thread(target=_heartbeat, args=(filename, _stop_heartbeat), daemon=True)
        hb.start()

        t_file = time.time()
        result = analyze_file(review_path, min_severity)
        _stop_heartbeat.set()

        # Modo diff-only: filtrar issues apenas nas linhas alteradas
        if diff_only and change_type == "modified":
            base_path = base_index[_rel]
            changed_lines = _get_changed_lines(base_path, review_path)
            total_before = len(result.issues)
            result = _filter_to_changed(result, changed_lines)
            _LOG.debug(
                "[%d/%d] diff-only: %d linhas alteradas | %d/%d issue(s) mantidos",
                idx, total, len(changed_lines), len(result.issues), total_before,
            )

        elapsed = time.time() - t_file

        diff_tag = f" [{len(result.issues)} nas linhas alteradas]" if diff_only and change_type == "modified" else ""
        _LOG.debug(
            "[%d/%d] Concluído %s | score=%d | issues=%d | %.1fs",
            idx, total, filename, result.score.value, len(result.issues), elapsed,
        )
        print(
            f"       ✓ score={result.score.value}/100 | {len(result.issues)} issue(s){diff_tag} | {elapsed:.1f}s",
            file=sys.stderr, flush=True,
        )

        results.append((review_path, result, change_type))

        if output_format == "text":
            tag = "✏️  [MODIFICADO]" if change_type == "modified" else "🆕 [NOVO]"
            print(f"\n{tag}", end=" ")
            print_text(result, review_path)

    total_elapsed = time.time() - t_start
    _LOG.info(
        "compare_directories concluído | %d arquivo(s) | %.1fs total",
        total, total_elapsed,
    )
    print(f"\n✅ Análise concluída em {total_elapsed:.1f}s", file=sys.stderr, flush=True)

    return results


# ── Comparação de dois arquivos individuais ────────────────────────────────────
def compare_files(
    base_file: str,
    review_file: str,
    min_severity: str = "info",
    diff_only: bool = False,
) -> tuple[AnalysisResult, set[int]]:
    """
    Compara dois arquivos VB6 individuais e analisa o arquivo de revisão.

    base_file   → arquivo original (referência)
    review_file → arquivo modificado (a ser analisado)
    diff_only   → se True, retorna apenas issues nas linhas alteradas

    Retorna (AnalysisResult, changed_lines).
    """
    t_start = time.time()
    filename = os.path.basename(review_file)
    file_size_kb = os.path.getsize(review_file) // 1024 if os.path.exists(review_file) else 0
    size_tag = f" ({file_size_kb} KB)" if file_size_kb > 100 else ""

    _LOG.info("compare_files iniciado | base=%s | review=%s | diff_only=%s", base_file, review_file, diff_only)
    print(f"⏳ Analisando: {filename}{size_tag} ...", file=sys.stderr, flush=True)

    import threading
    _stop_heartbeat = threading.Event()
    _t_start = time.time()

    def _heartbeat(fname: str, stop: threading.Event) -> None:
        while not stop.wait(10):
            elapsed = time.time() - _t_start
            print(f"       ⏳ ainda processando {fname}... ({elapsed:.0f}s)", file=sys.stderr, flush=True)
            _LOG.warning("Heartbeat: %s ainda em análise após %.0fs", fname, elapsed)

    hb = threading.Thread(target=_heartbeat, args=(filename, _stop_heartbeat), daemon=True)
    hb.start()

    result = analyze_file(review_file, min_severity)
    _stop_heartbeat.set()

    changed_lines: set[int] = set()
    if diff_only and os.path.exists(base_file):
        changed_lines = _get_changed_lines(base_file, review_file)
        total_before = len(result.issues)
        result = _filter_to_changed(result, changed_lines)
        _LOG.debug(
            "diff-only: %d linhas alteradas | %d/%d issue(s) mantidos",
            len(changed_lines), len(result.issues), total_before,
        )

    elapsed = time.time() - t_start
    diff_tag = f" [{len(result.issues)} nas linhas alteradas]" if diff_only else ""
    _LOG.info("compare_files concluído | score=%d | issues=%d%s | %.1fs", result.score.value, len(result.issues), diff_tag, elapsed)
    print(f"       ✓ score={result.score.value}/100 | {len(result.issues)} issue(s){diff_tag} | {elapsed:.1f}s", file=sys.stderr, flush=True)

    return result, changed_lines


# ── Ponto de entrada ───────────────────────────────────────────────────────────
def _write_or_print(content: str, output_path: str | None) -> None:
    """Grava conteúdo em arquivo ou imprime no stdout."""
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📄 Relatório salvo em: {output_path}", file=sys.stderr)
    else:
        print(content)


def _find_guardian_dir() -> Path:
    """Localiza ou cria o diretório .guardian no projeto."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        candidate = parent / ".guardian"
        if candidate.is_dir():
            return candidate
    guardian = cwd / ".guardian"
    guardian.mkdir(exist_ok=True)
    return guardian


def main() -> None:
    args = sys.argv[1:]

    _LOG.info("=== vb6_rule_engine iniciado | args: %s", " ".join(args))

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    output_format = "text"
    min_severity = "info"
    output_path: str | None = None
    diff_only = "--diff-only" in args

    # Extrair --format
    if "--format" in args:
        idx = args.index("--format")
        if idx + 1 < len(args):
            output_format = args[idx + 1]

    # Extrair --severity
    if "--severity" in args:
        idx = args.index("--severity")
        if idx + 1 < len(args):
            min_severity = args[idx + 1]

    # Extrair --output
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 < len(args):
            output_path = args[idx + 1]

    def _auto_save_html(results, title, change_types=None):
        """Salva HTML em .guardian/ automaticamente quando não há --output explícito."""
        if output_format == "json" or output_path is not None:
            return
        ts = datetime.now().strftime("%Y-%m-%d-%H%M")
        guardian = _find_guardian_dir()
        html_dest = guardian / f"code-review-{ts} - VB6.html"
        kwargs = {"title": title}
        if change_types:
            kwargs["change_types"] = change_types
        content = generate_html(results, **kwargs)
        html_dest.write_text(content, encoding="utf-8")
        print(f"📄 Relatório HTML salvo em: {html_dest}", file=sys.stderr)

    # Modo comparação de dois arquivos individuais
    if "--compare-files" in args:
        base_file = ""
        review_file = ""
        if "--base" in args:
            idx = args.index("--base")
            if idx + 1 < len(args):
                base_file = args[idx + 1]
        if "--review" in args:
            idx = args.index("--review")
            if idx + 1 < len(args):
                review_file = args[idx + 1]

        if not base_file or not review_file:
            print("Erro: --compare-files requer --base <arquivo_base> e --review <arquivo_revisao>", file=sys.stderr)
            sys.exit(2)

        _LOG.info("=== Modo compare-files | base=%s | review=%s", base_file, review_file)

        result, changed_lines = compare_files(base_file, review_file, min_severity, diff_only)

        filename = os.path.basename(review_file)
        base_name = os.path.basename(base_file)
        diff_label = " (diff-only)" if diff_only and changed_lines else ""
        file_title = f"VB6 Code Review — {filename} vs {base_name}{diff_label}"

        if output_format == "json":
            print(json.dumps(
                {"issues": [asdict(i) for i in result.issues], "score": asdict(result.score)},
                ensure_ascii=False, indent=2,
            ))
        else:
            # HTML sempre que há output_path ou output_format == html
            html_content = generate_html([(review_file, result)], title=file_title)
            effective_output = output_path
            if effective_output is None:
                ts = datetime.now().strftime("%Y-%m-%d-%H%M")
                guardian = _find_guardian_dir()
                effective_output = str(guardian / f"code-review-{ts} - VB6-FileCompare.html")
            _write_or_print(html_content, effective_output)
            if output_format == "text":
                print_text(result, review_file)

        has_blocker = any(i.severity in ("critical", "error") for i in result.issues)
        sys.exit(1 if has_blocker else 0)

    # Modo comparação entre diretórios
    if "--compare" in args:
        base_dir = ""
        review_dir = ""
        if "--base" in args:
            idx = args.index("--base")
            if idx + 1 < len(args):
                base_dir = args[idx + 1]
        if "--review" in args:
            idx = args.index("--review")
            if idx + 1 < len(args):
                review_dir = args[idx + 1]

        if not base_dir or not review_dir:
            print("Erro: --compare requer --base <pasta_atual> e --review <pasta_revisao>", file=sys.stderr)
            sys.exit(2)

        compare_results = compare_directories(base_dir, review_dir, min_severity, output_format, diff_only)

        if not compare_results:
            print("✅ Nenhuma diferença encontrada entre as pastas.", file=sys.stderr)
            sys.exit(0)

        n_modified = sum(1 for _, _, ct in compare_results if ct == "modified")
        n_added    = sum(1 for _, _, ct in compare_results if ct == "added")

        # Converter para formato compatível com as funções de saída existentes
        plain_results = [(fp, res) for fp, res, _ in compare_results]
        ct_map = {fp: ct for fp, _, ct in compare_results}

        diff_title = (
            f"VB6 Code Review — Diff "
            f"({n_modified} modificado(s), {n_added} adicionado(s))"
        )

        if output_format == "json":
            payload = []
            for fp, res, ct in compare_results:
                payload.append({
                    "file": fp,
                    "change_type": ct,
                    "issues": [asdict(i) for i in res.issues],
                    "score": asdict(res.score),
                })
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif output_format == "html":
            html_content = generate_html(plain_results, title=diff_title, change_types=ct_map)
            _write_or_print(html_content, output_path)
        else:
            print_summary(plain_results)
            # Gerar HTML mesmo no modo "text + html" quando output_path foi fornecido
            if output_path:
                html_content = generate_html(plain_results, title=diff_title, change_types=ct_map)
                _write_or_print(html_content, output_path)
            else:
                _auto_save_html(plain_results, diff_title, change_types=ct_map)

        has_blocker = any(
            i.severity in ("critical", "error")
            for _, res, _ in compare_results
            for i in res.issues
        )
        sys.exit(1 if has_blocker else 0)

    # Modo scan de diretório
    if "--scan" in args:
        scan_dir = "."
        if "--dir" in args:
            idx = args.index("--dir")
            if idx + 1 < len(args):
                scan_dir = args[idx + 1]

        scan_results = scan_directory(scan_dir, min_severity, output_format)

        scan_title = f"VB6 Code Review — {os.path.abspath(scan_dir)}"

        if output_format == "json":
            payload = []
            for fp, result in scan_results:
                payload.append({
                    "file": fp,
                    "issues": [asdict(i) for i in result.issues],
                    "score": asdict(result.score),
                })
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif output_format == "html":
            html_content = generate_html(scan_results, title=scan_title)
            _write_or_print(html_content, output_path)
        else:
            print_summary(scan_results)
            _auto_save_html(scan_results, scan_title)

        has_blocker = any(
            i.severity in ("critical", "error")
            for _, result in scan_results
            for i in result.issues
        )
        sys.exit(1 if has_blocker else 0)

    # Modo arquivo único
    file_path = args[0]
    result = analyze_file(file_path, min_severity)

    file_title = f"VB6 Code Review — {os.path.basename(file_path)}"

    if output_format == "json":
        print(json.dumps(
            {
                "issues": [asdict(i) for i in result.issues],
                "score": asdict(result.score),
            },
            ensure_ascii=False,
            indent=2,
        ))
    elif output_format == "html":
        html_content = generate_html([(file_path, result)], title=file_title)
        _write_or_print(html_content, output_path)
    else:
        print_text(result, file_path)
        _auto_save_html([(file_path, result)], file_title)

    has_blocker = any(i.severity in ("critical", "error") for i in result.issues)
    sys.exit(1 if has_blocker else 0)


if __name__ == "__main__":
    main()
