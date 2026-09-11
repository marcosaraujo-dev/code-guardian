# Code Guardian UI — Manual de Uso

Interface gráfica para execução dos scripts de code review do Code Guardian, com suporte a projetos C# e VB6, terminal integrado e geração de relatórios HTML.

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Instalação e Primeira Execução](#3-instalação-e-primeira-execução)
4. [Layout da Interface](#4-layout-da-interface)
5. [Aba C#](#5-aba-c)
6. [Aba VB6](#6-aba-vb6)
7. [Terminal de Saída](#7-terminal-de-saída)
8. [Botões de Ação](#8-botões-de-ação)
9. [Configurações de IA](#9-configurações-de-ia)
10. [Distribuição como Executável (.exe)](#10-distribuição-como-executável-exe)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Visão Geral

O **Code Guardian UI** é uma interface gráfica que encapsula todos os scripts de análise do Code Guardian, permitindo executar revisões de código sem precisar usar o terminal. A ferramenta foi construída em Python com `customtkinter` (tema escuro moderno) e oferece:

- Análise de projetos **C#** via `runner.py` (diff, staged, arquivo ou scan)
- Análise de projetos **VB6** via `vb6_rule_engine.py` (arquivo, scan ou comparação de pastas)
- **Terminal integrado** com saída colorida em tempo real
- **Geração de relatórios HTML** acessíveis com um clique
- **Configuração visual** de provedores de IA (Gemini, Claude, OpenAI, Ollama)
- **Instalação automática** de dependências na primeira execução

```
┌─────────────────────────────────────────────────────────────────────┐
│  Code Guardian  v1.0.0                                              │
├──────────────────────────┬──────────────────────────────────────────┤
│  [ C# ]  [ VB6 ]         │                                          │
│                          │  TERMINAL                                │
│  ┌────────────────────┐  │  [14:32:01] ────────────────────────     │
│  │ Modo de Análise    │  │  [14:32:01] Executando: runner.py...     │
│  │ ◉ Diff vs branch  │  │  [14:32:02] Analisando (1/3): X.cs       │
│  │ ○ Staged          │  │  [14:32:05] 🟡 L45 [Magic Number]...     │
│  │ ○ Arquivo único   │  │  [14:32:06] ✅ Análise concluída.         │
│  │ ○ Scan de pasta   │  │                                          │
│  └────────────────────┘  │                                          │
│                          │                                          │
│  ┌────────────────────┐  │                                          │
│  │ Opções             │  │                                          │
│  │ Severidade: [▼]    │  │                                          │
│  │ □ Apenas regras    │  │                                          │
│  │ Timeout: [60]      │  │                                          │
│  └────────────────────┘  │                                          │
├──────────────────────────┴──────────────────────────────────────────┤
│  [Executar]  [Abrir Relatório]  [Limpar Terminal]  [Configurações]  │
├─────────────────────────────────────────────────────────────────────┤
│  Repositório: C:/Repos/MeuProjeto   |   Pronto                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pré-requisitos

| Requisito | Versão mínima | Observação |
|-----------|--------------|------------|
| Python | 3.10+ | Deve estar no PATH do sistema |
| Git | qualquer | Necessário para modos diff e staged |
| customtkinter | 5.2+ | Instalado automaticamente na 1ª execução |
| Pillow | qualquer | Instalado automaticamente na 1ª execução |

> **Para modo executável (.exe):** Python precisa estar instalado no sistema do usuário, pois os scripts de análise são chamados como subprocessos.

---

## 3. Instalação e Primeira Execução

### Rodando como script Python (desenvolvimento)

```bash
# Na raiz do repositório
python code_guardian/code_guardian_ui.py
```

Na **primeira execução**, caso `customtkinter` ou `Pillow` não estejam instalados, a interface exibe automaticamente uma tela de instalação:

```
┌──────────────────────────────────────────────┐
│  Code Guardian                               │
│  Instalando dependências necessárias...      │
│                                              │
│   customtkinter   ✓ Instalado               │
│   darkdetect      ✓ Instalado               │
│   Pillow          Instalando...             │
│   packaging       Aguardando...             │
│                                              │
│  Progresso: ████████████░░░░  3/4           │
│                                              │
│  >> pip install Pillow                       │
│     Collecting Pillow...                     │
│                                              │
│  Instalando Pillow (3/4)...                  │
└──────────────────────────────────────────────┘
```

Após a instalação, a janela fecha automaticamente e a interface principal abre.

### Rodando como executável (.exe)

Basta abrir o arquivo `CodeGuardian.exe` — nenhuma instalação adicional é necessária para a interface gráfica. Consulte a [seção 10](#10-distribuição-como-executável-exe) para gerar o executável.

---

## 4. Layout da Interface

A janela é dividida em três áreas principais:

| Área | Localização | Função |
|------|-------------|--------|
| **Painel de configuração** | Esquerda (~430px) | Abas C# e VB6 com todos os parâmetros de análise |
| **Terminal de saída** | Direita (expansível) | Exibe em tempo real o output dos scripts |
| **Barra de ação** | Parte inferior | Botões Executar, Abrir Relatório, Limpar, Configurações |
| **Status bar** | Rodapé | Exibe o repositório detectado e o estado atual |

A janela é **redimensionável** (mínimo 900×600px). O terminal se expande horizontalmente conforme a janela cresce.

### Status bar

A barra de status exibe:
- O caminho do repositório git detectado automaticamente no startup
- O estado atual: `Pronto`, `Executando...`, `Concluído com sucesso`, `Cancelado`, etc.

---

## 5. Aba C#

A aba **C#** invoca o `runner.py` e suporta quatro modos de análise.

### 5.1 Modos de Análise

Selecione o modo clicando no botão de rádio correspondente. Os campos de entrada mudam dinamicamente conforme o modo selecionado.

---

#### Modo: Diff vs branch (padrão)

Analisa os arquivos alterados em relação a um branch base, usando `git diff`.

```
◉ Diff vs branch (padrão)
   Branch base:      [ origin/main          ]
   Raiz do projeto:  [ C:/Repos/MeuProjeto/ ] [Escolher...]
```

| Campo | Descrição | Padrão |
|-------|-----------|--------|
| Branch base | Branch de comparação do git diff | `origin/main` |
| Raiz do projeto | Pasta raiz do repositório a analisar | Auto-detectado |

**Quando usar:** em todo pull request ou antes de fazer push, para revisar apenas o que foi alterado.

---

#### Modo: Staged

Analisa apenas os arquivos adicionados ao staging area (`git add`).

```
○ Staged (arquivos em staging)
   Analisa apenas arquivos no staging area (git add).
   Raiz do projeto:  [ C:/Repos/MeuProjeto/ ] [Escolher...]
```

| Campo | Descrição |
|-------|-----------|
| Raiz do projeto | **Obrigatório** quando a UI está em pasta diferente do projeto |

> **Por que a Raiz do projeto é importante no modo Staged?**
> O comando `git diff --cached` precisa ser executado dentro do repositório correto. Se você está usando o executável `.exe` ou rodando a UI de uma pasta diferente do projeto, selecione a pasta raiz do projeto aqui.

**Quando usar:** antes de cada commit, para verificar o que está prestes a ser commitado.

---

#### Modo: Arquivo único

Analisa um único arquivo `.cs` selecionado.

```
○ Arquivo único (.cs)
   Arquivo .cs:  [ C:/Repos/Projeto/Services/UserService.cs ] [Escolher...]
```

Clique em **Escolher...** para abrir o seletor de arquivos filtrado para `.cs`.

**Quando usar:** revisão pontual de um arquivo específico durante o desenvolvimento.

---

#### Modo: Scan de diretório

Varre recursivamente todos os arquivos `.cs` de uma pasta.

```
○ Scan de diretório
   Pasta:  [ C:/Repos/MeuProjeto/src/ ] [Escolher pasta...]
```

> Arquivos gerados automaticamente são excluídos: `Migrations/`, `.Designer.cs`, `AssemblyInfo.cs`, arquivos em `bin/` e `obj/`.

**Quando usar:** revisão completa do projeto ou de uma camada específica (ex.: apenas a pasta `Services/`).

---

### 5.2 Opções da Aba C#

Após selecionar o modo, configure as opções abaixo:

#### Apenas regras (sem IA)

```
☑ Apenas regras (sem IA)
```

Quando marcado, pula a análise de IA e executa apenas o `rule_engine.py` e `metrics.py`. A análise fica mais rápida (segundos vs minutos) e não consome tokens de API.

> O dropdown **Provedor IA** fica oculto quando esta opção está marcada.

---

#### Severidade mínima

```
Severidade mínima:  [ info ▼ ]
```

Filtra os resultados pelo nível de severidade. Apenas issues iguais ou acima do nível selecionado são reportadas.

| Valor | O que inclui |
|-------|-------------|
| `info` | Todos os issues (padrão) |
| `warning` | Warnings, errors e criticals |
| `error` | Errors e criticals apenas |
| `critical` | Apenas issues críticos (SQL Injection, secrets, etc.) |

---

#### Falhar em

```
Falhar em:  [ none ▼ ]
```

Define o nível de severidade que faz a análise retornar exit code 1 (útil em pipelines CI/CD).

| Valor | Comportamento |
|-------|--------------|
| `none` | Sempre exit 0 (padrão) |
| `warning` | Exit 1 se houver qualquer warning ou acima |
| `error` | Exit 1 se houver error ou critical |
| `critical` | Exit 1 apenas se houver critical |

---

#### Timeout

```
Timeout (s):  [ 60 ]
```

Tempo máximo em segundos para a análise de IA por arquivo. O padrão é 60 segundos. Para projetos grandes ou conexões lentas, aumente para `120` ou `180`.

---

#### Saída HTML (opcional)

```
Saída HTML (opcional):  [ relatorio.html        ] [...]
```

Caminho personalizado para o relatório HTML gerado. Se vazio, o relatório é salvo automaticamente em `.codeguardian/last-report.html`.

---

#### Provedor IA

```
Provedor IA:  [ Auto (config.json) ▼ ]
```

Seleciona qual provedor de IA usar na análise. A opção `Auto` respeita o que está configurado no `config.json`.

| Opção | Provedor |
|-------|---------|
| Auto (config.json) | Usa o primário configurado nas Configurações |
| gemini | Google Gemini |
| claude | Anthropic Claude |
| openai | OpenAI GPT |
| ollama | Modelo local (offline) |

---

## 6. Aba VB6

A aba **VB6** invoca o `vb6_rule_engine.py` e suporta três modos de análise. Suporta arquivos `.bas`, `.cls`, `.frm` e `.ctl`.

### 6.1 Modos de Análise

---

#### Modo: Arquivo único

Analisa um único arquivo VB6.

```
◉ Arquivo único (.bas, .cls, .frm, .ctl)
   Arquivo VB6:  [ C:/VB6/frmCadastro.frm ] [Escolher...]
```

O seletor de arquivo é filtrado para extensões VB6. Clique em **Escolher...** para navegar.

---

#### Modo: Scan de diretório

Varre recursivamente todos os arquivos VB6 de uma pasta.

```
○ Scan de diretório
   Pasta:  [ C:/Repos/ProjetoVB6/ ] [Escolher pasta...]
```

Todos os `.bas`, `.cls`, `.frm` e `.ctl` encontrados são analisados. Um relatório consolidado é gerado.

---

#### Modo: Comparação de pastas

Compara duas versões de um projeto VB6 — a versão original e a versão revisada — identificando regressões e melhorias.

```
○ Comparação de pastas
   ┌─────────────────────────────────────────────────────┐
   │ Pasta base (original):                              │
   │ [ C:/Repos/ProjetoVB6/v1/  ]  [Escolher...]        │
   │                                                     │
   │ Pasta revisão (modificada):                         │
   │ [ C:/Repos/ProjetoVB6/v2/  ]  [Escolher...]        │
   └─────────────────────────────────────────────────────┘
```

| Campo | Descrição |
|-------|-----------|
| Pasta base | Versão original do código (antes das alterações) |
| Pasta revisão | Versão modificada (após as alterações) |

O script analisa ambas as pastas e gera um relatório comparativo mostrando issues novos, resolvidos e mantidos.

**Quando usar:** ao receber arquivos VB6 modificados para homologação — compare a versão em produção com a versão entregue.

---

### 6.2 Opções da Aba VB6

#### Severidade mínima

Mesma lógica da aba C#. Valores: `info`, `warning`, `error`, `critical`.

#### Formato de saída

```
Formato de saída:  [ text + html ▼ ]
```

| Valor | Comportamento |
|-------|--------------|
| `text + html` | Exibe no terminal + gera relatório HTML (padrão) |
| `json` | Saída em JSON estruturado (útil para integração com outras ferramentas) |
| `html` | Gera apenas o HTML, sem texto no terminal |

> Para os formatos `text + html` e `html`, o nome do arquivo é gerado automaticamente:
> `.codeguardian/code-review-YYYY-MM-DD-HHMM - VB6.html`

---

## 7. Terminal de Saída

O terminal exibe em tempo real toda a saída dos scripts de análise.

```
[14:32:01] ────────────────────────────────────────────────────
[14:32:01] Diretório: C:/Repos/MeuProjeto
[14:32:01] Executando: python runner.py --base origin/main
[14:32:01] ────────────────────────────────────────────────────
[14:32:02] [guardian] Analisando (1/3): Services/UserService.cs
[14:32:03] 🟡 L45  [Magic Numbers] Magic number detectado: 30
[14:32:03] 🟠 L78  [Deadlock Async] Task.Result pode causar deadlock
[14:32:04] [guardian] Analisando (2/3): Controllers/UserController.cs
[14:32:05] ✅ Nenhum problema encontrado.
[14:32:06] ────────────────────────────────────────────────────
[14:32:06] Análise concluída com sucesso.
```

### Cores de saída

| Cor | Significado | Exemplos |
|-----|-------------|---------|
| Verde | Sucesso / sem problemas | `✅ Análise concluída`, `Nenhum bloqueador` |
| Laranja | Avisos | `🟡 warning`, avisos de qualidade |
| Vermelho | Erros críticos | `🔴 critical`, `🟠 error`, exceções |
| Azul | Informações gerais | Mensagens de progresso, contagens |
| Cinza | Metadados | Timestamps, separadores, comandos executados |

### Comportamento

- **Auto-scroll:** o terminal acompanha automaticamente as novas linhas.
- **Histórico acumulado:** o conteúdo não é apagado entre execuções. Use **Limpar Terminal** para resetar.
- **Timestamp:** cada linha é prefixada com `[HH:MM:SS]` para rastreabilidade.

---

## 8. Botões de Ação

### Executar / Cancelar

- **Executar** (azul): inicia a análise com as configurações atuais.
- Durante a execução, o botão muda para **Cancelar** (vermelho).
- **Cancelar**: envia sinal de término ao processo. Se o processo não responder em 2 segundos, é forçado a encerrar.

> Configurações e Abrir Relatório ficam desabilitados durante a execução.

### Abrir Relatório

Disponível após a conclusão de uma análise que gerou um arquivo HTML. Abre o relatório mais recente no navegador padrão do sistema.

O relatório inclui:
- Risk Score geral do projeto
- Lista de issues por arquivo com severidade e linha
- Métricas de qualidade (tamanho de métodos, nesting, God Classes)
- Análise de IA (quando habilitada)

### Limpar Terminal

Apaga todo o conteúdo do terminal. A operação é imediata e irreversível.

### Configurações

Abre o diálogo de configuração de provedores de IA. Consulte a [seção 9](#9-configurações-de-ia).

---

## 9. Configurações de IA

O diálogo de configurações permite definir qual provedor de IA usar e inserir as chaves de API — tudo sem precisar editar arquivos manualmente.

```
┌───────────────────────────────────────────────┐
│  Configurações — Code Guardian                │
├───────────────────────────────────────────────┤
│  Provedores de IA                             │
│    Primário:   [ gemini  ▼ ]                  │
│    Fallback:   [ ollama  ▼ ]                  │
├───────────────────────────────────────────────┤
│  Gemini                                       │
│    Modelo:         [ gemini-1.5-pro      ]    │
│    GEMINI_API_KEY: [ ••••••••••••••••••• ]    │
├───────────────────────────────────────────────┤
│  Claude (Anthropic)                           │
│    Modelo:             [ claude-sonnet-4-6 ]  │
│    ANTHROPIC_API_KEY:  [ ••••••••••••••••• ]  │
├───────────────────────────────────────────────┤
│  OpenAI                                       │
│    Modelo:        [ gpt-4o              ]     │
│    OPENAI_API_KEY: [ ••••••••••••••••••• ]    │
├───────────────────────────────────────────────┤
│  Ollama (local)                               │
│    URL base:  [ http://localhost:11434  ]     │
│    Modelo:    [ qwen2.5-coder:32b      ]      │
├───────────────────────────────────────────────┤
│                       [Salvar]  [Cancelar]    │
└───────────────────────────────────────────────┘
```

### Provedores

| Campo | Descrição |
|-------|-----------|
| **Primário** | Provedor principal usado na análise |
| **Fallback** | Usado automaticamente se o primário falhar ou não estiver disponível |

### Chaves de API

Os campos de chave de API são mascarados (`••••`). Ao clicar em **Salvar**:

1. O `config.json` é atualizado com os modelos e provedores selecionados.
2. As chaves de API são aplicadas como **variáveis de ambiente** na sessão atual (não ficam gravadas no JSON por segurança).

> Para persistir as chaves entre reinicializações, configure-as como variáveis de ambiente do sistema (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).

### Localização do config.json

| Modo de execução | Localização |
|-----------------|-------------|
| Script Python (dev) | `code_guardian/config.json` |
| Executável `.exe` | `%APPDATA%\CodeGuardian\config.json` |

Ao usar o `.exe`, o arquivo de configuração fica em uma pasta do usuário e pode ser editado diretamente sem necessidade de recompilação.

---

## 10. Distribuição como Executável (.exe)

### Gerando o executável

```bash
# Na raiz do repositório
python code_guardian/build_exe.py
```

O script instala o PyInstaller automaticamente se necessário, e gera `dist/CodeGuardian.exe`.

### O que está embutido no exe

| Componente | Tratamento |
|-----------|------------|
| Interface gráfica (`customtkinter`, `Pillow`, etc.) | Embutido — sem instalação necessária |
| Scripts de análise (`runner.py`, `vb6_rule_engine.py`, etc.) | Embutidos como recursos |
| `config.json` (template) | Embutido — copiado para `%APPDATA%` na 1ª execução |
| Ícone CygnusForge | Embutido — aparece no Explorer e barra de tarefas |
| Python interpreter | **Não embutido** — deve estar instalado no sistema |

### Requisito no sistema do usuário

O `.exe` requer **Python 3.10+** instalado e no PATH, pois os scripts de análise são executados como subprocessos. A detecção é automática — se não encontrar, exibe mensagem de erro com instrução de instalação.

### Configuração pós-implantação (sem recompilar)

Após distribuir o `.exe`, o usuário pode alterar as chaves de API abrindo o diálogo **Configurações** dentro da própria interface. As configurações são salvas em:

```
C:\Users\<nome>\AppData\Roaming\CodeGuardian\config.json
```

---

## 11. Troubleshooting

### A interface abre com aparência básica (sem tema escuro)

**Causa:** `customtkinter` não está instalado.

**Solução:** Execute:
```bash
pip install customtkinter
```
Ou deixe a tela de instalação automática instalar na próxima execução.

---

### Erro: "Python não encontrado no sistema" (no exe)

**Causa:** Python não está instalado ou não está no PATH.

**Solução:**
1. Instale Python 3.10+ em [python.org](https://python.org)
2. Durante a instalação, marque **"Add Python to PATH"**
3. Reinicie o computador

---

### Modo Staged não detecta arquivos

**Causa:** A UI está sendo executada em uma pasta diferente do repositório git.

**Solução:** No campo **Raiz do projeto** (que aparece no modo Staged), selecione a pasta raiz do repositório que contém a pasta `.git`.

---

### O botão "Abrir Relatório" permanece desabilitado

**Causa:** Nenhum arquivo HTML foi gerado na pasta `.codeguardian/`.

**Possíveis razões:**
- A análise foi executada com `--format json`
- A pasta `.codeguardian/` não foi criada (sem permissão de escrita)
- A análise foi cancelada antes de gerar o relatório

**Solução:** Execute a análise novamente com formato `text + html` e verifique se há permissão de escrita na pasta do repositório.

---

### Análise trava e não termina

**Causa:** Timeout da chamada de IA ou processo filho travado.

**Solução:**
1. Clique em **Cancelar** — o processo é terminado em até 2 segundos.
2. Marque **Apenas regras (sem IA)** para pular a análise de IA.
3. Reduza o **Timeout** para um valor menor (ex.: `30`).

---

### Ícone do exe ainda aparece como Python/disquete

**Causa:** Cache de ícones do Windows desatualizado.

**Solução:** Abra o PowerShell como administrador e execute:
```powershell
Stop-Process -Name explorer -Force
Start-Sleep -Seconds 1
Remove-Item "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\iconcache*" -Force -ErrorAction SilentlyContinue
Start-Process explorer.exe
```

---

### Erro de encoding / caracteres estranhos no terminal

**Causa:** Variáveis de ambiente de encoding não configuradas.

**Solução:** Execute com:
```bash
python -X utf8 code_guardian/code_guardian_ui.py
```

Ou defina permanentemente no sistema:
```
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
```

---

## Referências

| Documento | Conteúdo |
|-----------|---------|
| `docs/code-guardian/00-Inicio-Rapido.md` | Visão geral do Code Guardian e scripts CLI |
| `docs/code-guardian/13-Runner-CLI.md` | Flags completos do `runner.py` |
| `docs/code-guardian/20-Uso-vb6-rule-engine.md` | Detalhes do `vb6_rule_engine.py` |
| `docs/code-guardian/12-Trocar-Provedor-IA.md` | Configuração de provedores de IA |
| `docs/code-guardian/07-Ollama-Setup.md` | Como configurar o Ollama local |
| `docs/code-guardian/21-GUI-Code-Guardian-UI.md` | Especificação técnica da interface |
