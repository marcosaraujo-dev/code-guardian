# Code Review com GitHub Copilot

Como usar o Code Guardian integrado ao GitHub Copilot para revisar código C#.

---

## Pré-requisitos

| Requisito | Detalhe |
|-----------|---------|
| Plano GitHub | Copilot Pro, Pro+, Business ou Enterprise |
| VS Code | Versão estável (Agent Mode em breve) ou **VS Code Insiders** (já disponível) |
| Extensão | GitHub Copilot + GitHub Copilot Chat instalados e autenticados |
| Python | 3.11+ instalado (para rodar scripts de análise estática, opcional) |

> **Skills disponíveis em:** VS Code Insiders com Agent Mode, GitHub Copilot Coding Agent (via Issues), GitHub Copilot CLI.
> Suporte na versão estável do VS Code estará disponível em breve.

---

## Como Funciona

O Copilot lê automaticamente as instruções e skills do repositório em dois locais:

```
.github/
├── copilot-instructions.md      ← padrões e checklist (carregado em todo chat)
└── skills/code-review/
    ├── SKILL.md                 ← skill de code review (ativada por contexto)
    └── references/
        ├── rules.md             ← regras estáticas detalhadas
        └── ai-analysis.md      ← checklist de análise profunda
```

Não é necessária nenhuma configuração adicional — esses arquivos já estão no repositório.

---

## Opção 1 — Chat no VS Code (mais simples)

### Como usar

1. Abrir o arquivo `.cs` que deseja revisar no VS Code
2. Abrir o Copilot Chat (`Ctrl+Alt+I` ou ícone na barra lateral)
3. Digitar o comando:

```
@workspace /code-review
```

Ou de forma mais direta:

```
Faça um code review do arquivo aberto seguindo os padrões do projeto
```

```
Revise Services/PedidoService.cs verificando SQL Injection, async/await e Result Pattern
```

### Variações úteis

```
# Revisão focada em segurança
Faça um security review de Services/UserService.cs

# Revisão de um arquivo específico (com arquivo aberto no editor)
Revise este arquivo verificando anti-patterns WPF e MVVM

# Revisão antes de commitar
Quais problemas existem nos arquivos que modifiquei hoje?
```

> **Dica**: O Copilot Chat lê o arquivo aberto no editor automaticamente como contexto.
> Para arquivos grandes, selecione o trecho de código antes de abrir o chat.

---

## Opção 2 — Agent Mode no VS Code Insiders

O Agent Mode permite que o Copilot execute a skill `/code-review` de forma autônoma, lendo arquivos, rodando comandos e gerando o relatório completo.

### Pré-requisitos extras

- VS Code **Insiders** instalado: [insiders.vscode.dev](https://insiders.vscode.dev)
- Extensão GitHub Copilot no VS Code Insiders
- Agent Mode habilitado nas configurações

### Como habilitar o Agent Mode

1. No VS Code Insiders: `Ctrl+,` → buscar por `"copilot agent"`
2. Habilitar **"Enable Agent Mode"**
3. No Copilot Chat, trocar de "Ask" para **"Agent"** no dropdown

### Como usar

No painel do Copilot Chat em modo Agent:

```
/code-review
```

```
/code-review --staged
```

```
/code-review --file Services/PedidoService.cs
```

```
/code-review --rules-only
```

O Agent vai:
1. Detectar os arquivos `.cs` alterados
2. Tentar rodar os scripts Python (`runner.py`) se disponíveis
3. Ler e analisar cada arquivo
4. Gerar o relatório com Risk Score

---

## Opção 3 — GitHub Copilot Coding Agent (via Issues)

O Coding Agent executa tasks completas de forma autônoma, lendo skills do repositório.

### Pré-requisitos

- Plano **GitHub Copilot Business ou Enterprise**
- Repositório no GitHub.com
- Copilot habilitado nas configurações da organização

### Como usar

1. **Criar uma Issue** no repositório com o título:

```
Code Review: [nome do PR ou feature]
```

2. **Descrever o que revisar** no corpo da issue:

```markdown
Por favor, faça um code review dos seguintes arquivos alterados nesta feature:
- Services/PedidoService.cs
- ViewModels/PedidosViewModel.cs

Verificar especialmente:
- SQL Injection e segurança
- Uso correto do Result Pattern
- Padrões MVVM no ViewModel

Branch: feature/novo-pagamento
```

3. **Atribuir ao Copilot**: no painel direito da issue, em "Assignees", selecionar **@Copilot**

4. O Coding Agent vai:
   - Fazer checkout do branch indicado
   - Ler as skills do repositório (`.github/skills/` e `.claude/skills/`)
   - Executar o code review
   - Comentar na issue com o relatório completo

---

## Opção 4 — GitHub Copilot CLI

Para quem prefere o terminal.

### Instalação

```bash
# Instalar a CLI do GitHub
winget install GitHub.cli        # Windows
brew install gh                   # macOS

# Autenticar
gh auth login

# Instalar extensão Copilot
gh extension install github/gh-copilot
```

### Como usar

```bash
# Navegar até o repositório
cd /caminho/para/o/projeto

# Code review de arquivos alterados
gh copilot suggest "faça um code review dos arquivos .cs alterados vs origin/main seguindo os padrões do projeto"

# Code review de arquivo específico
gh copilot suggest "revise Services/PedidoService.cs verificando SQL Injection, Result Pattern e logging"
```

---

## Fluxo Recomendado no Dia a Dia

```
Você escreveu código
        ↓
(Opcional) Rodar análise estática no terminal:
python code_guardian/runner.py --rules-only --format text
        ↓
Copiar o resultado da análise estática
        ↓
No Copilot Chat, colar o resultado e pedir:
"Com base nesta análise estática, faça um code review aprofundado
 de Services/PedidoService.cs"
        ↓
Revisar as issues apontadas
        ↓
Corrigir e commitar
```

> **Por que rodar o script antes?** Os scripts Python detectam padrões em ~1 segundo com alta precisão.
> O Copilot pode então focar na análise de lógica mais profunda, sem perder tempo com padrões simples.

---

## Exemplo de Sessão de Chat

```
Desenvolvedor:
Faça um code review de Services/FuncionarioService.cs seguindo os padrões do projeto.
Foque em segurança, Result Pattern e logging.

Copilot:
# 🛡️ Code Review — FuncionarioService.cs

**Risk Score: 35 — 🔴 Alto Risco**

## Issues Encontradas

### 🔴 [CRITICAL] SQL Injection — Linha 42
**Problema**: Query construída por concatenação de string com parâmetro `cpf`.
**Código atual**:
  var query = $"SELECT * FROM Funcionarios WHERE Cpf = '{cpf}'";
**Correção**:
  var func = await _context.Funcionarios
      .Where(f => f.Cpf == cpf)
      .FirstOrDefaultAsync();

### 🟠 [ERROR] Result Pattern ignorado — Linha 78
**Problema**: Método retorna `FuncionarioDto` diretamente em vez de `Result<FuncionarioDto>`.
...

**Resumo**: 1 critical, 2 error, 3 warning
**Recomendação**: Corrigir SQL Injection e Result Pattern antes de mergear.
```

---

## Interpretando o Relatório

| Ícone | Nível | O que fazer |
|-------|-------|-------------|
| 🔴 Critical | SQL Injection, secrets, path traversal | **Corrigir agora — não mergear** |
| 🟠 Error | Result Pattern, deadlock, exception swallowing | **Corrigir antes do merge** |
| 🟡 Warning | Console.Write, método longo, magic number | Revisar — não bloqueia |
| 🔵 Info | N+1 potencial, TODO, oportunidade de melhoria | Opcional |

**Risk Score:**

| Score | Classificação | Ação |
|-------|--------------|------|
| 0–10 | ✅ Baixo Risco | PR pode ser aprovado |
| 11–30 | ⚠️ Risco Moderado | Review humano recomendado |
| 31–60 | 🔴 Alto Risco | Review humano obrigatório |
| > 60 | 🚫 Risco Crítico | Corrigir antes de abrir PR |

---

## Limitações Conhecidas

| Limitação | Impacto | Contorno |
|-----------|---------|----------|
| Agent Mode só no VS Code Insiders | Skill `/code-review` com execução autônoma ainda não na versão estável | Usar VS Code Insiders ou Chat Mode |
| Scripts Python podem não rodar | Copilot Chat não executa comandos no terminal | Rodar `runner.py` manualmente e colar o resultado no chat |
| Contexto de arquivos grandes | Arquivos com >500 linhas podem ser cortados | Selecionar o trecho relevante antes de abrir o chat |

---

## Documentação Relacionada

| Documento | Conteúdo |
|-----------|---------|
| [00-Inicio-Rapido.md](../00-Inicio-Rapido.md) | Visão geral do Code Guardian |
| [amazon-q.md](amazon-q.md) | Guia equivalente para Amazon Q |
| [16-Fluxo-Desenvolvedor.md](../16-Fluxo-Desenvolvedor.md) | Fluxo completo com Claude Code |
