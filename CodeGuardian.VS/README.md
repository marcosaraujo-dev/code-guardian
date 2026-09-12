# Code Guardian for Visual Studio

**Revisão de código C# automatizada, integrada ao Visual Studio.**

Code Guardian analisa seus arquivos C# por demanda — detectando vulnerabilidades de segurança, más práticas, code smells, métricas de qualidade e tendências históricas — e exibe os resultados diretamente no Error List, no Tool Window e em relatórios exportáveis.

> Sem nuvem. Sem serviços externos. Executa inteiramente na sua máquina.

---

## O que detecta

| Categoria | Exemplos |
|-----------|----------|
| **Segurança** | SQL Injection, secrets hardcoded, path traversal, deserialização perigosa |
| **Confiabilidade** | Exceções swallowed, catch blocks vazios, loops sem limites |
| **Performance** | Padrões N+1, concatenação de strings em loops, `CancellationToken` ausente |
| **Clean Code** | God Class, métodos acima de 30 linhas, nesting profundo (5+ níveis), magic numbers, duplicação literal de métodos (copy/paste), comentários sem substância (narram o quê, não o porquê) |
| **Async/Await** | Padrões de deadlock `.Result`/`.Wait()`, fire-and-forget sem tratamento de erro |

---

## Funcionalidades

### Análise de Arquivo
Analisa o arquivo `.cs` ativo no editor com um clique — **Tools → Analyze Current File (Code Guardian)**.

### Análise de Solution
Varre todos os arquivos `.cs` da solution de uma vez — botão **Analisar Solution** no Tool Window ou menu de contexto do Solution Explorer.

### Análise Incremental
Analisa apenas os arquivos modificados desde o último commit (`git diff HEAD`), ideal para pipelines de desenvolvimento ágil.

### AI Toggle (IA On/Off)
Alterna entre análise completa (rules + IA) e análise rápida (apenas rules), direto no Tool Window. Útil para economizar tempo em análises frequentes.

### Filtros de Issues
Filtre a lista de issues por severidade (Todos / CRITICAL / ERROR / WARNING / INFO) e por texto livre (regra, arquivo ou mensagem).

### Risk Score 0–100
Toda análise produz um Risk Score visual com barra colorida — verde (baixo risco) a vermelho (crítico).

| Score | Rótulo |
|-------|--------|
| 0–10 | Low Risk |
| 11–30 | Moderate |
| 31–60 | High Risk |
| 61–100 | Critical |

### Histórico e Tendência
O painel exibe a tendência em relação à análise anterior (`↑ piorou`, `↓ melhorou`, `= estável`). O histórico completo fica salvo em `.codeguardian/guardian-metrics.json` com até 100 execuções.

### Error List Integration
Todos os issues aparecem no **Error List** do Visual Studio com severidade, Rule ID, arquivo e número de linha — clique para navegar diretamente ao problema.

### Navegação por Clique
Clique em qualquer issue no Tool Window para abrir o arquivo e posicionar o cursor na linha exata.

### Copiar Issue
Botão ⎘ em cada issue copia o texto formatado para a área de transferência: `[SEVERITY] RULE_ID — arquivo.cs:linha — mensagem`.

### Suprimir Issue
Botão ✕ em cada issue abre o arquivo, posiciona na linha e insere automaticamente o comentário `// guardian: suppress RULE_ID` para suprimir o aviso.

### Relatório HTML
Relatório HTML auto-contido com tema escuro: card de risco, tabela de métricas por arquivo e lista completa de issues com badges de severidade.

### Exportação SARIF
Exporta o resultado em formato **SARIF 2.1.0** para `.codeguardian/guardian-report.sarif`. Compatível com GitHub Actions, Azure DevOps e qualquer SARIF viewer.

### Git Hooks
Instala um hook `pre-commit` que bloqueia commits contendo issues críticos — via **Tools → Code Guardian: Install Git Hooks** ou pelo InfoBar automático ao abrir uma solution sem hooks.

### Métricas de Código
Para cada arquivo analisado:
- Total de linhas
- Maior método (linhas)
- Profundidade máxima de nesting
- Dependências no construtor (indicador de acoplamento)

---

## Requisitos

| Requisito | Detalhes |
|-----------|---------|
| **Visual Studio** | 2019 (16.x) ou 2022 (17.x) — Community, Professional ou Enterprise |
| **Python** | 3.8 ou superior — deve estar no `PATH` ou configurado nas Settings |
| **Scripts Code Guardian** | A pasta `code_guardian/` deve existir na raiz do repositório |

### Obtendo os scripts

O motor de análise (scripts Python) está disponível em:
**[github.com/marcosaraujo-dev/code-guardian](https://github.com/marcosaraujo-dev/code-guardian)**

Clone ou copie a pasta `code_guardian/` para a raiz do repositório:

```
seu-repositorio/
├── code_guardian/
│   ├── runner.py
│   ├── rule_engine.py
│   ├── metrics.py
│   ├── diff_parser.py
│   ├── ai_client.py
│   └── ...
├── src/
└── ...
```

---

## Início Rápido

1. Instale a extensão via arquivo `.vsix` ou pelo VS Marketplace
2. Clone ou copie a pasta `code_guardian/` para a raiz do seu repositório
3. Abra uma solution no Visual Studio
4. Vá em **Tools → Analyze Current File (Code Guardian)** ou abra o painel em **Tools → Code Guardian**
5. Visualize os resultados no **Error List** e no painel **Tools → Code Guardian**

---

## Configuração

Acesse **Tools → Options → Code Guardian**:

| Configuração | Padrão | Descrição |
|--------------|--------|-----------|
| Python Executable | `python` | Caminho para `python.exe` se não estiver no PATH |
| Runner Script Path | *(auto-detect)* | Override do caminho para `runner.py` |
| Analysis Timeout | `60` segundos | Tempo máximo por análise |
| Rules Only | `false` | Pular análise de IA (mais rápido) |

---

## Comandos

| Comando | Local | Descrição |
|---------|-------|-----------|
| **Code Guardian** | Menu Tools | Abre o Tool Window |
| **Analyze Current File** | Menu Tools | Analisa o arquivo `.cs` ativo |
| **Analyze with Code Guardian** | Context menu Solution Explorer | Scan completo da solution |
| **Install Git Hooks** | Menu Tools | Instala hook pre-commit no repositório |
| **Export SARIF** | Tool Window | Exporta resultado em SARIF 2.1.0 |

---

## Integração CI/CD

O arquivo `.codeguardian/guardian-report.sarif` pode ser consumido diretamente em pipelines:

**GitHub Actions:**
```yaml
- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: .codeguardian/guardian-report.sarif
```

**Azure DevOps:**
```yaml
- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: .codeguardian/guardian-report.sarif
    artifactName: code-guardian-sarif
```

---

## Níveis de Severidade

| Nível | Significado |
|-------|-------------|
| **Critical** | Vulnerabilidade de segurança ou bloqueador de confiabilidade — deve corrigir |
| **Error** | Violação clara de boas práticas |
| **Warning** | Code smell ou problema potencial |
| **Info** | Sugestão ou observação de métrica |

---

## Release Notes

### 1.0.4
- Exportação SARIF 2.1.0 para CI/CD (GitHub Actions, Azure DevOps)
- Histórico de execuções em `guardian-metrics.json` com tendência visual
- Análise incremental (apenas arquivos modificados via `git diff HEAD`)
- AI Toggle — alternar entre análise completa e rules-only no Tool Window
- Filtros por severidade e texto livre na lista de issues
- Navegação por clique — abre arquivo na linha exata do issue
- Botão de copiar issue para área de transferência
- Botão de suprimir issue com inserção automática de comentário
- Contador de issues críticos/erros na aba do Tool Window
- Progress bar durante análise de solution com nome do arquivo atual
- Correção no loop de instalação de Git Hooks (conflito com hook de terceiros)

### 1.0.0
- Release inicial com Rule Engine (20+ regras), métricas de código, Risk Score 0–100
- Error List integration, Tool Window, relatório HTML, Git Hooks

---

## Feedback e Issues

Encontrou um bug ou tem uma sugestão?
Abra uma issue em **[github.com/marcosaraujo-dev/code-guardian/issues](https://github.com/marcosaraujo-dev/code-guardian/issues)**

---

*Code Guardian é desenvolvido por [CygnusForge](https://cygnusforge.com.br) e é gratuito.*
