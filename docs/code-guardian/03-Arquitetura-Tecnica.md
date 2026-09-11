# Arquitetura Técnica - Code Guardian

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        CODE GUARDIAN                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    PRESENTATION LAYER                     │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │  CLI (Local) │  │ TFS Reporter │  │ HTML Reporter  │  │   │
│  │  │  Terminal    │  │ PR Comments  │  │ (futuro)       │  │   │
│  │  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │   │
│  └─────────┼────────────────┼──────────────────┼────────────┘   │
│            └────────────────┼──────────────────┘                │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   APPLICATION LAYER                       │   │
│  │                                                           │   │
│  │  ┌──────────────────────────────────────────────────┐    │   │
│  │  │              ReviewOrchestrator                   │    │   │
│  │  │  (coordena fluxo, gerencia config, timeout)      │    │   │
│  │  └──────────────────────┬───────────────────────────┘    │   │
│  │                         │                                 │   │
│  │  ┌─────────────┐  ┌────▼─────┐  ┌──────────────────┐    │   │
│  │  │ ConfigLoader │  │ Pipeline │  │ IssueAggregator  │    │   │
│  │  │             │  │ Manager  │  │ (deduplica, rank) │    │   │
│  │  └─────────────┘  └──────────┘  └──────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │                    ANALYZER LAYER                         │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │ Rule Engine  │  │ Roslyn       │  │  AI Engine     │  │   │
│  │  │             │  │ Integration  │  │                │  │   │
│  │  │ •built-in   │  │ •dotnet build│  │ ┌────────────┐ │  │   │
│  │  │ •custom     │  │ •analyzers   │  │ │Logic Agent │ │  │   │
│  │  │ •regex      │  │ •parse MSBld │  │ │Security Ag.│ │  │   │
│  │  │             │  │              │  │ │Perf Agent  │ │  │   │
│  │  └──────┬──────┘  └──────┬───────┘  │ └────────────┘ │  │   │
│  │         │                │          └───────┬────────┘  │   │
│  └─────────┼────────────────┼──────────────────┼────────────┘   │
│            └────────────────┼──────────────────┘                │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  INFRASTRUCTURE LAYER                     │   │
│  │                                                           │   │
│  │  ┌──────────┐  ┌───────────┐  ┌────────┐  ┌──────────┐  │   │
│  │  │ Git Diff  │  │ AI Client │  │ TFS    │  │ History  │  │   │
│  │  │ Parser    │  │ (Gemini/  │  │ Client │  │ Store    │  │   │
│  │  │           │  │  Ollama)  │  │ (API)  │  │ (SQLite) │  │   │
│  │  └──────────┘  └───────────┘  └────────┘  └──────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Estrutura de Pastas do Projeto

```
code-guardian/
│
├── pyproject.toml                # Configuração do pacote Python
├── README.md                     # Documentação
├── setup.py                      # Instalação
│
├── code_guardian/                 # Pacote principal
│   ├── __init__.py
│   ├── __main__.py               # Entry point (python -m code_guardian)
│   │
│   ├── cli/                      # PRESENTATION - CLI
│   │   ├── __init__.py
│   │   ├── main.py               # Comandos CLI (click/typer)
│   │   ├── formatter.py          # Output colorido no terminal
│   │   └── hooks.py              # Git hooks install/uninstall
│   │
│   ├── core/                     # APPLICATION - Orquestração
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # ReviewOrchestrator
│   │   ├── config.py             # ConfigLoader
│   │   ├── aggregator.py         # IssueAggregator
│   │   ├── models.py             # Issue, ReviewResult, RiskScore
│   │   └── pipeline.py           # PipelineManager
│   │
│   ├── analyzers/                # ANALYZER - Engines de análise
│   │   ├── __init__.py
│   │   ├── base.py               # IAnalyzer (interface base)
│   │   ├── rule_engine.py        # Rule Engine
│   │   ├── roslyn.py             # Roslyn Integration
│   │   └── ai/                   # AI Engine
│   │       ├── __init__.py
│   │       ├── ai_engine.py      # Orquestrador dos agentes
│   │       ├── logic_agent.py    # Logic Agent
│   │       ├── security_agent.py # Security Agent
│   │       ├── perf_agent.py     # Performance Agent
│   │       └── prompts/          # Templates de prompt
│   │           ├── logic.txt
│   │           ├── security.txt
│   │           └── performance.txt
│   │
│   ├── infrastructure/           # INFRASTRUCTURE - Integrações
│   │   ├── __init__.py
│   │   ├── git_parser.py         # Git Diff Parser
│   │   ├── ai_client.py          # Client abstrato para IA
│   │   ├── ai_client.py      # Google Gemini
│   │   ├── ollama_client.py      # Ollama local
│   │   ├── tfs_client.py         # Azure DevOps API
│   │   └── history_store.py      # SQLite storage
│   │
│   ├── reporters/                # PRESENTATION - Output
│   │   ├── __init__.py
│   │   ├── base.py               # IReporter (interface base)
│   │   ├── console_reporter.py   # Output no terminal
│   │   ├── tfs_reporter.py       # Comentários na PR
│   │   └── html_reporter.py      # Relatório HTML
│   │
│   └── rules/                    # Regras built-in
│       ├── __init__.py
│       ├── builtin_rules.yml     # Regras padrão
│       └── csharp_rules.yml      # Regras específicas C#
│
├── templates/                    # Templates
│   ├── code-guardian.yml         # Config padrão
│   ├── pipeline-azure-devops.yml # Pipeline TFS
│   └── pre-push-hook.sh          # Git hook
│
├── tests/                        # Testes
│   ├── unit/
│   │   ├── test_rule_engine.py
│   │   ├── test_git_parser.py
│   │   ├── test_aggregator.py
│   │   └── test_ai_engine.py
│   ├── integration/
│   │   ├── test_ai_client.py
│   │   ├── test_tfs_client.py
│   │   └── test_e2e_review.py
│   └── fixtures/                 # Dados de teste
│       ├── sample_diff.txt
│       ├── sample_cs_files/
│       └── expected_issues.json
│
└── docs/                         # Documentação
    ├── setup.md
    ├── configuration.md
    ├── tfs-integration.md
    └── adding-rules.md
```

---

## Modelos de Dados

### Issue (resultado de análise)

```python
@dataclass
class Issue:
    """Representa um problema encontrado no código."""
    id: str                          # UUID único
    file: str                        # Caminho do arquivo
    line: int                        # Número da linha
    severity: Severity               # critical | error | warning | info
    category: str                    # NullReference, SQLInjection, etc.
    message: str                     # Descrição do problema
    suggestion: str | None           # Sugestão de correção
    source: AnalyzerSource           # rule_engine | roslyn | ai_logic | ai_security | ai_perf
    rule_id: str | None              # ID da regra (rule engine)
    confidence: float                # 0.0 a 1.0 (confiança da IA)

class Severity(Enum):
    CRITICAL = "critical"   # Bloqueia sempre
    ERROR = "error"         # Bloqueia por padrão
    WARNING = "warning"     # Não bloqueia por padrão
    INFO = "info"           # Informativo

class AnalyzerSource(Enum):
    RULE_ENGINE = "rule_engine"
    ROSLYN = "roslyn"
    AI_LOGIC = "ai_logic"
    AI_SECURITY = "ai_security"
    AI_PERFORMANCE = "ai_performance"
```

### ReviewResult (resultado consolidado)

```python
@dataclass
class ReviewResult:
    """Resultado consolidado de um review."""
    issues: list[Issue]
    risk_score: RiskScore
    files_analyzed: int
    lines_changed: int
    execution_time_ms: int
    analyzers_used: list[str]
    metadata: ReviewMetadata

@dataclass
class RiskScore:
    """Score de risco da PR."""
    value: int                       # 0-100+
    label: str                       # Baixo, Moderado, Alto, Crítico
    breakdown: dict[Severity, int]   # {critical: 1, error: 3, ...}

    @staticmethod
    def calculate(issues: list[Issue]) -> "RiskScore":
        weights = {
            Severity.CRITICAL: 25,
            Severity.ERROR: 10,
            Severity.WARNING: 3,
            Severity.INFO: 1
        }
        value = sum(weights[i.severity] for i in issues)
        # ...classificar
```

### FileChange (diff parseado)

```python
@dataclass
class FileChange:
    """Representa um arquivo alterado no diff."""
    file_path: str
    changes: list[LineChange]

@dataclass
class LineChange:
    """Representa uma linha alterada."""
    line_number: int                 # Número da linha no arquivo destino
    content: str                     # Conteúdo da linha
    change_type: ChangeType          # added | modified | deleted
    context_before: list[str]        # Linhas de contexto antes
    context_after: list[str]         # Linhas de contexto depois
```

### Config

```python
@dataclass
class GuardianConfig:
    """Configuração do Code Guardian."""
    version: str
    ai: AIConfig
    files: FileFilterConfig
    analyzers: AnalyzersConfig
    blocking: BlockingConfig
    rules: list[CustomRule]
    tfs: TFSConfig | None

@dataclass
class AIConfig:
    provider: str               # gemini | ollama | openai
    model: str                  # modelo específico
    fallback: str | None        # provider fallback
    ollama_model: str | None
    temperature: float          # 0.0 a 1.0
    max_tokens: int
    api_key: str | None         # resolvido de env var ou config
```

---

## Interfaces (Contratos)

### IAnalyzer

```python
from abc import ABC, abstractmethod

class IAnalyzer(ABC):
    """Interface base para todos os analyzers."""

    @abstractmethod
    def name(self) -> str:
        """Nome do analyzer."""
        ...

    @abstractmethod
    async def analyze(
        self,
        changes: list[FileChange],
        config: GuardianConfig
    ) -> list[Issue]:
        """Analisa os arquivos alterados e retorna issues."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o analyzer pode ser executado."""
        ...
```

### IAIClient

```python
class IAIClient(ABC):
    """Interface para clientes de IA."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096
    ) -> str:
        """Envia prompt para o modelo e retorna resposta."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o cliente está acessível."""
        ...
```

### IReporter

```python
class IReporter(ABC):
    """Interface para reportar resultados."""

    @abstractmethod
    async def report(self, result: ReviewResult) -> None:
        """Publica o resultado do review."""
        ...
```

---

## Fluxo de Execução Detalhado

### Fluxo Local (CLI)

```
Desenvolvedor executa: code-guardian review
                         │
                         ▼
                  ┌──────────────┐
                  │ CLI Parser   │  Parseia argumentos (--staged, --file, etc.)
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ ConfigLoader │  Carrega .code-guardian.yml + ~/.code-guardian/config.yml
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Git Parser   │  Extrai diff (staged ou branch)
                  │              │  Filtra por extensão (.cs)
                  └──────┬───────┘
                         │
                         ▼ list[FileChange]
                  ┌──────────────┐
                  │ Orchestrator │
                  │              │─┐
                  └──────────────┘ │
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
       ┌──────▼──────┐    ┌───────▼──────┐    ┌────────▼────────┐
       │ Rule Engine │    │ Roslyn       │    │ AI Engine       │
       │ (sync, <1s) │    │ (dotnet build│    │ (async, ~20s)   │
       │             │    │  ~10-30s)    │    │                 │
       └──────┬──────┘    └───────┬──────┘    │ ┌─────────────┐│
              │                   │           │ │Logic Agent  ││
              │                   │           │ │Security Ag. ││
              │                   │           │ │Perf Agent   ││
              │                   │           │ └──────┬──────┘│
              │                   │           └────────┼───────┘
              │                   │                    │
              └───────────────────┼────────────────────┘
                                  │
                                  ▼ list[Issue] (de cada analyzer)
                         ┌──────────────┐
                         │ Aggregator   │  Deduplica, ordena, calcula score
                         └──────┬───────┘
                                │
                                ▼ ReviewResult
                         ┌──────────────┐
                         │ Console      │  Formata e exibe no terminal
                         │ Reporter     │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │ History      │  Salva resultado (opcional)
                         │ Store        │
                         └──────────────┘
                                │
                                ▼
                         Exit code (0 ou 1)
```

### Fluxo TFS (Pipeline)

```
PR criada no TFS
       │
       ▼
Pipeline dispara (Branch Policy > Build Validation)
       │
       ▼
┌────────────────────────────────────────────┐
│ Pipeline YAML                               │
│                                             │
│  1. checkout: self (fetchDepth: 0)          │
│  2. UsePythonVersion@0 (3.11+)             │
│  3. pip install code-guardian               │
│  4. python -m code_guardian.runner          │
│     --mode tfs                              │
│     --base-branch origin/main               │
│     --output tfs                            │
│                                             │
│  Variáveis de ambiente:                     │
│  • SYSTEM_PULLREQUEST_PULLREQUESTID         │
│  • SYSTEM_TEAMFOUNDATIONCOLLECTIONURI       │
│  • BUILD_REPOSITORY_ID                      │
│  • SYSTEM_ACCESSTOKEN (Build Service)       │
│  • CODE_GUARDIAN_API_KEY (Gemini)            │
└─────────────────┬──────────────────────────┘
                  │
                  ▼
           ┌──────────────┐
           │ ReviewRunner  │  (entry point para pipeline)
           │ (TFS mode)   │
           └──────┬───────┘
                  │
                  ▼ (mesmo engine do CLI)
           ┌──────────────┐
           │ Orchestrator │  Executa analyzers
           └──────┬───────┘
                  │
                  ▼ ReviewResult
           ┌──────────────┐
           │ TFS Reporter │
           │              │
           │ 1. Posta resumo na PR (comentário geral)
           │ 2. Posta issue em cada linha (threadContext)
           │ 3. Atualiza status (succeeded/failed)
           │ 4. Seta Risk Score como tag
           └──────────────┘
```

---

## Integração com Gemini

### Client Gemini

```python
import google.generativeai as genai

class GeminiClient(IAIClient):
    """Client para Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=4096,
                response_mime_type="application/json"  # Força JSON
            )
        )

    async def complete(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "user", "parts": [system_prompt]})
            messages.append({"role": "model", "parts": ["Entendido. Vou analisar conforme instruído."]})

        messages.append({"role": "user", "parts": [prompt]})

        response = await self._model.generate_content_async(messages)
        return response.text

    def is_available(self) -> bool:
        try:
            # Teste rápido de conectividade
            genai.list_models()
            return True
        except Exception:
            return False
```

### Client Ollama (Local)

```python
import httpx

class OllamaClient(IAIClient):
    """Client para Ollama (execução local, sem internet)."""

    def __init__(self, model: str = "deepseek-coder-v2", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url

    async def complete(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "system": system_prompt or "",
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.1),
                        "num_predict": kwargs.get("max_tokens", 4096)
                    }
                },
                timeout=120.0
            )
            return response.json()["response"]

    def is_available(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self._base_url}/api/tags", timeout=5.0)
            return r.status_code == 200
        except Exception:
            return False
```

---

## Pipeline YAML de Referência (TFS/Azure DevOps)

```yaml
# azure-pipelines-code-guardian.yml

trigger: none  # Não dispara em push

pr:
  branches:
    include:
      - main
      - develop
  paths:
    include:
      - 'src/**/*.cs'
    exclude:
      - '**/Migrations/**'

pool:
  vmImage: 'windows-latest'  # ou 'ubuntu-latest'

variables:
  - name: CODE_GUARDIAN_API_KEY
    value: $(GEMINI_API_KEY)   # Variável secreta configurada no pipeline

steps:
  # 1. Checkout completo (precisa do histórico para diff)
  - checkout: self
    fetchDepth: 0
    displayName: 'Checkout completo'

  # 2. Instalar Python
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'
    displayName: 'Instalar Python 3.11'

  # 3. Instalar Code Guardian
  - script: |
      pip install code-guardian
    displayName: 'Instalar Code Guardian'

  # 4. Executar Review
  - script: |
      python -m code_guardian.runner \
        --mode tfs \
        --base-branch origin/main
    displayName: 'Code Guardian - AI Review'
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)
      CODE_GUARDIAN_API_KEY: $(GEMINI_API_KEY)

  # 5. Publicar resultado como artefato (opcional)
  - task: PublishBuildArtifacts@1
    condition: always()
    inputs:
      pathToPublish: '$(System.DefaultWorkingDirectory)/code-guardian-report.json'
      artifactName: 'CodeGuardianReport'
    displayName: 'Publicar relatório'
```

---

## Modelo de Execução dos Agentes de IA

### Estratégia de Prompt

Cada agente recebe:
1. **System Prompt**: Define o papel e formato de resposta
2. **Diff Content**: Apenas as linhas alteradas com contexto
3. **File Context**: Informações sobre o arquivo (namespace, classe, imports)

### Otimizações para Reduzir Custo/Latência

| Técnica | Descrição | Economia |
|---------|-----------|----------|
| **Diff-only** | Enviar apenas linhas alteradas, não arquivo inteiro | ~80% tokens |
| **Batching** | Agrupar arquivos pequenos em um único prompt | ~50% chamadas |
| **Cache** | Não re-analisar arquivos não alterados entre runs | ~60% chamadas |
| **Short-circuit** | Se Rule Engine encontra critical, pular AI para esse arquivo | ~30% chamadas |
| **JSON mode** | Forçar resposta em JSON (Gemini suporta nativamente) | Elimina parsing errors |
| **Low temperature** | temperature=0.1 para consistência | Reduz variabilidade |

### Tratamento de Erros da IA

```python
async def _call_ai_with_retry(self, prompt: str) -> list[Issue]:
    """Chama IA com retry e fallback."""
    for attempt in range(3):
        try:
            response = await self._primary_client.complete(prompt)
            return self._parse_response(response)
        except RateLimitError:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except (TimeoutError, ConnectionError):
            if self._fallback_client and self._fallback_client.is_available():
                response = await self._fallback_client.complete(prompt)
                return self._parse_response(response)
            break
        except JSONDecodeError:
            # IA retornou texto inválido, tentar com prompt mais restritivo
            prompt = self._add_json_enforcement(prompt)
            continue

    # Se tudo falhar, retorna vazio (graceful degradation)
    logger.warning("AI indisponível. Continuando com Rule Engine apenas.")
    return []
```

---

## Segurança

### Código-fonte nunca deve sair da rede interna

| Cenário | Solução |
|---------|---------|
| Gemini corporativo | API via VPN, dados não retidos pela Google |
| Ollama local | Roda na máquina, zero rede externa |
| TFS on-premises | Pipeline roda no agent interno |
| Secrets | API keys via variáveis de ambiente, nunca no código |

### Dados Sensíveis

- O diff pode conter connection strings, tokens → sanitizar antes de enviar para IA
- Implementar `SensitiveDataFilter` que remove padrões de secrets do diff antes de enviar

```python
class SensitiveDataFilter:
    PATTERNS = [
        r'password\s*=\s*"[^"]*"',
        r'connectionString\s*=\s*"[^"]*"',
        r'apiKey\s*=\s*"[^"]*"',
        r'Bearer\s+[A-Za-z0-9\-._~+/]+=*',
    ]

    def sanitize(self, content: str) -> str:
        for pattern in self.PATTERNS:
            content = re.sub(pattern, '[REDACTED]', content, flags=re.IGNORECASE)
        return content
```

---

## Dependências Python

```
# requirements.txt / pyproject.toml

# Core
click>=8.0           # CLI framework (ou typer)
pyyaml>=6.0          # Parsing YAML config
pydantic>=2.0        # Validação de modelos

# AI Clients
google-generativeai>=0.5  # Gemini SDK
httpx>=0.27              # HTTP async (Ollama)

# Git
gitpython>=3.1       # Git operations (alternativa a subprocess)

# TFS/Azure DevOps
requests>=2.31       # HTTP para API Azure DevOps

# Storage
aiosqlite>=0.20      # SQLite async para histórico

# CLI Output
rich>=13.0           # Terminal colorido e formatado

# Dev/Test
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=5.0
```

---

## Alternativas e Comparações de Modelos

### Para uso com licença Gemini corporativa

| Modelo | Velocidade | Qualidade Code Review | Custo | Recomendação |
|--------|-----------|----------------------|-------|-------------|
| **Gemini 2.0 Flash** | Muito rápido | Boa | Baixo | **Usar para MVP** |
| **Gemini 2.0 Pro** | Médio | Excelente | Médio | Usar para reviews críticos |
| **Gemini 1.5 Flash** | Rápido | Boa | Baixo | Alternativa estável |

### Para uso local (Ollama)

| Modelo | RAM Necessária | Qualidade | Recomendação |
|--------|---------------|-----------|-------------|
| **DeepSeek Coder V2** | 8GB+ | Muito boa para código | **Recomendado** |
| **CodeLlama 34B** | 20GB+ | Boa | Se tiver GPU |
| **Llama 3.1 8B** | 6GB+ | Razoável | Máquinas limitadas |
| **Qwen2.5 Coder 7B** | 6GB+ | Boa | Alternativa leve |

### Para uso futuro (outros providers)

| Provider | Modelo | Qualidade | Consideração |
|----------|--------|-----------|-------------|
| Anthropic | Claude Sonnet 4 | Excelente | Se licença futura |
| OpenAI | GPT-4o mini | Boa | Custo-benefício |
| Azure OpenAI | GPT-4o | Excelente | Se já tem Azure |
