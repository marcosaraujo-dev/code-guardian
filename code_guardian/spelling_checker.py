#!/usr/bin/env python3
"""
Spelling Checker - Detecta erros de escrita em strings de código C#.
Verifica mensagens de erro, validação e UI em busca de palavras mal escritas.

Uso:
    python spelling_checker.py <arquivo.cs>
    python spelling_checker.py <arquivo.cs> --format json
    python spelling_checker.py <arquivo.cs> --format text
    python spelling_checker.py <arquivo.cs> --severity warning
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json
import re
from dataclasses import dataclass, asdict

# ─────────────────────────────────────────────────────────────────────────────
# Dicionário de erros comuns em português (palavra_errada → palavra_correta)
# Focado em domínios de RH, folha de pagamento e sistemas corporativos.
# ─────────────────────────────────────────────────────────────────────────────
MISSPELLINGS: dict[str, str] = {
    # Funcionário
    "cunfionario": "funcionário",
    "funcionaro": "funcionário",
    "funcioanrio": "funcionário",
    "fucionario": "funcionário",
    "funcionairo": "funcionário",
    "funcioario": "funcionário",
    "funciornario": "funcionário",
    "funionario": "funcionário",

    # Empresa / Departamento
    "enpresa": "empresa",
    "emresa": "empresa",
    "deprtamento": "departamento",
    "departamneto": "departamento",
    "deparatmento": "departamento",
    "departemento": "departamento",

    # Salário / Pagamento
    "salrio": "salário",
    "salairo": "salário",
    "pagamento": "pagamento",
    "pagaento": "pagamento",
    "pagamneto": "pagamento",
    "vencimeto": "vencimento",
    "vencimneto": "vencimento",

    # Nome / Código
    "nmoe": "nome",
    "nemo": "nome",
    "noe": "nome",
    "codgio": "código",
    "condigo": "código",
    "codigoo": "código",
    "cdoigo": "código",

    # Informe / Preencha
    "informa": "informe",
    "infroem": "informe",
    "infrome": "informe",
    "prencha": "preencha",
    "preecha": "preencha",
    "preencah": "preencha",
    "prerecha": "preencha",

    # Obrigatório / Campo
    "obrigatiro": "obrigatório",
    "obrigatorio": "obrigatório",
    "obrigarório": "obrigatório",
    "obrigatoroi": "obrigatório",
    "camop": "campo",
    "camop": "campo",
    "cmpo": "campo",

    # Data / Período
    "daat": "data",
    "dat": "data",
    "peiriodo": "período",
    "perioro": "período",
    "peridoo": "período",
    "peíodo": "período",

    # Valor / Quantidade
    "valro": "valor",
    "varlo": "valor",
    "qauntidade": "quantidade",
    "qantidade": "quantidade",
    "quantidate": "quantidade",
    "quantidaed": "quantidade",

    # Registro / Cadastro
    "regitro": "registro",
    "reigstro": "registro",
    "regsitro": "registro",
    "cadastrao": "cadastro",
    "cadatro": "cadastro",
    "cadsatro": "cadastro",

    # Selecione / Escolha
    "slecione": "selecione",
    "selecoine": "selecione",
    "seelcione": "selecione",
    "ecslhoa": "escolha",
    "escloha": "escolha",

    # Usuário
    "usario": "usuário",
    "usairo": "usuário",
    "ussário": "usuário",
    "usiário": "usuário",

    # Senha / Acesso
    "snha": "senha",
    "sanha": "senha",
    "aceso": "acesso",
    "acesoo": "acesso",
    "acsso": "acesso",

    # Erro / Falha
    "eror": "erro",
    "ero": "erro",
    "eroo": "erro",
    "flaha": "falha",
    "fahlha": "falha",
    "fahal": "falha",

    # Inválido / Incorreto
    "invalido": "inválido",
    "imvalido": "inválido",
    "invlado": "inválido",
    "incorrecto": "incorreto",
    "incorrto": "incorreto",

    # Confirmar / Cancelar
    "confiramr": "confirmar",
    "confiramr": "confirmar",
    "cnfirmar": "confirmar",
    "canelar": "cancelar",
    "cancelra": "cancelar",
    "calcenar": "cancelar",

    # Sucesso / Concluído
    "suesso": "sucesso",
    "suscesso": "sucesso",
    "sucecsso": "sucesso",
    "conculido": "concluído",
    "conclído": "concluído",
    "ocnluído": "concluído",

    # Matrícula / Admissão
    "matriucla": "matrícula",
    "maticula": "matrícula",
    "admisão": "admissão",
    "admicão": "admissão",
    "admissao": "admissão",

    # Contrato / Cargo
    "contrao": "contrato",
    "contarot": "contrato",
    "cargoo": "cargo",
    "carfo": "cargo",

    # Endereço / CEP
    "edreco": "endereço",
    "endereçoo": "endereço",
    "enedrço": "endereço",

    # Telefone / Email
    "teelfone": "telefone",
    "telefoen": "telefone",
    "emali": "email",
    "e-mail": "e-mail",  # correto, não alterar
    "emial": "email",

    # Recibo / Comprovante
    "reciob": "recibo",
    "reciboo": "recibo",
    "coprovante": "comprovante",
    "comprvoante": "comprovante",

    # Benefício / Desconto
    "benificio": "benefício",
    "benifício": "benefício",
    "desocnto": "desconto",
    "descotno": "desconto",

    # Férias / Licença
    "ferais": "férias",
    "féiras": "férias",
    "licena": "licença",
    "licença": "licença",  # correto
    "licenca": "licença",

    # Departamento (extras)
    "recuros": "recursos",
    "recursso": "recursos",
    "humanos": "humanos",   # correto
    "humanso": "humanos",

    # Palavras genéricas de sistema
    "cadastarr": "cadastrar",
    "cadatsar": "cadastrar",
    "atualizaer": "atualizar",
    "atualizr": "atualizar",
    "excludir": "excluir",
    "ecxluir": "excluir",
    "inserri": "inserir",
    "inserrir": "inserir",
    "consutlar": "consultar",
    "consutla": "consultar",
    "pesquisaar": "pesquisar",
    "pesquiar": "pesquisar",
    "lsitar": "listar",
    "lsita": "listar",
    "imprmir": "imprimir",
    "imprimr": "imprimir",
    "exportar": "exportar",   # correto
    "exportarr": "exportar",
    "importra": "importar",
    "importarr": "importar",

    # Mensagens de UI
    "carreagndo": "carregando",
    "carreagnado": "carregando",
    "aguardee": "aguarde",
    "agaurdando": "aguardando",
    "aguardnado": "aguardando",
    "pocessando": "processando",
    "processnado": "processando",
    "procssando": "processando",
    "savlando": "salvando",
    "salvadndo": "salvando",
    "gravnado": "gravando",
    "gravaando": "gravando",
}

# ─────────────────────────────────────────────────────────────────────────────
# Padrões de regex para extrair strings literais de C#
# ─────────────────────────────────────────────────────────────────────────────
_STRING_PATTERNS = [
    # Strings interpoladas: $"texto {expr} texto"
    (r'\$"((?:[^"\\]|\\.)*)"', "interpolated"),
    # Strings verbatim: @"texto"
    (r'@"((?:[^"]|"")*)"', "verbatim"),
    # Strings normais: "texto"
    (r'"((?:[^"\\]|\\.)*)"', "literal"),
]

# Contextos onde strings têm maior probabilidade de serem mensagens ao usuário
_MESSAGE_CONTEXT_PATTERNS = [
    r'(?:message|mensagem|msg|texto|text|label|titulo|title|caption|description|descricao|'
    r'erro|error|aviso|warning|info|sucesso|success|placeholder|hint|tooltip|'
    r'AddNotification|AddError|AddWarning|throw\s+new\s+\w*Exception|'
    r'ModelState\.AddModelError|NotificationContext|context\.Add|'
    r'MessageBox\.|ShowMessage|Alert|Notification)\s*[=\(,]?\s*\$?"'
]


@dataclass
class SpellingIssue:
    file: str
    line: int
    severity: str
    category: str
    rule_id: str
    message: str
    source: str = "spelling_checker"


def _extract_strings_from_line(line: str) -> list[tuple[str, int]]:
    """
    Extrai strings literais de uma linha C#.
    Retorna lista de (conteudo_da_string, posicao_inicio).
    Ignora linhas que são comentários.
    """
    stripped = line.strip()
    # Ignorar linhas de comentário
    if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
        return []

    # Remover comentário inline antes de extrair strings
    # Simples: pegar tudo antes de '//' que não esteja dentro de string
    results: list[tuple[str, int]] = []

    for pattern, _ in _STRING_PATTERNS:
        for match in re.finditer(pattern, line):
            content = match.group(1)
            results.append((content, match.start()))

    return results


def _is_in_message_context(line: str) -> bool:
    """Verifica se a linha está em um contexto de mensagem ao usuário."""
    for pattern in _MESSAGE_CONTEXT_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def _tokenize(text: str) -> list[str]:
    """Separa o texto em palavras, removendo caracteres especiais."""
    # Remove expressões entre chaves (interpolação: {variavel})
    text = re.sub(r'\{[^}]*\}', ' ', text)
    # Separa por espaços, pontuação, underscores, camelCase, etc.
    words = re.findall(r"[A-Za-zÀ-ú]+", text)
    return [w.lower() for w in words if len(w) >= 3]


def analyze_file(file_path: str, min_severity: str = "warning") -> list[SpellingIssue]:
    """Analisa um arquivo C# e retorna issues de ortografia encontradas."""
    severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
    min_level = severity_order.get(min_severity, 2)

    # Spelling é sempre 'warning' — pular se nível mínimo for mais restrito
    if severity_order["warning"] > min_level:
        return []

    issues: list[SpellingIssue] = []

    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return [SpellingIssue(
            file=file_path, line=0, severity="error",
            category="File", rule_id="FILE_NOT_FOUND",
            message=f"Arquivo não encontrado: {file_path}"
        )]
    except Exception as e:
        return [SpellingIssue(
            file=file_path, line=0, severity="error",
            category="File", rule_id="FILE_READ_ERROR",
            message=f"Erro ao ler arquivo: {e}"
        )]

    for line_num, line in enumerate(lines, 1):
        strings = _extract_strings_from_line(line)
        if not strings:
            continue

        in_message_context = _is_in_message_context(line)

        for string_content, _ in strings:
            words = _tokenize(string_content)
            found_in_line: set[str] = set()

            for word in words:
                if word in MISSPELLINGS and word not in found_in_line:
                    found_in_line.add(word)
                    correction = MISSPELLINGS[word]

                    # Determinar severidade: warning em contexto de mensagem, info caso contrário
                    severity = "warning" if in_message_context else "info"
                    if severity_order[severity] > min_level:
                        continue

                    issues.append(SpellingIssue(
                        file=file_path,
                        line=line_num,
                        severity=severity,
                        category="Ortografia",
                        rule_id="SPELLING_ERROR",
                        message=(
                            f"Possível erro de ortografia: '{word}' → '{correction}'. "
                            f"Verifique a string na linha {line_num}."
                        )
                    ))

    return issues


def _severity_icon(severity: str) -> str:
    return {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")


def print_text(issues: list[SpellingIssue], file_path: str) -> None:
    if not issues:
        print(f"✅ {file_path}: Nenhum erro de ortografia encontrado.")
        return

    print(f"\n📁 {file_path}")
    for issue in sorted(issues, key=lambda i: i.line):
        icon = _severity_icon(issue.severity)
        print(f"  {icon} L{issue.line:3d} [{issue.category}] {issue.message}")


def print_summary(issues: list[SpellingIssue]) -> None:
    from collections import Counter
    counts = Counter(i.severity for i in issues)
    total = sum(counts.values())
    if total == 0:
        print("\n✅ Spelling Checker: Nenhum erro de ortografia encontrado.")
        return
    print(f"\nSpelling Checker: {total} issue(s) encontrada(s) — "
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

    # Spelling não bloqueia build (sem critical/error intencionais)
    sys.exit(0)


if __name__ == "__main__":
    main()
