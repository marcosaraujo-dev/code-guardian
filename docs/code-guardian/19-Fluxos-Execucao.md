# Fluxos de Execução — Guia Completo

Todos os caminhos possíveis para executar o Code Guardian, com o que acontece em cada etapa, o que é gerado e quando usar cada um.

---

## Mapa de Entradas

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PONTOS DE ENTRADA                                 │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Agente IA   │  │ Desenvolvedor│  │  Git Hooks   │              │
│  │  /code-review│  │  runner.py   │  │ (automático) │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│         └─────────────────┼─────────────────┘                      │
│                           ▼                                         │
│              ┌─────────────────────────┐                            │
│              │  rule_engine.py         │ Análise estática (sempre)  │
│              │  metrics.py             │ Métricas de código         │
│              │  diff_parser.py         │ Extração do diff git       │
│              └─────────────────────────┘                            │
│                           │                                         │
│              ┌─────────────────────────┐                            │
│              │  ai_client.py           │ Análise de IA (opcional)   │
│              │                         │                            │
│              │  primary ──▶ Gemini API │ Via internet (API Key)     │
│              │     ou  ──▶ Ollama      │ Local, sem internet        │
│              │     ou  ──▶ Claude Code │ Nativo, no agente          │
│              │  fallback ──▶ automático│ Se primary falhar          │
│              └─────────────────────────┘                            │
│                           │                                         │
│              ┌─────────────────────────┐                            │
│              │  Saídas geradas         │                            │
│              │  • Texto no terminal    │                            │
│              │  • HTML em .codeguardian/   │                            │
│              │  • JSON (CI/CD)         │                            │
│              │  • Trailer no commit    │                            │
│              │  • Plano de Correção    │                            │
│              └─────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Fluxo 1 — Agente de IA (`/code-review`)

**Quem usa**: Desenvolvedor dentro do Claude Code, Amazon Q ou qualquer agente que suporte SKILL.md.

**Gatilho**: Usuário digita `/code-review` (ou `/code-review --staged`, `--file`, etc.)

```
Usuário: /code-review
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  SKILL: .claude/skills/code-review/SKILL.md                 │
│                                                              │
│  PASSO 1 — Detectar escopo                                   │
│    Bash: git diff origin/main...HEAD --name-only             │
│    Filtrar: apenas .cs (excluir Migrations, obj/, bin/)      │
│                                                              │
│  PASSO 2 — Rule Engine (via Bash tool)                       │
│    python code_guardian/rule_engine.py       │
│    → JSON com issues: SQL Injection, deadlocks, secrets...   │
│    Tempo: < 1 segundo por arquivo                            │
│                                                              │
│  PASSO 3 — Métricas (via Bash tool)                          │
│    python code_guardian/metrics.py           │
│    → JSON com: linhas/método, nesting, dependências          │
│                                                              │
│  PASSO 4 — Análise de IA (o próprio agente)                  │
│    Read tool: lê cada arquivo .cs                            │
│    Bash: diff_parser.py --for-ai (linhas alteradas)          │
│    IA analisa: Zona 1 (linhas novas) + Zona 2 (impacto)      │
│    Detecta: NullRef, deadlocks, race cond., IDOR, N+1...     │
│    ⚡ SEM custo de API — o próprio modelo analisa             │
│                                                              │
│  PASSO 5 — Consolidar                                        │
│    Deduplica issues dos scripts + IA                         │
│    Classifica: introduced / impact / preexisting             │
│    Calcula Risk Score                                        │
│                                                              │
│  PASSO 6 — Relatório markdown na conversa                    │
│    Resumo + issues por arquivo + métricas + recomendações    │
│                                                              │
│  PASSO 7 — Plano de Correção                                 │
│    Lista priorizada: blockers obrigatórios + melhorias       │
│    Cada item com: arquivo, linha, código antes/depois        │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
        Saída: Relatório markdown na conversa
               Dev pode interagir: "corrija o item 2"
               Dev pode pedir: "explique por que isso é um problema"
```

**Provedor de IA neste fluxo**: O próprio modelo do agente (Claude, Amazon Q, etc.). Não chama `ai_client.py`.

**Quando usar**: Durante desenvolvimento, ao abrir um arquivo para review, ao criar um PR.

---

## Fluxo 2 — Desenvolvedor (terminal, `runner.py`)

**Quem usa**: Desenvolvedor manualmente no terminal ou em scripts.

**Gatilho**: `python code_guardian/runner.py [flags]`

### Subfluxos por modo de seleção de arquivos

```
python runner.py [flags]
        │
        ├─── --file Services/X.cs        → analisa 1 arquivo específico
        │
        ├─── --scan                       → varre diretório atual (todos os .cs)
        │    --scan --dir C:/meu/projeto  → varre diretório específico
        │
        ├─── --staged                     → arquivos em git staging area
        │
        └─── (padrão)                     → git diff vs origin/main
```

### Pipeline interno

```
Arquivo(s) selecionados
        │
        ▼
Para cada .cs (com progresso no stderr: "[guardian] Analisando (2/8): X.cs"):
        │
        ├─► rule_engine.py --format json
        │   Resultado: lista de issues com severidade, linha, categoria
        │
        ├─► metrics.py --format json
        │   Resultado: total_lines, max_method_lines, max_nesting, deps
        │
        └─► ai_client.py --format json    (se --rules-only NÃO especificado)
            Resultado: análise textual por arquivo
                │
                ▼
        ┌───────────────────────────┐
        │  Qual IA usar?            │
        │  (lido de config.json)    │
        │                           │
        │  primary = gemini?        │
        │    → GEMINI_API_KEY       │
        │      em variável de env   │
        │                           │
        │  primary = ollama?        │
        │    → localhost:11434      │
        │      sem internet         │
        │                           │
        │  fallback automático se   │
        │  primary falhar           │
        └───────────────────────────┘
        │
        ▼
Consolidar: issues + métricas + IA
Calcular Risk Score
        │
        ├─── --format text (padrão)  → relatório markdown + Plano de Correção
        ├─── --format json           → JSON (sem HTML)
        └─── --output rel.html       → HTML com Design System
```

### Flags disponíveis

| Flag | Efeito |
|------|--------|
| `--rules-only` | Pula IA (mais rápido, apenas scripts) |
| `--severity error` | Mostra apenas critical/error |
| `--fail-on critical` | Exit 1 apenas em critical |
| `--format json` | Saída JSON (CI/CD), sem HTML |
| `--output rel.html` | Salva HTML no caminho dado |
| `--timeout 90` | Timeout por subprocess |
| `--summary-file path` | Grava trailer para git hook |

### Saídas geradas

| Modo | Saída gerada automaticamente |
|------|------------------------------|
| Qualquer (exceto `--format json`) | `.codeguardian/last-runner-report.html` |
| `--output caminho.html` | caminho especificado |

### Quando usar

```bash
# Review rápido antes de commitar (sem IA)
python runner.py --staged --rules-only

# Review completo do PR com IA
python runner.py --base origin/main

# Varrer projeto inteiro offline (Ollama)
python runner.py --scan --rules-only

# Para CI/CD — bloquear se houver error+
python runner.py --format json || echo "BLOQUEADO"
```

---

## Fluxo 3 — Commit (Git Hooks automáticos)

**Quem usa**: Automático — dispara em cada `git commit` e `git push`.

**Setup**: `python code_guardian/install_hooks.py install`

### Hook 1: `pre-commit`

```
git commit -m "feat: ..."
        │
        ▼
[pre-commit hook dispara]
        │
        ├─ Verifica se há .cs no stage (grep -i .cs$)
        │  Se não houver → exit 0 (segue sem análise)
        │
        ├─ Limpa: rm -f .codeguardian/last-commit-summary.txt
        │         (evita reutilização de resultado anterior)
        │
        ├─ Executa runner.py:
        │   --staged              → apenas arquivos staged
        │   --rules-only          → sem IA (rápido, < 10s)
        │   --severity warning    → HTML completo
        │   --fail-on error       → bloqueia em critical/error
        │   --output last-commit-report.html
        │   --summary-file last-commit-summary.txt
        │
        ├─ EXIT_CODE=$?
        │
        ├─ Se EXIT_CODE != 0 (blockers encontrados):
        │   rm -f last-commit-summary.txt
        │   echo "[guardian] BLOQUEADO: issues criticas encontradas."
        │   echo "   Relatorio: .codeguardian/last-commit-report.html"
        │   exit 1 → commit abortado
        │
        └─ Se EXIT_CODE = 0 (passou):
            echo "[guardian] Nenhum bloqueador. Commit liberado."
            echo "   Relatorio: .codeguardian/last-commit-report.html"
            exit 0 → segue para prepare-commit-msg
```

### Hook 2: `prepare-commit-msg`

```
[prepare-commit-msg hook dispara — após pre-commit]
        │
        ├─ Lê .codeguardian/last-commit-summary.txt
        │
        ├─ Verifica se arquivo tem < 5 minutos
        │  (proteção contra --no-verify com arquivo stale)
        │
        ├─ Verifica commit_source:
        │  "commit" (amend) → pula (não duplica)
        │  "merge" / "squash" → pula
        │
        └─ Appenda trailer na mensagem do commit:
           "Guardian-Review: ✅ Passou | Score: 4 | Critical: 0 | ..."

Resultado no git log:
    feat: implementar validacao de CPF

    Guardian-Review: ✅ Passou | Score: 4 | Critical: 0 | Error: 0 | Warning: 1 | Arquivos: 2
```

### Hook 3: `pre-push`

```
git push origin feature/x
        │
        ▼
[pre-push hook dispara]
        │
        ├─ Executa runner.py:
        │   (sem --staged → diff completo vs origin/main)
        │   --rules-only
        │   --severity warning
        │   --fail-on error
        │   --output last-push-report.html
        │
        ├─ Se bloqueado:
        │   echo "[guardian] BLOQUEADO"
        │   echo "   Relatorio: .codeguardian/last-push-report.html"
        │   exit 1 → push abortado
        │
        └─ Se passou:
            echo "[guardian] Push liberado."
            exit 0 → push executado
```

### Fluxo completo commit → push

```
dev escreve código
        │
git add Services/X.cs
        │
git commit -m "feat: ..."
        │
[pre-commit]──── analisa staged ──── blockers? ──▶ SIM → abortado
        │                                            NÃO → segue
[prepare-commit-msg]──── injeta Guardian-Review trailer
        │
commit gravado no histórico
        │
git push origin feature/x
        │
[pre-push]──── analisa diff completo ──── blockers? ──▶ SIM → abortado
        │                                               NÃO → segue
push executado
        │
Abre PR no TFS → Revisor vê o trailer nos commits
```

### Pular os hooks (emergência)

```bash
git commit --no-verify -m "hotfix urgente"   # pula pre-commit
git push   --no-verify origin main           # pula pre-push
```

---

## Fluxo 4 — Com Ollama (IA local, sem internet)

**Quando usar**: Sem acesso à internet, ambiente corporativo restrito, ou privacidade do código.

### Setup

```bash
# 1. Instalar Ollama
# Windows: https://ollama.ai/download
# Linux:   curl -fsSL https://ollama.ai/install.sh | sh

# 2. Baixar modelo recomendado (escolher conforme RAM disponível)
ollama pull qwen2.5-coder:7b      # 8 GB RAM — rápido, boa qualidade
ollama pull qwen2.5-coder:14b     # 16 GB RAM — recomendado
ollama pull deepseek-r1:14b       # 16 GB RAM — raciocínio profundo
ollama pull glm4:latest           # 16 GB RAM — uso geral
# ollama pull qwen2.5-coder:32b   # 32 GB RAM ou GPU — máxima qualidade

# 3. Verificar que está rodando
ollama list
curl http://localhost:11434/api/tags
```

### Configurar como primary

```json
// code_guardian/config.json
{
  "ai": {
    "primary": "ollama",
    "fallback": "none",
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "qwen2.5-coder:7b",
      "timeout_seconds": 120
    }
  }
}
```

### Pipeline com Ollama

```
runner.py (qualquer modo)
        │
        ▼
rule_engine.py + metrics.py  (sem IA, sempre roda)
        │
        ▼
ai_client.py
        │
        ├─ primary = "ollama"
        │
        ├─ Verifica: GET http://localhost:11434/api/tags
        │   Se não responder → fallback (ou skip se fallback = "none")
        │
        └─ POST http://localhost:11434/api/generate
           model: "qwen2.5-coder:7b"
           prompt: [arquivo C# + instruções de review]
           timeout: 120s
                │
                ▼
           Resposta: análise textual do arquivo
```

### Usando Ollama no runner.py

```bash
# Análise completa com Ollama
python runner.py --staged

# Se quiser verificar qual IA está sendo usada, observe a linha:
# [guardian] Usando Ollama (qwen2.5-coder:7b) para análise de IA...
```

### Usando Ollama no /code-review

O `/code-review` **não chama `ai_client.py`** — o próprio agente (Claude, Amazon Q) já é a IA.
Se quiser que o runner.py em background use Ollama, ajuste o `config.json` conforme acima.

### Comparativo de modelos Ollama

| Modelo | RAM runtime | Especialidade | Qualidade review C# | Velocidade |
|--------|------------|---------------|---------------------|------------|
| `qwen2.5-coder:7b` | ~6 GB | Código | ⭐⭐⭐⭐ | Rápido (~20s) |
| `qwen2.5-coder:14b` | ~11 GB | Código | ⭐⭐⭐⭐⭐ | Médio (~45s) |
| `deepseek-r1:14b` | ~11 GB | Raciocínio | ⭐⭐⭐⭐⭐ | Lento (~60–90s) |
| `glm4:latest` | ~5 GB | Geral | ⭐⭐⭐⭐ | Rápido (~35s) |
| `qwen2.5-coder:32b` | ~21 GB | Código | ⭐⭐⭐⭐⭐ | Lento (~90s) |

**Para 16 GB RAM**: use `qwen2.5-coder:14b` como primário para code review e `deepseek-r1:14b` para análise de bugs complexos. Não rode dois simultaneamente.

---

## Fluxo 5 — Via API (Gemini)

**Quando usar**: Análise mais profunda com modelo grande, sem necessidade de Ollama local.

### Setup

```bash
# 1. Obter API Key gratuita
# https://aistudio.google.com/app/apikey

# 2. Definir variável de ambiente
# Windows (PowerShell):
$env:GEMINI_API_KEY = "AIza..."

# Windows (permanente):
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "AIza...", "User")

# Linux/macOS:
export GEMINI_API_KEY="AIza..."
```

### Configurar como primary

```json
// code_guardian/config.json
{
  "ai": {
    "primary": "gemini",
    "fallback": "ollama",
    "gemini": {
      "model": "gemini-1.5-pro",
      "api_key_env": "GEMINI_API_KEY"
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "qwen2.5-coder:7b",
      "timeout_seconds": 120
    }
  }
}
```

### Pipeline com Gemini

```
ai_client.py
        │
        ├─ primary = "gemini"
        │
        ├─ Lê GEMINI_API_KEY da variável de ambiente
        │   Se vazia → fallback imediato para Ollama
        │
        ├─ POST https://generativelanguage.googleapis.com/v1beta/models/...
        │   Timeout: 60s (padrão) ou --timeout N
        │
        ├─ Se rate limit ou timeout:
        │   → fallback para Ollama (se configurado)
        │
        └─ Se Ollama também não disponível:
            → review parcial (apenas rule_engine + metrics)
            → log: "[guardian] IA indisponível, análise parcial"
```

### Fallback automático

```
Gemini chamado
        │
        ├─ OK ──────────────────────────────▶ usa resultado Gemini
        │
        ├─ GEMINI_API_KEY não definida ─────▶ tenta Ollama
        │
        ├─ Rate limit (429) ────────────────▶ tenta Ollama
        │
        ├─ Timeout ─────────────────────────▶ tenta Ollama
        │
        └─ Ollama também falha ─────────────▶ review parcial (sem IA)
```

---

## Arquivos gerados em cada fluxo

| Contexto | HTML gerado | Onde |
|----------|-------------|------|
| `runner.py` (qualquer modo sem `--format json`) | `last-runner-report.html` | `.codeguardian/` |
| `runner.py --output caminho.html` | caminho especificado | caminho dado |
| Hook `pre-commit` | `last-commit-report.html` | `.codeguardian/` |
| Hook `pre-push` | `last-push-report.html` | `.codeguardian/` |
| `tests/run_tests.py` | `last-test-report.html` | `.codeguardian/` |
| `git commit` com pre-commit ok | trailer em cada commit | `git log` |

> A pasta `.codeguardian/` está no `.gitignore` — os relatórios são locais e não entram no repositório.

---

## Matriz comparativa

| Aspecto | `/code-review` (agente) | `runner.py` (terminal) | Git Hook (automático) |
|---------|-------------------------|------------------------|----------------------|
| **Gatilho** | Manual (`/code-review`) | Manual (`python runner.py`) | Automático (commit/push) |
| **IA usada** | O próprio agente (Claude, Q) | Gemini API ou Ollama | Apenas scripts (sem IA) |
| **Custo IA** | Zero (já pago na assinatura) | Gemini grátis / Ollama zero | Zero (sem IA) |
| **Velocidade** | ~30–60s (com análise IA) | ~10s (rules-only) / ~60s (com IA) | ~5–15s (rules-only) |
| **Funciona offline** | Sim (modelo local do agente) | Com Ollama | Sempre |
| **Plano de Correção** | Gerado pelo PASSO 7 da skill | Gerado automaticamente | Não (apenas bloqueio) |
| **HTML gerado** | Não (saída na conversa) | Sim (.codeguardian/) | Sim (.codeguardian/) |
| **Trailer no commit** | Não | Se `--summary-file` for passado | Sim (via prepare-commit-msg) |
| **Interativo** | Sim ("corrija o item 2") | Não | Não |
| **Bloqueia merge** | Não (apenas review) | Via exit code (CI) | Sim (bloqueia commit/push) |

---

## Sequência completa de um PR

Do início ao merge, todos os fluxos ativos:

```
1. Dev escreve código no IDE
        │
        ▼
2. /code-review (agente)  ← FEEDBACK IMEDIATO
   Scripts Python + análise do próprio Claude
   Dev vê Plano de Correção e corrige antes de commitar
        │
        ▼
3. git add Services/X.cs
   git commit -m "feat: ..."  ← BARREIRA 1
        │
   [pre-commit hook]
   Analisa staged files (rules-only, < 10s)
   ├── Blockers? → SIM → commit abortado → dev corrige
   └── Não → segue
        │
   [prepare-commit-msg hook]
   Injeta: "Guardian-Review: ✅ Passou | Score: 4 | ..."
        │
   commit gravado com trailer no histórico
        │
        ▼
4. git push origin feature/x  ← BARREIRA 2
        │
   [pre-push hook]
   Analisa diff completo do branch (rules-only)
   ├── Blockers? → SIM → push abortado → dev corrige
   └── Não → push executado
        │
        ▼
5. Abre PR no TFS  ← REVISOR VÊ
   Commits da PR listam os trailers Guardian-Review
   Revisor sabe que o dev rodou o guardian antes de enviar
        │
        ▼
6. (Opcional) Pipeline TFS
   runner.py --format json --base origin/main
   Análise completa com IA (Gemini ou Ollama)
   Bloqueia PR se houver critical/error
```

---

## Documentação relacionada

| Documento | Conteúdo |
|-----------|----------|
| [00-Inicio-Rapido.md](00-Inicio-Rapido.md) | Setup em 5 minutos |
| [07-Ollama-Setup.md](07-Ollama-Setup.md) | Instalação detalhada do Ollama |
| [11-Uso-ai-client.md](11-Uso-ai-client.md) | ai_client.py — provedores, config, fallback |
| [12-Trocar-Provedor-IA.md](12-Trocar-Provedor-IA.md) | Como mudar Gemini ↔ Ollama ↔ outros |
| [13-Runner-CLI.md](13-Runner-CLI.md) | Todos os flags do runner.py |
| [15-Git-Hooks.md](15-Git-Hooks.md) | Instalação e configuração dos hooks |
| [16-Fluxo-Desenvolvedor.md](16-Fluxo-Desenvolvedor.md) | Guia do dia a dia do desenvolvedor |
