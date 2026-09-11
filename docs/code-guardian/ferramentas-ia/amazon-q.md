# Code Review com Amazon Q Developer

Como usar o Code Guardian integrado ao Amazon Q Developer para revisar código C#.

---

## Pré-requisitos

| Requisito | Detalhe |
|-----------|---------|
| Conta AWS | Com Amazon Q Developer habilitado (plano Free ou Pro) |
| IDE | VS Code com extensão Amazon Q, ou JetBrains (IntelliJ, Rider), ou Visual Studio |
| Python | 3.11+ instalado (para rodar scripts de análise estática, opcional) |
| AWS CLI | Configurado com credenciais válidas (para planos Pro) |

### Instalação da extensão

**VS Code:**
1. Abrir extensões (`Ctrl+Shift+X`)
2. Buscar **"Amazon Q"**
3. Instalar **Amazon Q** (publisher: AWS)
4. Fazer login: clicar no ícone Amazon Q na barra lateral → "Sign in"

**Visual Studio:**
1. Extensions → Manage Extensions
2. Buscar "AWS Toolkit"
3. Instalar e reiniciar

---

## Como Funciona

O Amazon Q lê automaticamente os arquivos de regras do diretório `.amazonq/rules/` no repositório:

```
.amazonq/rules/
├── code-review.md       ← processo de review + exemplos ERRADO/CORRETO
├── project-standards.md ← padrões do projeto (nomenclatura, SOLID, libs)
└── result-pattern.md    ← implementação completa do Result Pattern
```

Esses arquivos são carregados como **contexto de projeto** automaticamente quando você usa o Amazon Q dentro do repositório. Nenhuma configuração adicional é necessária.

---

## Opção 1 — Chat no VS Code / Visual Studio (mais simples)

### Como abrir

- **VS Code**: Clicar no ícone Amazon Q na barra lateral esquerda
- **Visual Studio**: View → Amazon Q

### Comandos de code review

```
/code-review
```

```
Faça um code review de Services/FuncionarioService.cs
```

```
Revise os arquivos que alterei hoje verificando SQL Injection, Result Pattern e MVVM
```

```
Analise este código seguindo os padrões do projeto e gere um relatório com Risk Score
```

### Variações por foco

```
# Segurança
Faça um security review de Services/UserService.cs verificando OWASP Top 10

# Performance
Analise Services/PedidoService.cs por problemas de performance: N+1, LINQ em loops, paginação

# WPF/MVVM
Revise ViewModels/FuncionariosViewModel.cs verificando padrões MVVM e anti-patterns

# Apenas críticos
Analise Services/FuncionarioService.cs e me mostre apenas issues críticas e erros que bloqueiam merge
```

> **Dica**: O Amazon Q considera o arquivo aberto no editor como contexto principal.
> Para revisar múltiplos arquivos, mencione-os explicitamente no prompt.

---

## Opção 2 — Fluxo com Análise Estática Prévia (recomendado)

Combinar os scripts Python (rápidos e precisos) com a análise de IA do Amazon Q para máxima cobertura.

### Passo 1: Rodar análise estática no terminal

```bash
# Análise de todos os arquivos alterados vs origin/main
python code_guardian/runner.py --rules-only --format text

# Apenas arquivos staged (antes do commit)
python code_guardian/runner.py --staged --rules-only --format text

# Arquivo específico
python code_guardian/runner.py --file Services/FuncionarioService.cs --rules-only
```

**Exemplo de saída:**
```
📁 Services/FuncionarioService.cs
  🔴 L 42 [SQL_INJECTION_CONCAT] Possível SQL Injection: query construída por concatenação.
  🟠 L 87 [TASK_RESULT_DEADLOCK] Task.Result pode causar deadlock. Use await.
  🟡 L120 [CONSOLE_WRITELINE] Console.WriteLine em produção. Use ILogger.

Rule Engine: 3 issue(s) — 🔴 1 critical  🟠 1 error  🟡 1 warning
```

### Passo 2: Colar no Amazon Q e pedir análise aprofundada

```
A análise estática do Code Guardian encontrou os seguintes problemas em Services/FuncionarioService.cs:

[cole aqui a saída do runner.py]

Com base nesses achados, faça uma análise aprofundada do arquivo verificando:
1. Se o SQL Injection na linha 42 é confirmado e qual a melhor correção
2. Se o deadlock na linha 87 afeta outros métodos da classe
3. Outros problemas de lógica, segurança ou padrões que a análise estática pode ter perdido

Gere um relatório no formato Code Guardian com Risk Score.
```

---

## Opção 3 — Amazon Q Developer Agent (autônomo)

O Amazon Q tem um modo agente que executa tasks de forma autônoma, lendo o código e gerando relatórios sem necessidade de comandos manuais.

### Como usar no VS Code

1. No painel Amazon Q, clicar em **"Dev Agent"** (ou abrir com `/dev`)
2. Descrever a task:

```
Faça um code review completo dos arquivos C# alterados neste branch vs origin/main.
Siga os padrões do projeto em .amazonq/rules/.
Gere um relatório com Risk Score e lista de issues por severidade.
```

### Como usar com AWS CLI (para pipelines)

```bash
# Instalar AWS CLI e configurar credenciais
aws configure

# Usar Amazon Q via CLI
aws q chat --message "Faça um code review de Services/FuncionarioService.cs seguindo os padrões em .amazonq/rules/"
```

---

## Opção 4 — Integração no Pull Request (CodeGuru)

Para review automático em PRs, o Amazon Q se integra ao **Amazon CodeGuru Reviewer**.

### Configuração no repositório GitHub

1. Acessar [CodeGuru console](https://console.aws.amazon.com/codeguru)
2. **Reviewer** → **Associated repositories** → **Associate repository**
3. Selecionar o repositório GitHub
4. Autorizar a integração

A partir daí, cada Pull Request receberá automaticamente comentários do Amazon Q com análise de código.

---

## Fluxo Recomendado no Dia a Dia

```
Você escreveu código
        ↓
Terminal: rodar análise estática
  python code_guardian/runner.py --staged --rules-only --format text
        ↓
Copiar a saída
        ↓
Amazon Q Chat: colar saída + pedir análise aprofundada
  "Com base nesta análise, revise FuncionarioService.cs e confirme/expanda os problemas"
        ↓
Amazon Q gera relatório completo com Risk Score
        ↓
Corrigir issues críticas e de erro
        ↓
git commit (hook pre-commit valida automaticamente)
        ↓
git push (hook pre-push valida novamente)
```

---

## Exemplo de Sessão Completa

**Terminal:**
```bash
python code_guardian/runner.py --staged --rules-only --format text
```
```
📁 Services/FuncionarioService.cs
  🔴 L 42 [SQL_INJECTION_CONCAT] Possível SQL Injection.
  🟠 L 87 [TASK_RESULT_DEADLOCK] Task.Result pode causar deadlock.

Risk Score parcial: 35 — 🔴 Alto Risco
```

**Amazon Q Chat:**
```
Usuário:
A análise estática encontrou 2 problemas em Services/FuncionarioService.cs:
- L42: SQL Injection por concatenação
- L87: Task.Result causando deadlock

Faça análise aprofundada e gere relatório completo com Risk Score final.

Amazon Q:
# 🛡️ Code Review — FuncionarioService.cs

**Risk Score: 45 — 🔴 Alto Risco**

## Issues do PR

### 🔴 [CRITICAL] SQL Injection — Linha 42
**Confirmado**: A interpolação `$"WHERE Cpf = '{cpf}'"` permite injeção de SQL.
**Risco**: Extração de todos os dados, bypass de autenticação, execução de comandos.

**Código atual**:
```csharp
var query = $"SELECT * FROM Funcionarios WHERE Cpf = '{cpf}'";
var result = await _connection.QueryAsync<Funcionario>(query);
```

**Correção**:
```csharp
var funcionario = await _context.Funcionarios
    .Where(f => f.Cpf == cpf)
    .FirstOrDefaultAsync();
// ou Dapper com parâmetros:
var funcionario = await _connection.QueryFirstOrDefaultAsync<Funcionario>(
    "SELECT * FROM Funcionarios WHERE Cpf = @Cpf",
    new { Cpf = cpf });
```

### 🟠 [ERROR] Deadlock Async — Linha 87
**Confirmado**: `.Result` em contexto com SynchronizationContext (WPF/ASP.NET).
**Impacto adicional**: O método `ProcessarFuncionario()` (L.120) também chama este método
com `.Result` — deadlock em cascata.

**Código atual**:
```csharp
var dados = _externalService.GetDadosAsync().Result;
```

**Correção**:
```csharp
var dados = await _externalService.GetDadosAsync();
```

### 🟠 [ERROR] Result Pattern ausente — Linha 55
**Identificado pela IA**: Método `CriarFuncionarioAsync` retorna `FuncionarioDto`
diretamente. Padrão do projeto exige `Result<FuncionarioDto>`.

...

## Resumo
- Critical: 1 | Error: 2 | Warning: 3
- **Recomendação**: Corrigir SQL Injection e deadlock antes de mergear.
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

## Prompts Prontos para Copiar

Salve estes prompts para usar rapidamente no dia a dia:

```
# Review geral
Faça um code review completo de [ARQUIVO] seguindo os padrões em .amazonq/rules/.
Gere relatório com Risk Score e issues por severidade.

# Review de segurança
Revise [ARQUIVO] focando em vulnerabilidades OWASP: SQL Injection, secrets hardcoded,
Path Traversal, IDOR e Mass Assignment.

# Review de padrões
Verifique se [ARQUIVO] segue o Result Pattern, logging obrigatório e padrões MVVM
conforme .amazonq/rules/. Liste violações com exemplos de correção.

# Review com análise estática
[Cole aqui a saída do runner.py]
Expanda esta análise estática com verificações de lógica, padrões e performance
que o regex não detecta.

# Review antes do PR
Quais problemas nos arquivos que alterei hoje impediriam a aprovação do PR?
Foco em critical e error.
```

---

## Limitações Conhecidas

| Limitação | Impacto | Contorno |
|-----------|---------|----------|
| Amazon Q não executa comandos do terminal | Scripts Python não rodam automaticamente | Rodar `runner.py` manualmente e colar no chat |
| Contexto de arquivos grandes | Arquivos com >500 linhas podem ser truncados | Selecionar o método/seção relevante |
| Plano Free tem limite de mensagens | Menos mensagens por mês | Usar `--rules-only` para análise estática e reservar Amazon Q para análise profunda |
| CodeGuru só em repositórios AWS CodeCommit ou GitHub | Automação em PR limitada | Usar chat manualmente ou integrar via CLI no pipeline |

---

## Documentação Relacionada

| Documento | Conteúdo |
|-----------|---------|
| [00-Inicio-Rapido.md](../00-Inicio-Rapido.md) | Visão geral do Code Guardian |
| [github-copilot.md](github-copilot.md) | Guia equivalente para GitHub Copilot |
| [16-Fluxo-Desenvolvedor.md](../16-Fluxo-Desenvolvedor.md) | Fluxo completo com Claude Code |
| [13-Runner-CLI.md](../13-Runner-CLI.md) | Todos os parâmetros do runner.py |
