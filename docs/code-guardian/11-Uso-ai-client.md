# ai_client.py — Análise de IA com Fallback Automático

## O que faz

Envia o código para um modelo de IA e recebe uma análise detalhada em português.
Suporta **4 provedores** com **fallback automático** — tenta o primário configurado e, se indisponível, usa o backup.

```text
Provedor primário disponível? → SIM → usa primário
              ↓ NÃO
Provedor fallback disponível? → SIM → usa fallback
              ↓ NÃO
Retorna None (Rule Engine continua sem IA)
```

### Provedores suportados

| Provedor | Variável de ambiente | Modelo padrão | Requer internet |
|----------|---------------------|---------------|-----------------|
| `gemini` | `GEMINI_API_KEY` | gemini-1.5-pro | Sim |
| `claude` | `ANTHROPIC_API_KEY` | claude-sonnet-4-6 | Sim |
| `openai` | `OPENAI_API_KEY` | gpt-4o | Sim |
| `ollama` | Nenhuma | qwen2.5-coder:7b | **Não** |

---

## Configuração prévia

### Gemini (Google)

```bash
# Windows PowerShell (sessão atual)
$env:GEMINI_API_KEY = "AIza..."

# Windows PowerShell (permanente)
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "AIza...", "User")

# Linux / macOS
export GEMINI_API_KEY="AIza..."
```

Obter chave: [aistudio.google.com](https://aistudio.google.com) → Get API Key

### Claude (Anthropic)

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Linux / macOS
export ANTHROPIC_API_KEY="sk-ant-..."
```

Obter chave: [console.anthropic.com](https://console.anthropic.com)

### OpenAI (ChatGPT)

```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."

# Linux / macOS
export OPENAI_API_KEY="sk-..."
```

Obter chave: [platform.openai.com](https://platform.openai.com)

### Ollama (local, sem internet)

Ver [07-Ollama-Setup.md](07-Ollama-Setup.md) para instalação completa.

```bash
ollama pull qwen2.5-coder:7b   # 4.7 GB, baixar uma única vez
curl http://localhost:11434/api/tags  # verificar se está rodando
```

---

## Arquivo de configuração — `config.json`

Localização: `code_guardian/config.json`

Criado automaticamente na primeira execução. Editar para mudar o provedor ativo:

```json
{
  "ai": {
    "primary": "gemini",
    "fallback": "ollama",
    "gemini": {
      "model": "gemini-1.5-pro",
      "api_key_env": "GEMINI_API_KEY"
    },
    "claude": {
      "model": "claude-sonnet-4-6",
      "api_key_env": "ANTHROPIC_API_KEY",
      "max_tokens": 4096
    },
    "openai": {
      "model": "gpt-4o",
      "api_key_env": "OPENAI_API_KEY",
      "max_tokens": 4096
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "qwen2.5-coder:7b",
      "timeout_seconds": 120
    }
  }
}
```

### Combinações comuns de primary/fallback

```json
// Melhor qualidade com fallback local
{ "primary": "claude", "fallback": "ollama" }

// Só OpenAI, sem fallback
{ "primary": "openai", "fallback": "none" }

// Ambiente sem internet (só Ollama)
{ "primary": "ollama", "fallback": "none" }

// Claude primário, Gemini como backup
{ "primary": "claude", "fallback": "gemini" }
```

---

## Entrada

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `<arquivo.cs>` | caminho | Sim | Arquivo C# a analisar |
| `--format` | `json` \| `text` | Não (padrão: `text`) | Formato da saída |
| `--list-providers` | flag | Não | Lista provedores disponíveis e sai |

---

## Verificar provedores disponíveis

```bash
python code_guardian/ai_client.py --list-providers

# Saída exemplo:
# Provedores disponíveis: claude, ollama
```

---

## Saída — Formato `text`

### Com provedor primário (ex: Claude)

```text
[guardian] Usando Claude (claude-sonnet-4-6) para análise de IA...
[guardian] Análise concluída em 9.2s

=== Análise de IA — Services/UserService.cs ===

Provedor : Claude (claude-sonnet-4-6)
Tempo    : 9.2s

## Bugs de Lógica

**Linha 42** — Severidade: critical
SQL Injection detectado: a query está sendo construída por concatenação com request.Id.
...
```

### Com fallback (ex: Ollama quando Claude falhou)

```text
[guardian] Claude indisponível — usando Ollama (qwen2.5-coder:7b)...
[guardian] Análise concluída em 38.2s
[guardian] ⚠️  Usando ollama como fallback — provedor primário indisponível

=== Análise de IA — Services/UserService.cs ===

Provedor : Ollama (qwen2.5-coder:7b) [fallback]
Tempo    : 38.2s
⚠️  Usando ollama como fallback — provedor primário indisponível
...
```

### Sem nenhuma IA disponível

```text
[guardian] ⚠️  Nenhum modelo de IA disponível

=== Análise de IA — Services/UserService.cs ===

⚠️  Nenhum modelo de IA disponível
Executando apenas Rule Engine e Métricas (sem análise de IA)

Para habilitar, configure uma das opções abaixo em config.json:
  • Gemini : definir GEMINI_API_KEY
  • Claude : definir ANTHROPIC_API_KEY
  • OpenAI : definir OPENAI_API_KEY
  • Ollama : ollama pull qwen2.5-coder:7b
```

---

## Saída — Formato `json`

### Com IA disponível

```json
{
  "file": "Services/UserService.cs",
  "ai_available": true,
  "provider": "claude",
  "model": "claude-sonnet-4-6",
  "analysis": "## Bugs de Lógica\n\n**Linha 42** ...",
  "elapsed_seconds": 9.2,
  "is_fallback": false,
  "warning": ""
}
```

### Com fallback ativo

```json
{
  "file": "Services/UserService.cs",
  "ai_available": true,
  "provider": "ollama",
  "model": "qwen2.5-coder:7b",
  "analysis": "...",
  "elapsed_seconds": 38.2,
  "is_fallback": true,
  "warning": "⚠️  Usando ollama como fallback — provedor primário indisponível"
}
```

### Sem IA disponível

```json
{
  "file": "Services/UserService.cs",
  "ai_available": false,
  "provider": null,
  "model": null,
  "analysis": null,
  "elapsed_seconds": 0,
  "warning": "Nenhum modelo de IA disponível. Configure GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY ou instale o Ollama."
}
```

### Campos da resposta

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `file` | string | Caminho do arquivo analisado |
| `ai_available` | bool | `true` se algum provedor respondeu |
| `provider` | string \| null | `"gemini"`, `"claude"`, `"openai"`, `"ollama"` ou `null` |
| `model` | string \| null | Nome exato do modelo usado |
| `analysis` | string \| null | Texto da análise em markdown |
| `elapsed_seconds` | float | Tempo de resposta em segundos |
| `is_fallback` | bool | `true` se usou o provedor de backup |
| `warning` | string | Mensagem de aviso (vazia se tudo ok) |

---

## Exit codes

| Código | Condição |
|--------|----------|
| `0` | Sempre (mesmo sem IA disponível) |
| `1` | Arquivo não encontrado ou erro de leitura |

---

## Exemplos de uso

```bash
# Análise com saída no terminal
python code_guardian/ai_client.py Services/UserService.cs

# Saída JSON para integração
python code_guardian/ai_client.py Services/UserService.cs --format json

# Ver quais provedores estão prontos agora
python code_guardian/ai_client.py --list-providers

# Forçar uso do Claude (editar config.json antes)
# "primary": "claude", "fallback": "ollama"
python code_guardian/ai_client.py Services/UserService.cs
```

---

## Uso como módulo Python

```python
from .claude.scripts.code_guardian.ai_client import AIClient

client = AIClient()

# Ver o que está disponível
print(client.list_available())  # ["claude", "ollama"]

# Analisar com prompt padrão
with open("Services/UserService.cs") as f:
    code = f.read()

result = client.analyze(code)

if result is None:
    print("Nenhuma IA disponível")
elif result.is_fallback:
    print(f"Fallback: {result.provider} ({result.model})")
else:
    print(f"{result.provider} respondeu em {result.elapsed_seconds}s")

print(result.analysis)

# Prompt customizado (ex: só segurança)
prompt = "Analise APENAS vulnerabilidades de segurança neste código C#:\n```csharp\n" + code + "\n```"
result = client.analyze(code, custom_prompt=prompt)
```

---

## Comparativo dos provedores

| Critério              | Gemini 1.5 Pro    | Claude Sonnet   | GPT-4o      | Ollama qwen 7b |
| --------------------- | ----------------- | --------------- | ----------- | -------------- |
| Qualidade para C#     | ⭐⭐⭐⭐⭐        | ⭐⭐⭐⭐⭐      | ⭐⭐⭐⭐⭐  | ⭐⭐⭐⭐       |
| Velocidade            | ~8s               | ~9s             | ~10s        | ~30-60s        |
| Custo                 | Free (com limite) | Pago            | Pago        | Grátis         |
| Funciona offline      | Não               | Não             | Não         | **Sim**        |
| Dados saem da empresa | Sim (Google)      | Sim (Anthropic) | Sim (OpenAI)| **Não**        |
| Contexto máximo       | 1M tokens         | 200K tokens     | 128K tokens | ~8K tokens     |

> Para código **confidencial**: usar **Ollama** — nada sai da máquina.
> Para melhor **qualidade de análise**: usar **Claude** ou **Gemini**.
