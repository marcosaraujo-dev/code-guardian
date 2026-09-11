# Code Guardian — Início Rápido

Ferramentas de code review automatizado para C#.
Combina análise estática (regex + métricas) com IA (Gemini ou Ollama local).

---

## Pré-requisitos

- Python 3.11+
- Git instalado
- (Opcional) Chave da API Gemini ou Ollama instalado

---

## Estrutura dos scripts

```text
code_guardian/
├── runner.py       → orquestrador completo: diff + rule_engine + metrics + IA (ponto de entrada CLI)
├── rule_engine.py  → detecta 20+ padrões problemáticos via regex (offline, rápido)
├── metrics.py      → calcula métricas de qualidade: nesting, God Class, métodos longos
├── diff_parser.py  → extrai arquivos e linhas alterados do git diff
└── ai_client.py    → análise de IA com fallback automático Gemini → Ollama
```

---

## Uso mais comum — comando único (recomendado)

```bash
# Analisar todos os arquivos .cs alterados vs origin/main (com IA)
python code_guardian/runner.py

# Apenas análise estática (sem IA, instantâneo)
python code_guardian/runner.py --rules-only

# Apenas arquivos staged (antes do commit)
python code_guardian/runner.py --staged --rules-only

# Arquivo específico
python code_guardian/runner.py --file Services/UserService.cs

# Varrer todo o projeto recursivamente (sem precisar de git diff)
python code_guardian/runner.py --scan

# Varrer diretório específico
python code_guardian/runner.py --scan --dir C:/projetos/MinhaApp
```

O `runner.py` executa rule_engine + metrics + IA em todos os arquivos alterados e gera um **relatório consolidado com Risk Score**.

---

## Uso mais comum — revisar um arquivo

```bash
# 1. Análise estática (sem IA, instantâneo)
python code_guardian/rule_engine.py Services/UserService.cs --format text
python code_guardian/metrics.py Services/UserService.cs --format text

# 2. Análise de IA (Gemini ou Ollama, conforme disponível)
python code_guardian/ai_client.py Services/UserService.cs
```

---

## Uso mais comum — revisar PR completo

```bash
# Ver quais arquivos .cs mudaram neste branch
python code_guardian/diff_parser.py --files-only --format text

# Analisar cada arquivo alterado
FILES=$(python code_guardian/diff_parser.py --files-only --format text)
for FILE in $FILES; do
    echo "=== $FILE ==="
    python code_guardian/rule_engine.py "$FILE" --format text
    python code_guardian/metrics.py "$FILE" --format text
    python code_guardian/ai_client.py "$FILE"
    echo ""
done
```

---

## Configurar IA

### Opção A — Gemini (internet, API gratuita com limites)

```bash
# Windows PowerShell
$env:GEMINI_API_KEY = "AIza..."

# Linux / macOS
export GEMINI_API_KEY="AIza..."
```

### Opção B — Ollama (local, sem internet, código não sai da máquina)

```bash
# 1. Instalar: https://ollama.com/download
# 2. Baixar o modelo (4.7 GB, uma única vez)
ollama pull qwen2.5-coder:7b
# 3. Verificar
curl http://localhost:11434/api/tags
```

O `ai_client.py` detecta e usa automaticamente o que estiver disponível.

---

## Formatos de saída

Todos os scripts aceitam `--format text` (terminal) ou `--format json` (integração).

| Formato | Quando usar |
| ------- | ----------- |
| `text` | Leitura no terminal, debug manual |
| `json` | Integração com outros scripts, pipelines, Claude Code |

---

## Severidades

| Ícone | Nível | Significado |
| ----- | ----- | ----------- |
| 🔴 | `critical` | Bloqueia merge — segurança ou corrupção de dados |
| 🟠 | `error` | Deve ser corrigido — bug confirmado ou risco alto |
| 🟡 | `warning` | Deve ser revisado — violação de padrão |
| 🔵 | `info` | Oportunidade de melhoria |

---

## Exit codes (úteis em CI)

```bash
# rule_engine.py: exit 1 se houver critical ou error
python rule_engine.py MeuArquivo.cs || echo "BLOQUEADO — corrigir antes do merge"

# diff_parser.py --files-only: exit 1 se não houver arquivos .cs alterados
python diff_parser.py --files-only --format text || echo "Nenhum arquivo .cs no PR"
```

---

## Documentação detalhada por script

| Documento | Conteúdo |
| --------- | -------- |
| [13-Runner-CLI.md](13-Runner-CLI.md) | Runner CLI completo (ponto de entrada recomendado) |
| [08-Uso-rule-engine.md](08-Uso-rule-engine.md) | Regras, entradas, saídas JSON/text, exemplos |
| [09-Uso-metrics.md](09-Uso-metrics.md) | Métricas, limiares, campos JSON, exemplos |
| [10-Uso-diff-parser.md](10-Uso-diff-parser.md) | Modos (branch/staged), filtros, saída para IA |
| [11-Uso-ai-client.md](11-Uso-ai-client.md) | Provedores (Gemini/Claude/OpenAI/Ollama), campos JSON |
| [12-Trocar-Provedor-IA.md](12-Trocar-Provedor-IA.md) | Como trocar de provedor, receitas prontas |
| [07-Ollama-Setup.md](07-Ollama-Setup.md) | Instalação e configuração do Ollama |
| [14-TFS-Pipeline.md](14-TFS-Pipeline.md) | Integração com TFS/Azure DevOps Pipeline |
| [15-Git-Hooks.md](15-Git-Hooks.md) | Hooks pre-commit e pre-push (install/uninstall/status) |
| [16-Fluxo-Desenvolvedor.md](16-Fluxo-Desenvolvedor.md) | Guia completo de uso no dia a dia |

---

## Exemplo de saída combinada

```text
=== Services/UserService.cs ===

📁 Services/UserService.cs
  🔴 L  42 [SQL Injection] Possível SQL Injection: query construída por concatenação.
  🟠 L  87 [Deadlock Async] Task.Result pode causar deadlock. Use await.
Rule Engine: 2 issue(s) — 🔴 1 critical  🟠 1 error

📊 Métricas: Services/UserService.cs
   Total de linhas: 412
   Classe: UserService
   ├─ Métodos: 14 (públicos: 12)
   ├─ Dependências injetadas: 7
   └─ Nesting máximo: 5
   🟡 L  1 [God Class] Classe com 7 dependências injetadas...

[guardian] Usando Gemini (gemini-1.5-pro) para análise de IA...
[guardian] Análise concluída em 8.1s

=== Análise de IA — Services/UserService.cs ===
Provedor : Gemini (gemini-1.5-pro)
Tempo    : 8.1s

## Bugs de Lógica

**Linha 42** — critical
SQL Injection confirmado. A interpolação `"...WHERE id = " + request.Id`
permite que qualquer valor no campo `Id` altere a estrutura da query.
[sugestão de correção...]
```
