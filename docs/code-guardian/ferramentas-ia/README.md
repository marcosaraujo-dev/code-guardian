# Code Review com Ferramentas de IA

Como usar o Code Guardian com diferentes assistentes de IA.

---

## Comparativo Rápido

| Capacidade | Claude Code | GitHub Copilot | Amazon Q |
|-----------|:-----------:|:--------------:|:--------:|
| Executa scripts Python automaticamente | ✅ | ⚠️ Agent Mode (Insiders) | ❌ |
| Skill `/code-review` nativa | ✅ | ✅ (Agent Mode) | ❌ |
| Lê `.claude/skills/` | ✅ | ✅ | ❌ |
| Lê `.github/skills/` | ❌ | ✅ | ❌ |
| Lê `.amazonq/rules/` | ❌ | ❌ | ✅ |
| Análise de IA pelo chat | ✅ | ✅ | ✅ |
| Review automático em PR | Via TFS Pipeline | Via Coding Agent | Via CodeGuru |
| Plano gratuito disponível | ✅ (API key) | ❌ | ✅ (Free tier) |

---

## Escolhendo a Ferramenta

```
Usa Claude Code como IDE principal?
    └── SIM → Use /code-review (guia: ../16-Fluxo-Desenvolvedor.md)

Tem GitHub Copilot e quer skill automatizada?
    └── VS Code Insiders com Agent Mode → Use /code-review no Copilot
    └── VS Code estável → Use chat com contexto manual
    └── GitHub Issues → Use Copilot Coding Agent
    → Guia: github-copilot.md

Usa Amazon Q?
    └── Rodar runner.py no terminal → Colar resultado no chat Amazon Q
    → Guia: amazon-q.md

Quer o máximo de cobertura?
    └── runner.py (análise estática) + qualquer IA (análise profunda)
```

---

## Fluxo Universal (funciona com qualquer ferramenta)

```bash
# 1. Análise estática (1 segundo, sem IA)
python code_guardian/runner.py --staged --rules-only --format text

# 2. Colar saída no chat da sua ferramenta preferida e pedir análise aprofundada
```

Este fluxo funciona com Claude Code, GitHub Copilot Chat e Amazon Q — independente da ferramenta.

---

## Guias Detalhados

| Ferramenta | Documento |
|-----------|-----------|
| **GitHub Copilot** | [github-copilot.md](github-copilot.md) |
| **Amazon Q Developer** | [amazon-q.md](amazon-q.md) |
| **Claude Code** (referência) | [../16-Fluxo-Desenvolvedor.md](../16-Fluxo-Desenvolvedor.md) |
