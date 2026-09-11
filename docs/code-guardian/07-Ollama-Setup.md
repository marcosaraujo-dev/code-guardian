# Ollama — Modelo Local para Code Review

## O que é o Ollama — Explicação para quem nunca ouviu falar

Imagine que o ChatGPT ou o Claude são como **contratar um especialista que mora em outro país**: você manda sua pergunta pela internet, ele responde — mas você depende da conexão, paga por uso, e tudo o que você envia passa pelos servidores deles.

O Ollama é diferente: é como **contratar esse mesmo especialista para trabalhar dentro da sua empresa**, no seu próprio computador. Ele funciona 100% offline, seus dados nunca saem da máquina, e depois do download inicial é completamente gratuito.

```
                ┌─────────────────────────────────────────┐
                │  SEM Ollama (cloud)                      │
                │                                          │
                │  Seu código ──► Internet ──► Gemini/     │
                │                              Claude/GPT  │
                │                                          │
                │  ⚠️  Código sai da empresa               │
                │  ⚠️  Precisa de internet                 │
                │  ⚠️  Pode ter custo                      │
                └─────────────────────────────────────────┘

                ┌─────────────────────────────────────────┐
                │  COM Ollama (local)                      │
                │                                          │
                │  Seu código ──► Ollama ──► Resposta      │
                │               (na sua máquina)           │
                │                                          │
                │  ✅ Código nunca sai da máquina          │
                │  ✅ Funciona sem internet                │
                │  ✅ Gratuito após o download             │
                └─────────────────────────────────────────┘
```

---

## Ollama vs Claude vs Gemini — Qual usar?

| Situação | Melhor escolha | Por quê |
|----------|---------------|---------|
| Código confidencial que não pode sair da empresa | **Ollama** | Dados ficam 100% locais |
| Sem internet (home office sem VPN, avião, etc.) | **Ollama** | Funciona completamente offline |
| Quer a melhor análise possível, código não é sensível | **Claude/Gemini** | Modelos maiores, mais precisos |
| Análise ocasional, sem gastar cota de API | **Ollama** | Zero custo após download |
| Precisa resposta em menos de 10 segundos | **Claude/Gemini** | Infraestrutura otimizada na nuvem |
| Equipe sem acesso a APIs externas | **Ollama** | Funciona em redes corporativas fechadas |

> **Resumo simples**: Use Claude/Gemini quando puder e quiser a melhor qualidade. Use Ollama quando o código é confidencial, está offline, ou quer custo zero.

No Code Guardian, os dois coexistem — Gemini como primário, Ollama como fallback automático:

```
Análise solicitada
      ↓
Gemini disponível? → SIM → usa Gemini (melhor qualidade)
      ↓ NÃO
Ollama rodando?   → SIM → usa Ollama (local, gratuito)
      ↓ NÃO
Apenas Rule Engine (sem IA, mas ainda funcional)
```

---

## Por que os modelos Ollama são menores que o Claude?

Claude Sonnet tem ~175 bilhões de parâmetros e roda em centenas de servidores na nuvem. Os modelos Ollama rodam em **uma única máquina** — por isso os tamanhos práticos são menores (7B, 14B, 32B parâmetros). Mesmo assim, para tarefas específicas como análise de código C#, modelos de 14B treinados especialmente para código (`qwen2.5-coder`) chegam muito perto da qualidade dos grandes modelos.

---

## Requisitos de Hardware

| RAM disponível | Modelo recomendado | Qualidade para código | Velocidade |
|----------------|-------------------|----------------------|------------|
| 8 GB | `qwen2.5-coder:7b` | ⭐⭐⭐⭐ | ~30s por arquivo |
| 16 GB | `qwen2.5-coder:14b` | ⭐⭐⭐⭐⭐ | ~45s por arquivo |
| 16 GB (raciocínio) | `deepseek-r1:14b` | ⭐⭐⭐⭐⭐ | ~60s por arquivo |
| 16 GB (geral) | `glm4:latest` | ⭐⭐⭐⭐ | ~35s por arquivo |
| 32 GB+ | `qwen2.5-coder:32b` | ⭐⭐⭐⭐⭐ | ~90s por arquivo |
| GPU (VRAM 8GB+) | qualquer modelo acima | ⭐⭐⭐⭐⭐ | ~5s por arquivo |

> **Nota para 16 GB RAM**: `qwen2.5-coder:14b` é o ponto ideal — roda confortavelmente, usa ~11 GB em execução, deixando 5 GB livres para o sistema. O `qwen2.5-coder:32b` requer ~21 GB e pode usar swap (lento); só recomendado com GPU.

---

## Instalação

### Windows

1. Baixar o instalador em [ollama.com/download](https://ollama.com/download)
2. Executar o instalador (não precisa de permissão de admin)
3. O Ollama inicia automaticamente como serviço em background

Verificar se está rodando:
```bash
ollama --version
# ollama version is 0.x.x
```

### Linux / WSL

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### macOS

```bash
brew install ollama
ollama serve  # iniciar o serviço
```

---

## Modelos disponíveis — Download

### Para análise de código C# (recomendado)

```bash
# Melhor custo-benefício — 8 GB RAM (4.7 GB download)
ollama pull qwen2.5-coder:7b

# Alta qualidade — 16 GB RAM (9.0 GB download)  ← RECOMENDADO para 16 GB
ollama pull qwen2.5-coder:14b

# Máxima qualidade — 32 GB RAM ou GPU (19 GB download)
ollama pull qwen2.5-coder:32b
```

### Para análise e raciocínio profundo

```bash
# DeepSeek-R1 14B — raciocínio passo a passo, ótimo para bugs complexos
# 16 GB RAM (9.0 GB download)
ollama pull deepseek-r1:14b
```

**O que é o DeepSeek-R1?** É um modelo que "pensa em voz alta" antes de responder — raciocina sobre o problema em várias etapas antes de dar a resposta final. Para detectar bugs sutis e deadlocks, essa abordagem é superior à resposta direta.

### Para uso geral (desenvolvimento + análise)

```bash
# GLM-4 Flash — bom equilíbrio geral, rápido
# 16 GB RAM (~5 GB download)
ollama pull glm4:latest
```

**O que é o GLM-4?** É o modelo open-source da Zhipu AI (China), com boa compreensão de código e linguagem natural. O "Flash" é a variante otimizada para velocidade.

### Verificar modelos instalados

```bash
ollama list
# NAME                      SIZE    MODIFIED
# qwen2.5-coder:14b         9.0 GB  2 minutes ago
# deepseek-r1:14b           9.0 GB  5 minutes ago
# glm4:latest               5.5 GB  8 minutes ago
```

O download é feito uma única vez. Modelos ficam em `~/.ollama/models/`.

---

## Comparativo detalhado dos modelos

| Modelo | RAM runtime | Especialidade | Melhor para | Limitação |
|--------|------------|---------------|-------------|-----------|
| `qwen2.5-coder:7b` | ~6 GB | Código (treinado especificamente) | Review rápido, máquinas 8 GB | Menos preciso em lógica complexa |
| `qwen2.5-coder:14b` | ~11 GB | Código (versão maior) | Code review diário em 16 GB | Mais lento que 7b |
| `qwen2.5-coder:32b` | ~21 GB | Código (máxima qualidade) | Review detalhado, 32 GB ou GPU | Exige hardware mais potente |
| `deepseek-r1:14b` | ~11 GB | Raciocínio em cadeia | Bugs complexos, análise de fluxo | Mais lento (pensa antes de responder) |
| `glm4:latest` | ~5 GB | Geral (código + texto) | Uso misto: código e documentação | Menos especializado em C# |

### Quando usar cada um

```
Para Code Guardian (análise de código C#):
  8 GB RAM   → qwen2.5-coder:7b
  16 GB RAM  → qwen2.5-coder:14b  (primeira escolha)
             → deepseek-r1:14b    (segunda escolha, mais lento mas mais profundo)

Para desenvolvimento geral (documentação, perguntas, refatoração):
  16 GB RAM  → glm4:latest  (geral, rápido)
             → deepseek-r1:14b  (análise profunda)

Para máxima qualidade (sem restrição de RAM/GPU):
  → qwen2.5-coder:32b
```

> **Dica**: Não rode dois modelos ao mesmo tempo em 16 GB. Cada um usa ~9–11 GB. Alterne conforme a tarefa — o Ollama faz o swap automaticamente quando você chama um modelo diferente.

---

## Como o Ollama funciona internamente

Após a instalação, o Ollama expõe uma **API REST local** na porta `11434`:

```
http://localhost:11434
```

Ela é compatível com o formato OpenAI, facilitando a integração:

```python
# Exemplo de chamada direta
import requests

response = requests.post("http://localhost:11434/api/chat", json={
    "model": "qwen2.5-coder:14b",
    "messages": [
        {"role": "user", "content": "Analise este código C#: ..."}
    ],
    "stream": False
})

print(response.json()["message"]["content"])
```

---

## Configuração no Code Guardian

O arquivo de configuração fica em `code_guardian/config.json`:

```json
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
      "model": "qwen2.5-coder:14b",
      "timeout_seconds": 120
    }
  }
}
```

Para usar `deepseek-r1:14b` como modelo Ollama:

```json
"ollama": {
  "base_url": "http://localhost:11434",
  "model": "deepseek-r1:14b",
  "timeout_seconds": 180
}
```

> Use `timeout_seconds: 180` para o DeepSeek-R1 — ele raciocina antes de responder e pode demorar mais.

### Variável de ambiente para o Gemini

```bash
# Windows (PowerShell)
$env:GEMINI_API_KEY = "sua-chave-aqui"

# Windows (permanente — via Sistema > Variáveis de Ambiente)
# Ou no .env do projeto (não commitar)

# Linux / macOS
export GEMINI_API_KEY="sua-chave-aqui"
```

---

## Verificar se o Ollama está pronto

```bash
# Verificar se o serviço está rodando
curl http://localhost:11434/api/tags

# Testar o modelo manualmente
ollama run qwen2.5-coder:14b "Explique em uma linha o que é async/await em C#"

# Testar o DeepSeek-R1
ollama run deepseek-r1:14b "Qual é a diferença entre Task.Wait() e await em C#?"
```

---

## Comportamento no Code Guardian

### Com Gemini disponível (padrão)
```
[guardian] Usando Gemini 1.5 Pro para análise de IA...
[guardian] Análise concluída em 8.3s
```

### Com Ollama como fallback
```
[guardian] Gemini indisponível — usando Ollama (qwen2.5-coder:14b)...
[guardian] Análise concluída em 34.1s
[guardian] ⚠️  Modo offline — qualidade pode ser inferior ao Gemini
```

### Sem IA disponível
```
[guardian] ⚠️  Nenhum modelo de IA disponível
[guardian] Executando apenas Rule Engine e Métricas (sem análise de IA)
[guardian] Para habilitar IA local: ollama pull qwen2.5-coder:14b
```

---

## Uso exclusivo com Ollama (sem Gemini)

Para equipes sem acesso ao Gemini, é possível configurar o Ollama como primário:

```json
{
  "ai": {
    "primary": "ollama",
    "fallback": "none"
  }
}
```

---

## Comparativo Gemini vs Ollama para Code Review C#

| Critério | Gemini 1.5 Pro | qwen2.5-coder:14b | deepseek-r1:14b |
|----------|----------------|-------------------|-----------------|
| Qualidade de análise | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Detecção de bugs lógicos | Excelente | Boa | Muito boa |
| Compreensão de C# | Excelente | Muito boa | Boa |
| Velocidade | ~8s | ~45s | ~60–90s |
| Custo | Consome cota API | Gratuito | Gratuito |
| Funciona offline | Não | Sim | Sim |
| Dados saem da empresa | Sim | Não (dados locais) | Não (dados locais) |
| Setup necessário | Só API key | Instalação + download | Instalação + download |

> **Nota de privacidade**: se o código é confidencial e não pode sair da empresa,
> o Ollama é a opção correta — tudo processa localmente, nenhum dado é enviado para fora.

---

## Problemas comuns

### "connection refused" ao chamar localhost:11434
```bash
# Iniciar o serviço manualmente
ollama serve
```

### Modelo muito lento
- Verificar se outro processo está usando muita RAM
- Considerar usar um modelo menor (`qwen2.5-coder:7b` em vez de `qwen2.5-coder:14b`)
- Se tiver GPU NVIDIA: instalar CUDA drivers — Ollama detecta automaticamente

### Modelo não encontrado
```bash
ollama pull qwen2.5-coder:14b  # baixar novamente
ollama list                     # verificar o nome exato
```

### "pull model manifest: file does not exists"
O nome do modelo está incorreto. Usar apenas o tag oficial:
```bash
# ✅ Correto
ollama pull deepseek-r1:14b

# ❌ Incorreto (tag não existe)
ollama pull deepseek-r1:distill-qwen-14b
```

### Windows: Ollama não inicia como serviço
- Abrir "Serviços" do Windows → procurar "Ollama" → iniciar manualmente
- Ou executar `ollama serve` no terminal e deixar aberto

### qwen2.5-coder:32b muito lento em 16 GB
O modelo precisa de ~21 GB e em 16 GB usará swap de disco (10–20x mais lento). Opções:
- Usar `qwen2.5-coder:14b` que cabe confortavelmente
- Instalar mais RAM
- Usar GPU com 16 GB VRAM
