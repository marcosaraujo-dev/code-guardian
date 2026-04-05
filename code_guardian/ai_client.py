#!/usr/bin/env python3
"""
AI Client — cliente com fallback automático entre múltiplos provedores de IA.

Provedores suportados:
    - gemini   → Google Gemini API  (requer GEMINI_API_KEY)
    - claude   → Anthropic Claude   (requer ANTHROPIC_API_KEY)
    - openai   → OpenAI ChatGPT     (requer OPENAI_API_KEY)
    - ollama   → Ollama local       (requer Ollama rodando em localhost:11434)

Fluxo de fallback (configurável em config.json):
    primary → fallback → sem IA (Rule Engine continua funcionando)

Uso direto:
    python ai_client.py <arquivo.cs>
    python ai_client.py <arquivo.cs> --format json
    python ai_client.py --list-providers

Uso como módulo:
    from ai_client import AIClient
    client = AIClient()
    result = client.analyze(code)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path

# ── URLs das APIs ────────────────────────────────────────────────────────────
GEMINI_API_URL  = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
CLAUDE_API_URL  = "https://api.anthropic.com/v1/messages"
OPENAI_API_URL  = "https://api.openai.com/v1/chat/completions"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_HEALTH_URL = "http://localhost:11434/api/tags"

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
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

REVIEW_PROMPT = """Você é um especialista em code review de C#. Analise o código abaixo e identifique:

1. **Bugs de lógica** — NullReferenceException, race conditions, deadlocks async
2. **Problemas de segurança** — SQL Injection, secrets hardcoded, IDOR
3. **Performance** — N+1 queries, alocações desnecessárias, LINQ ineficiente
4. **Violações de Clean Code** — métodos longos, God Class, poor naming
5. **Violações de SOLID** — SRP, DIP, ISP
6. **Padrões ausentes** — Result<T> em services, logging em operações críticas

Para cada problema encontrado, informe:
- Linha aproximada
- Severidade: critical / error / warning / info
- Descrição clara do problema
- Sugestão de correção

Responda em português. Seja direto e específico.

Código para análise:
```csharp
{code}
```"""


@dataclass
class AIResult:
    provider: str
    model: str
    analysis: str
    elapsed_seconds: float
    is_fallback: bool = False
    warning: str = ""


def _load_config() -> dict:
    """Carrega config.json ou retorna o padrão."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CONFIG


def _save_default_config() -> None:
    """Cria config.json padrão se não existir."""
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)


def _http_post(url: str, payload: dict, timeout: int = 30, headers: dict | None = None) -> dict:
    """Executa POST HTTP retornando dict. Lança urllib.error.URLError em falha."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)

    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_get(url: str, timeout: int = 5) -> bool:
    """Verifica se URL está acessível. Retorna True/False."""
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


# ── Provedores ───────────────────────────────────────────────────────────────

class GeminiProvider:
    """Integração com Google Gemini API."""

    def __init__(self, config: dict):
        self.model = config.get("model", "gemini-1.5-pro")
        api_key_env = config.get("api_key_env", "GEMINI_API_KEY")
        self.api_key = os.environ.get(api_key_env, "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def analyze(self, prompt: str) -> str:
        url = GEMINI_API_URL.format(model=self.model, key=self.api_key)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096}
        }
        response = _http_post(url, payload, timeout=60)

        candidates = response.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini retornou resposta vazia")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("Gemini retornou conteúdo vazio")

        return parts[0].get("text", "").strip()


class ClaudeProvider:
    """Integração com Anthropic Claude API."""

    def __init__(self, config: dict):
        self.model = config.get("model", "claude-sonnet-4-6")
        self.max_tokens = config.get("max_tokens", 4096)
        api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
        self.api_key = os.environ.get(api_key_env, "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def analyze(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        response = _http_post(CLAUDE_API_URL, payload, timeout=60, headers=headers)

        content = response.get("content", [])
        if not content:
            raise ValueError("Claude retornou resposta vazia")

        text = content[0].get("text", "").strip()
        if not text:
            raise ValueError("Claude retornou conteúdo vazio")

        return text


class OpenAIProvider:
    """Integração com OpenAI API (ChatGPT)."""

    def __init__(self, config: dict):
        self.model = config.get("model", "gpt-4o")
        self.max_tokens = config.get("max_tokens", 4096)
        api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
        self.api_key = os.environ.get(api_key_env, "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def analyze(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}]
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = _http_post(OPENAI_API_URL, payload, timeout=60, headers=headers)

        choices = response.get("choices", [])
        if not choices:
            raise ValueError("OpenAI retornou resposta vazia")

        text = choices[0].get("message", {}).get("content", "").strip()
        if not text:
            raise ValueError("OpenAI retornou conteúdo vazio")

        return text


class OllamaProvider:
    """Integração com Ollama local (offline)."""

    def __init__(self, config: dict):
        base_url = config.get("base_url", "http://localhost:11434")
        self.chat_url = f"{base_url}/api/chat"
        self.health_url = f"{base_url}/api/tags"
        self.model = config.get("model", "qwen2.5-coder:7b")
        self.timeout = config.get("timeout_seconds", 120)

    def is_available(self) -> bool:
        return _http_get(self.health_url, timeout=3)

    def analyze(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2}
        }
        response = _http_post(self.chat_url, payload, timeout=self.timeout)

        content = response.get("message", {}).get("content", "").strip()
        if not content:
            raise ValueError("Ollama retornou resposta vazia")

        return content


# ── Cliente principal ────────────────────────────────────────────────────────

class AIClient:
    """
    Cliente de IA com fallback automático.

    Configuração em config.json:
        primary  → provedor principal  (gemini, claude, openai, ollama)
        fallback → provedor de backup  (qualquer um acima, ou "none")

    Ordem de execução: primary → fallback → retorna None
    """

    _PROVIDER_CLASSES = {
        "gemini": (GeminiProvider, "gemini"),
        "claude": (ClaudeProvider, "claude"),
        "openai": (OpenAIProvider, "openai"),
        "ollama": (OllamaProvider, "ollama"),
    }

    def __init__(self):
        _save_default_config()
        config = _load_config()
        ai_config = config.get("ai", DEFAULT_CONFIG["ai"])

        self.primary_name = ai_config.get("primary", "gemini")
        self.fallback_name = ai_config.get("fallback", "ollama")

        # Instanciar todos os provedores com suas configs
        self._providers: dict = {}
        for name, (cls, key) in self._PROVIDER_CLASSES.items():
            provider_config = ai_config.get(key, {})
            self._providers[name] = cls(provider_config)

    def _get_provider(self, name: str):
        return self._providers.get(name)

    def analyze(self, code: str, custom_prompt: str | None = None) -> AIResult | None:
        """
        Analisa código com o melhor provedor disponível.
        Retorna AIResult ou None se nenhum provedor disponível.
        """
        prompt = custom_prompt or REVIEW_PROMPT.format(code=code)

        primary = self._get_provider(self.primary_name)
        fallback = self._get_provider(self.fallback_name)

        if primary and primary.is_available():
            result = self._try_provider(primary, self.primary_name, prompt)
            if result:
                return result
            print(f"[guardian] {self.primary_name.capitalize()} falhou — tentando fallback...",
                  file=sys.stderr)

        if fallback and self.fallback_name != "none" and fallback.is_available():
            return self._try_provider(fallback, self.fallback_name, prompt, is_fallback=True)

        return None

    def _try_provider(self, provider, name: str, prompt: str, is_fallback: bool = False) -> AIResult | None:
        model = getattr(provider, "model", name)
        start = time.time()
        try:
            analysis = provider.analyze(prompt)
            elapsed = round(time.time() - start, 1)
            warning = f"⚠️  Usando {name} como fallback — provedor primário indisponível" if is_fallback else ""
            return AIResult(
                provider=name,
                model=model,
                analysis=analysis,
                elapsed_seconds=elapsed,
                is_fallback=is_fallback,
                warning=warning
            )
        except urllib.error.URLError:
            return None
        except Exception as exc:
            print(f"[guardian] Erro em {name}: {exc}", file=sys.stderr)
            return None

    def list_available(self) -> list[str]:
        """Retorna lista dos provedores disponíveis no momento."""
        return [name for name, p in self._providers.items() if p.is_available()]


# ── Formatação de saída ──────────────────────────────────────────────────────

def _format_text(result: AIResult | None, file_path: str) -> str:
    lines = [f"=== Análise de IA — {file_path} ===\n"]

    if result is None:
        lines.append("⚠️  Nenhum modelo de IA disponível")
        lines.append("Executando apenas Rule Engine e Métricas (sem análise de IA)")
        lines.append("")
        lines.append("Para habilitar, configure uma das opções abaixo em config.json:")
        lines.append("  • Gemini : definir GEMINI_API_KEY")
        lines.append("  • Claude : definir ANTHROPIC_API_KEY")
        lines.append("  • OpenAI : definir OPENAI_API_KEY")
        lines.append("  • Ollama : ollama pull qwen2.5-coder:7b")
        return "\n".join(lines)

    provider_label = f"{result.provider.capitalize()} ({result.model})"
    if result.is_fallback:
        provider_label += " [fallback]"

    lines.append(f"Provedor : {provider_label}")
    lines.append(f"Tempo    : {result.elapsed_seconds}s")
    if result.warning:
        lines.append(result.warning)
    lines.append("")
    lines.append(result.analysis)
    return "\n".join(lines)


def _format_json(result: AIResult | None, file_path: str) -> str:
    if result is None:
        output = {
            "file": file_path,
            "ai_available": False,
            "provider": None,
            "model": None,
            "analysis": None,
            "elapsed_seconds": 0,
            "warning": (
                "Nenhum modelo de IA disponível. "
                "Configure GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY ou instale o Ollama."
            )
        }
    else:
        output = {
            "file": file_path,
            "ai_available": True,
            "provider": result.provider,
            "model": result.model,
            "analysis": result.analysis,
            "elapsed_seconds": result.elapsed_seconds,
            "is_fallback": result.is_fallback,
            "warning": result.warning
        }
    return json.dumps(output, ensure_ascii=False, indent=2)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Análise de IA para arquivos C# — suporta Gemini, Claude, OpenAI e Ollama"
    )
    parser.add_argument("file", help="Arquivo .cs para analisar")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--list-providers", action="store_true",
                        help="Lista os provedores disponíveis e sai")
    args = parser.parse_args()

    client = AIClient()

    if args.list_providers:
        available = client.list_available()
        if available:
            print("Provedores disponíveis: " + ", ".join(available))
        else:
            print("Nenhum provedor de IA disponível.")
        return 0

    file_path = args.file
    try:
        with open(file_path, encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Erro: arquivo não encontrado: {file_path}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Erro ao ler arquivo: {exc}", file=sys.stderr)
        return 1

    # Feedback de progresso
    primary_name = client.primary_name
    primary_obj = client._get_provider(primary_name)
    if primary_obj and primary_obj.is_available():
        model = getattr(primary_obj, "model", primary_name)
        print(f"[guardian] Usando {primary_name.capitalize()} ({model}) para análise de IA...",
              file=sys.stderr)
    else:
        fallback_name = client.fallback_name
        fallback_obj = client._get_provider(fallback_name)
        if fallback_obj and fallback_name != "none" and fallback_obj.is_available():
            model = getattr(fallback_obj, "model", fallback_name)
            print(
                f"[guardian] {primary_name.capitalize()} indisponível — "
                f"usando {fallback_name.capitalize()} ({model})...",
                file=sys.stderr
            )
        else:
            print("[guardian] ⚠️  Nenhum modelo de IA disponível", file=sys.stderr)

    result = client.analyze(code)

    if result:
        print(f"[guardian] Análise concluída em {result.elapsed_seconds}s", file=sys.stderr)
        if result.warning:
            print(f"[guardian] {result.warning}", file=sys.stderr)

    if args.format == "json":
        print(_format_json(result, file_path))
    else:
        print(_format_text(result, file_path))

    return 0


if __name__ == "__main__":
    sys.exit(main())
