# Como Trocar o Provedor de IA

O `ai_client.py` suporta 4 provedores. A troca é feita editando **uma única linha** no `config.json` — sem alterar nenhum código.

---

## Localização do arquivo de configuração

```text
code_guardian/config.json
```

---

## Estrutura do config.json

```json
{
  "ai": {
    "primary": "gemini",
    "fallback": "ollama",
    ...
  }
}
```

| Campo | Descrição |
| -------- | -------- |
| `primary` | Provedor principal — usado primeiro |
| `fallback` | Provedor de backup — usado se o primary falhar ou não estiver disponível |

Os valores possíveis para ambos: `gemini`, `claude`, `openai`, `ollama`, `none`.

---

## Provedores disponíveis

| Valor | Serviço | O que precisa |
| ----- | ------- | ------------- |
| `gemini` | Google Gemini | Variável `GEMINI_API_KEY` definida |
| `claude` | Anthropic Claude | Variável `ANTHROPIC_API_KEY` definida |
| `openai` | OpenAI ChatGPT | Variável `OPENAI_API_KEY` definida |
| `ollama` | Ollama local | Ollama instalado e rodando em `localhost:11434` |
| `none` | Sem fallback | — |

---

## Receitas prontas

### Usar Claude como primário, Ollama como fallback

```json
{
  "ai": {
    "primary": "claude",
    "fallback": "ollama"
  }
}
```

Definir a chave no terminal antes de usar:

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Linux / macOS
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

### Usar OpenAI como primário, Claude como fallback

```json
{
  "ai": {
    "primary": "openai",
    "fallback": "claude"
  }
}
```

```bash
$env:OPENAI_API_KEY    = "sk-..."
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

---

### Usar Ollama como primário (ambiente sem internet)

```json
{
  "ai": {
    "primary": "ollama",
    "fallback": "none"
  }
}
```

Nenhuma chave necessária. Ollama deve estar instalado:

```bash
ollama pull qwen2.5-coder:7b   # baixar modelo (uma vez)
ollama serve                   # iniciar se não estiver rodando
```

---

### Usar Gemini com fallback para Claude (sem Ollama)

```json
{
  "ai": {
    "primary": "gemini",
    "fallback": "claude"
  }
}
```

---

### Desabilitar IA completamente (só Rule Engine + Métricas)

```json
{
  "ai": {
    "primary": "none",
    "fallback": "none"
  }
}
```

---

## Trocar o modelo dentro do mesmo provedor

Cada provedor tem seu bloco de configuração. Para usar um modelo diferente, editar o campo `model`:

### Claude — trocar de Sonnet para Opus

```json
"claude": {
  "model": "claude-opus-4-6",
  "api_key_env": "ANTHROPIC_API_KEY",
  "max_tokens": 4096
}
```

### Gemini — usar versão mais rápida (menor custo de cota)

```json
"gemini": {
  "model": "gemini-1.5-flash",
  "api_key_env": "GEMINI_API_KEY"
}
```

### Ollama — trocar para modelo maior (requer 16 GB RAM)

```json
"ollama": {
  "base_url": "http://localhost:11434",
  "model": "qwen2.5-coder:14b",
  "timeout_seconds": 180
}
```

Modelos Ollama disponíveis para código:

| Modelo | Tamanho | RAM mínima | Qualidade |
| ------ | ------- | ---------- | --------- |
| `qwen2.5-coder:7b` | 4.7 GB | 8 GB | ⭐⭐⭐⭐ |
| `qwen2.5-coder:14b` | 9 GB | 16 GB | ⭐⭐⭐⭐⭐ |
| `codellama:7b` | 3.8 GB | 8 GB | ⭐⭐⭐ |
| `deepseek-coder-v2:16b` | 9 GB | 16 GB | ⭐⭐⭐⭐⭐ |

---

## Usar uma variável de ambiente diferente para a chave

Se a chave já está definida com outro nome no seu ambiente, editar `api_key_env`:

```json
"claude": {
  "model": "claude-sonnet-4-6",
  "api_key_env": "MINHA_CHAVE_CLAUDE",
  "max_tokens": 4096
}
```

O sistema vai ler `$env:MINHA_CHAVE_CLAUDE` em vez de `$env:ANTHROPIC_API_KEY`.

---

## Verificar qual provedor está ativo

```bash
python code_guardian/ai_client.py --list-providers
```

Saída exemplo:

```text
Provedores disponíveis: claude, ollama
```

Isso mostra quais provedores estão **prontos agora** (chave definida ou serviço rodando),
independente do que está configurado como `primary`/`fallback`.

---

## Fluxo completo de decisão

```text
Execução do ai_client.py
        ↓
Lê config.json → pega "primary" e "fallback"
        ↓
Testa se primary está disponível
  (chave definida? serviço respondendo?)
        ↓ SIM
Usa primary → retorna resultado
        ↓ NÃO
Testa se fallback está disponível
        ↓ SIM
Usa fallback → retorna resultado + aviso de fallback
        ↓ NÃO (ou fallback = "none")
Retorna None → Rule Engine continua sem análise de IA
```

---

## Dicas de escolha

| Situação | Recomendação |
| -------- | ------------ |
| Melhor qualidade de análise | `primary: "claude"` ou `"gemini"` |
| Código confidencial (não pode sair da empresa) | `primary: "ollama"`, `fallback: "none"` |
| Ambiente sem internet | `primary: "ollama"`, `fallback: "none"` |
| Cota do Gemini acabou | Trocar para `primary: "claude"` ou `"openai"` |
| Máquina sem RAM suficiente para Ollama | Usar apenas provedores em nuvem |
| CI/CD sem chaves de API | `primary: "none"`, `fallback: "none"` (só análise estática) |
