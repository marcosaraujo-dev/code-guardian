# Integração com TFS / Azure DevOps Pipeline

## Visão Geral

O Code Guardian pode ser executado automaticamente em **cada Pull Request** via pipeline do TFS (Azure DevOps), bloqueando o merge se houver issues críticas.

---

## Pré-requisitos

- Python 3.11+ disponível no agente de build
- Acesso ao repositório git no agente
- (Opcional) Variável de ambiente com chave de API de IA

---

## Pipeline YAML completo

Salvar em `azure-pipelines-code-guardian.yml` na raiz do repositório:

```yaml
# azure-pipelines-code-guardian.yml
# Code Guardian — Review automático de código C# em PRs

trigger: none  # Não executa em push direto

pr:
  branches:
    include:
      - main
      - master
      - develop

pool:
  vmImage: 'windows-latest'  # ou 'ubuntu-latest'

variables:
  PYTHON_VERSION: '3.11'
  GUARDIAN_SCRIPTS: 'code_guardian'

steps:
  # 1. Checkout com histórico completo (necessário para git diff)
  - checkout: self
    fetchDepth: 0
    displayName: 'Checkout com histórico git completo'

  # 2. Configurar Python
  - task: UsePythonVersion@0
    inputs:
      versionSpec: $(PYTHON_VERSION)
      addToPath: true
    displayName: 'Configurar Python $(PYTHON_VERSION)'

  # 3. Análise estática (Rule Engine + Métricas) — rápido, sem IA
  - script: |
      python $(GUARDIAN_SCRIPTS)/runner.py \
        --base origin/$(System.PullRequest.TargetBranch) \
        --rules-only \
        --format json \
        --fail-on error \
        > code-guardian-report.json
    displayName: 'Code Guardian — Análise Estática'
    continueOnError: false
    env:
      PYTHONIOENCODING: utf-8

  # 4. Publicar relatório JSON como artefato
  - task: PublishBuildArtifacts@1
    inputs:
      pathToPublish: 'code-guardian-report.json'
      artifactName: 'code-guardian-report'
    displayName: 'Publicar Relatório'
    condition: always()

  # 5. Exibir resumo no log
  - script: |
      python -c "
      import json, sys
      with open('code-guardian-report.json') as f:
          r = json.load(f)
      print(f'Risk Score: {r[\"risk_score\"]} — {r[\"risk_label\"]}')
      s = r['summary']
      print(f'Critical: {s[\"critical\"]} | Error: {s[\"error\"]} | Warning: {s[\"warning\"]} | Info: {s[\"info\"]}')
      sys.exit(1 if r['has_blockers'] else 0)
      "
    displayName: 'Exibir Resumo e Validar'
```

---

## Pipeline com análise de IA (Gemini)

Para habilitar análise de IA no pipeline, adicionar as variáveis de ambiente:

```yaml
steps:
  # ... (passos anteriores)

  # Análise completa com IA
  - script: |
      python $(GUARDIAN_SCRIPTS)/runner.py \
        --base origin/$(System.PullRequest.TargetBranch) \
        --format json \
        --fail-on error \
        > code-guardian-report.json
    displayName: 'Code Guardian — Análise Completa (com IA)'
    env:
      GEMINI_API_KEY: $(GEMINI_API_KEY)        # variável do TFS
      ANTHROPIC_API_KEY: $(ANTHROPIC_API_KEY)  # opcional
      PYTHONIOENCODING: utf-8
```

Para configurar a variável `GEMINI_API_KEY` no TFS:
1. Projeto → Pipelines → Library → + Variable Group
2. Adicionar `GEMINI_API_KEY` com o valor da chave
3. Marcar como **Secret** para não aparecer nos logs
4. Vincular o grupo de variáveis ao pipeline

---

## Branch Policy (bloqueio de merge)

Para bloquear merge automaticamente quando o Code Guardian encontrar issues:

1. **Projeto TFS → Repos → Branches → Políticas do branch `main`**
2. **+ Adicionar política de build**
3. Selecionar o pipeline `azure-pipelines-code-guardian.yml`
4. Configurar:
   - **Disparador**: Automático
   - **Política**: Obrigatório (bloqueia merge se falhar)
   - **Expiração**: Após o PR ser atualizado

---

## Configuração mínima (só análise estática, sem IA)

Para um início rápido sem chaves de API:

```yaml
trigger: none
pr:
  branches:
    include: ['*']

pool:
  vmImage: 'ubuntu-latest'

steps:
  - checkout: self
    fetchDepth: 0

  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'

  - script: |
      python code_guardian/runner.py \
        --rules-only \
        --severity error \
        --format json \
        --fail-on error
    displayName: 'Code Guardian'
    env:
      PYTHONIOENCODING: utf-8
```

---

## Variáveis de ambiente disponíveis no pipeline

| Variável | Provedor | Descrição |
|----------|----------|-----------|
| `GEMINI_API_KEY` | Google Gemini | Chave da API Gemini |
| `ANTHROPIC_API_KEY` | Claude | Chave da API Anthropic |
| `OPENAI_API_KEY` | OpenAI | Chave da API OpenAI |
| — | Ollama | Não precisa de chave (local) |

> O `ai_client.py` usa automaticamente o provedor disponível conforme `config.json`.
> Ver [12-Trocar-Provedor-IA.md](12-Trocar-Provedor-IA.md) para configurar o provedor preferido.

---

## Exit codes do runner.py no pipeline

| Exit code | Significado | Resultado no pipeline |
|-----------|-------------|----------------------|
| `0` | Sem bloqueadores | ✅ Build passa |
| `1` | Issues encontradas | ❌ Build falha → merge bloqueado |

O parâmetro `--fail-on` controla qual severidade dispara o exit 1:
- `--fail-on critical` → só bloqueia para critical
- `--fail-on error` → bloqueia para critical + error (padrão)
- `--fail-on warning` → bloqueia para qualquer issue >= warning

---

## Exemplo de log no pipeline

```
=== Code Guardian — Análise Estática ===

📁 Services/PedidoService.cs
  🔴 L42 [SQL_INJECTION_CONCAT] Possível SQL Injection: query por concatenação.
  🟠 L87 [TASK_RESULT_DEADLOCK] Task.Result pode causar deadlock. Use await.

Risk Score: 35 — 🔴 Alto Risco
Critical: 1 | Error: 1 | Warning: 2 | Info: 0

##[error]Script retornou exit code 1
```

---

## Documentação relacionada

| Documento | Conteúdo |
|-----------|----------|
| [13-Runner-CLI.md](13-Runner-CLI.md) | Parâmetros e saída do runner.py |
| [11-Uso-ai-client.md](11-Uso-ai-client.md) | Configurar provedor de IA |
| [12-Trocar-Provedor-IA.md](12-Trocar-Provedor-IA.md) | Trocar entre Gemini/Claude/Ollama |
