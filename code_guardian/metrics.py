#!/usr/bin/env python3
"""
Metrics - Calcula métricas de qualidade de código C#.

Detecta:
- Métodos com mais de 30 linhas
- Nesting máximo (> 3 níveis)
- Número de dependências injetadas (> 5 = possível God Class)
- Número de métodos públicos (> 10 = possível God Class)
- Tamanho total da classe

Uso:
    python metrics.py <arquivo.cs>
    python metrics.py <arquivo.cs> --format json
    python metrics.py <arquivo.cs> --format text
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json
import re
from dataclasses import dataclass, asdict, field

MAX_METHOD_LINES = 30
MAX_NESTING = 5  # namespace + class já consomem 2 níveis em C#
MAX_CONSTRUCTOR_DEPS = 5
MAX_PUBLIC_METHODS = 10
MAX_CLASS_LINES = 300


@dataclass
class MethodMetrics:
    name: str
    start_line: int
    line_count: int
    is_public: bool


@dataclass
class ClassMetrics:
    name: str
    start_line: int
    line_count: int
    methods: list[MethodMetrics] = field(default_factory=list)
    constructor_deps: int = 0
    public_method_count: int = 0
    max_nesting: int = 0


@dataclass
class FileMetrics:
    file: str
    total_lines: int
    classes: list[ClassMetrics] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)


def _count_nesting(content: str) -> int:
    """Calcula o nível máximo de nesting (chaves aninhadas)."""
    max_level = 0
    current = 0
    in_string = False
    in_char = False
    in_comment = False
    i = 0

    while i < len(content):
        c = content[i]
        next_c = content[i + 1] if i + 1 < len(content) else ""

        # Comentário de linha
        if not in_string and not in_char and c == "/" and next_c == "/":
            # Pular até fim da linha
            while i < len(content) and content[i] != "\n":
                i += 1
            continue

        # Comentário de bloco
        if not in_string and not in_char and c == "/" and next_c == "*":
            in_comment = True
            i += 2
            continue
        if in_comment and c == "*" and next_c == "/":
            in_comment = False
            i += 2
            continue
        if in_comment:
            i += 1
            continue

        # String literal
        if c == '"' and not in_char and not in_comment:
            in_string = not in_string
        if c == "'" and not in_string and not in_comment:
            in_char = not in_char

        if not in_string and not in_char:
            if c == "{":
                current += 1
                max_level = max(max_level, current)
            elif c == "}":
                current = max(0, current - 1)

        i += 1

    return max_level


def _extract_methods(lines: list[str]) -> list[MethodMetrics]:
    """Extrai métodos do arquivo com suas linhas."""
    methods = []

    # Padrão para detectar métodos C# (simplificado mas funcional)
    method_pattern = re.compile(
        r'^\s*(public|private|protected|internal|protected\s+internal|private\s+protected)'
        r'(?:\s+(?:static|virtual|override|abstract|sealed|async|new|extern))*'
        r'\s+(?:Task(?:<[^>]+>)?|void|bool|int|long|string|decimal|double|float|'
        r'IActionResult|ActionResult(?:<[^>]+>)?|[A-Z]\w*(?:<[^>]+>)?)'
        r'\s+(\w+)\s*[<(]'
    )

    method_starts: list[tuple[int, str, bool]] = []  # (line_idx, name, is_public)

    for i, line in enumerate(lines):
        match = method_pattern.match(line)
        if match:
            access_mod = match.group(1).strip()
            method_name = match.group(2)
            is_public = "public" in access_mod
            method_starts.append((i, method_name, is_public))

    # Calcular tamanho aproximado de cada método
    for idx, (start_i, name, is_public) in enumerate(method_starts):
        end_i = method_starts[idx + 1][0] if idx + 1 < len(method_starts) else len(lines)
        line_count = end_i - start_i

        methods.append(MethodMetrics(
            name=name,
            start_line=start_i + 1,
            line_count=line_count,
            is_public=is_public
        ))

    return methods


def _count_constructor_deps(content: str, class_name: str) -> int:
    """Conta dependências injetadas via construtor."""
    # Procura campos readonly que são injeções (private readonly IXxx _xxx)
    field_pattern = re.compile(
        r'private\s+readonly\s+(?:I\w+|[A-Z]\w+(?:Service|Repository|Provider|Factory|'
        r'Client|Manager|Handler|Sender|Notifier|Logger|Cache))\s+_\w+',
        re.MULTILINE
    )
    return len(field_pattern.findall(content))


def analyze_file(file_path: str) -> FileMetrics:
    """Analisa um arquivo C# e retorna métricas de qualidade."""
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
            lines = content.splitlines()
    except FileNotFoundError:
        metrics = FileMetrics(file=file_path, total_lines=0)
        metrics.issues.append({
            "line": 0, "severity": "error",
            "category": "File", "message": f"Arquivo não encontrado: {file_path}"
        })
        return metrics

    metrics = FileMetrics(file=file_path, total_lines=len(lines))

    # Extrair métodos
    methods = _extract_methods(lines)

    # Calcular nesting máximo
    max_nesting = _count_nesting(content)

    # Contar dependências no construtor
    constructor_deps = _count_constructor_deps(content, "")

    # Contar métodos públicos
    public_methods = [m for m in methods if m.is_public]

    # Criar resumo de classe (simplificado - uma classe por arquivo)
    class_metrics = ClassMetrics(
        name=file_path.split("\\")[-1].replace(".cs", ""),
        start_line=1,
        line_count=len(lines),
        methods=methods,
        constructor_deps=constructor_deps,
        public_method_count=len(public_methods),
        max_nesting=max_nesting
    )
    metrics.classes.append(class_metrics)

    # Gerar issues
    # Métodos longos
    for method in methods:
        if method.line_count > MAX_METHOD_LINES:
            metrics.issues.append({
                "line": method.start_line,
                "severity": "warning",
                "category": "Método Longo",
                "message": (
                    f"Método '{method.name}' tem aproximadamente {method.line_count} linhas "
                    f"(máximo recomendado: {MAX_METHOD_LINES}). Extrair em métodos menores."
                )
            })

    # Nesting profundo
    if max_nesting > MAX_NESTING:
        metrics.issues.append({
            "line": 1,
            "severity": "warning",
            "category": "Deep Nesting",
            "message": (
                f"Nível máximo de nesting: {max_nesting} "
                f"(máximo recomendado: {MAX_NESTING}). Usar guard clauses e early return."
            )
        })

    # Muitas dependências (possível God Class)
    if constructor_deps > MAX_CONSTRUCTOR_DEPS:
        metrics.issues.append({
            "line": 1,
            "severity": "warning",
            "category": "God Class",
            "message": (
                f"Classe com {constructor_deps} dependências injetadas "
                f"(máximo recomendado: {MAX_CONSTRUCTOR_DEPS}). Possível God Class — avaliar SRP."
            )
        })

    # Muitos métodos públicos
    if len(public_methods) > MAX_PUBLIC_METHODS:
        metrics.issues.append({
            "line": 1,
            "severity": "warning",
            "category": "God Class",
            "message": (
                f"Classe com {len(public_methods)} métodos públicos "
                f"(máximo recomendado: {MAX_PUBLIC_METHODS}). Considerar separar em Use Cases."
            )
        })

    # Arquivo muito longo
    if len(lines) > MAX_CLASS_LINES:
        metrics.issues.append({
            "line": 1,
            "severity": "info",
            "category": "Arquivo Grande",
            "message": (
                f"Arquivo com {len(lines)} linhas "
                f"(máximo recomendado: {MAX_CLASS_LINES}). Avaliar separação de responsabilidades."
            )
        })

    return metrics


def _severity_icon(severity: str) -> str:
    return {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    file_path = args[0]
    output_format = "json"

    if "--format" in args:
        idx = args.index("--format")
        if idx + 1 < len(args):
            output_format = args[idx + 1]

    file_metrics = analyze_file(file_path)

    if output_format == "json":
        print(json.dumps(asdict(file_metrics), ensure_ascii=False, indent=2))
    else:
        print(f"\n📊 Métricas: {file_path}")
        print(f"   Total de linhas: {file_metrics.total_lines}")

        for cls in file_metrics.classes:
            print(f"\n   Classe: {cls.name}")
            print(f"   ├─ Métodos: {len(cls.methods)} (públicos: {cls.public_method_count})")
            print(f"   ├─ Dependências injetadas: {cls.constructor_deps}")
            print(f"   └─ Nesting máximo: {cls.max_nesting}")

            long_methods = [m for m in cls.methods if m.line_count > MAX_METHOD_LINES]
            if long_methods:
                print(f"\n   Métodos longos ({len(long_methods)}):")
                for m in long_methods:
                    print(f"   🟡 {m.name} (~{m.line_count} linhas, L{m.start_line})")

        if file_metrics.issues:
            print(f"\n   Issues ({len(file_metrics.issues)}):")
            for issue in file_metrics.issues:
                icon = _severity_icon(issue["severity"])
                print(f"   {icon} L{issue['line']:3d} [{issue['category']}] {issue['message']}")
        else:
            print("\n   ✅ Métricas dentro dos padrões recomendados.")

    has_issues = bool(file_metrics.issues)
    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
