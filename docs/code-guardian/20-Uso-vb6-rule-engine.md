# VB6 Rule Engine — Guia do Desenvolvedor

Análise estática de código **Visual Basic 6** com sistema de score 0–100.
Detecta SQL Injection, error handling incorreto, violações de arquitetura Prosoft, performance e nomenclatura — sem necessidade de IA.

---

## Pré-requisitos

- Python 3.11+
- Arquivos VB6 com extensão `.bas`, `.cls`, `.frm` ou `.ctl`

Não requer conexão com internet nem chave de API.

---

## Uso mais comum

```bash
# Analisar um formulário
python code_guardian/vb6_rule_engine.py Views/frmCadastro.frm --format text

# Analisar uma classe de negócio
python code_guardian/vb6_rule_engine.py Classes/clsNFuncionario.cls --format text

# Analisar projeto inteiro (varre recursivamente)
python code_guardian/vb6_rule_engine.py --scan --dir C:/projetos/MeuSistemaVB6 --format text

# Somente erros críticos (leitura rápida)
python code_guardian/vb6_rule_engine.py frmCadastro.frm --severity error --format text
```

---

## Saída esperada

```text
📁 frmCadastro.frm
  🔴 L  1 [Declarações Obrigatórias] Option Explicit ausente. Todo módulo VB6 deve ter 'Option Explicit' como primeira declaração.
  🟠 L  6 [Tratamento de Erro] Sub/Function 'cmdSalvar_Click' sem tratamento de erro. Todo método deve ter 'On Error GoTo ErrNomeMetodo'.
  🔴 L 12 [SQL Injection] Possível SQL Injection: query construída por concatenação de strings. Use queries parametrizadas via ADODB.Command e parâmetros.
  🟠 L 12 [Arquitetura] Form executando SQL diretamente. Forms devem delegar para classes de negócio (clsN) ou dados (clsD).
  🟡 L 20 [Magic Numbers] Magic number detectado. Extrair para constante nomeada: 'Const NOME_CONSTANTE As Long = valor'.
  🟡 L 26 [Performance] UBound() chamado diretamente no For...Next. Cachear em variável antes do loop para melhor performance.

  Score: 40 / 100 — High technical debt
```

---

## Flags disponíveis

| Flag | O que faz | Exemplo |
|------|-----------|---------|
| `--format html` | Relatório HTML visual — **padrão** | `--format html` |
| `--format text` | Saída legível para humanos (terminal) | `--format text` |
| `--format json` | Saída JSON para integração com outras ferramentas | `--format json` |
| `--output <arquivo>` | Salva o resultado em arquivo (HTML ou JSON) | `--output rel.html` |
| `--severity error` | Mostra só `error` e `critical`, oculta warning/info | `--severity error` |
| `--severity warning` | Mostra `warning`, `error` e `critical` | `--severity warning` |
| `--scan` | Varre diretório recursivamente | `--scan` |
| `--dir <caminho>` | Diretório alvo do scan (padrão: diretório atual) | `--dir ./src` |
| `--compare` | Analisa só arquivos diferentes entre duas pastas | ver abaixo |
| `--base <caminho>` | Pasta com o código atual (usado com `--compare`) | `--base C:/proj` |
| `--review <caminho>` | Pasta da branch em revisão (usado com `--compare`) | `--review C:/temp` |

---

## Modo `--compare` — analisar apenas o que mudou

Para source control que copia a branch de revisão em pasta temporária, o `--compare` evita analisar arquivos que não foram alterados:

```bash
python code_guardian/vb6_rule_engine.py \
    --compare \
    --base   C:/projetos/SistemaFolha \
    --review C:/temp/revisao_branch \
    --output .codeguardian/vb6-diff.html
```

| Situação do arquivo | O que acontece |
|---------------------|----------------|
| Conteúdo idêntico nas duas pastas | Ignorado — não aparece no relatório |
| Existe nos dois, conteúdo diferente | Analisado — badge `✏️ MODIFICADO` |
| Só existe na pasta de revisão | Analisado — badge `🆕 NOVO` |

O relatório HTML exibe uma coluna extra **Mudança** na tabela de arquivos.

---

## O que cada severidade significa

| Ícone | Nível | O que fazer |
|-------|-------|-------------|
| 🔴 Critical | SQL Injection, Option Explicit ausente | **Corrigir antes de qualquer commit** |
| 🟠 Error | Sem error handler, SQL em Form, função >150 linhas | **Corrigir antes de abrir PR** |
| 🟡 Warning | Variant, magic number, performance, nomenclatura | Revisar — fortemente recomendado |
| 🔵 Info | TODO, sROTINA_NOME ausente | Opcional |

---

## Sistema de Score

O score começa em **100** e penalidades são subtraídas — **uma penalidade por tipo de violação**, independente do número de ocorrências.

| Violação detectada | Penalidade |
|--------------------|-----------|
| Bug ou erro de lógica | −20 |
| SQL Injection por concatenação | −20 |
| `On Error GoTo` ausente em método | −15 |
| `Option Explicit` ausente no arquivo | −15 |
| `On Error Resume Next` sem check de `Err.Number` | −15 |
| Loop infinito (`Do While True`) | −15 |
| SQL direto em Form (`.frm`) | −15 |
| `clsN` fazendo SQL direto (violação de arquitetura) | −15 |
| Declaração proibida (DefInt, DefStr, etc.) | −15 |
| Função/Sub com mais de 300 linhas | −20 |
| Função/Sub com mais de 150 linhas | −10 |
| `Variant` em lugar de tipo específico | −10 |
| Objeto criado sem `Set = Nothing` | −10 |
| Concatenação de strings em loop | −10 |
| SQL executada dentro de loop | −10 |
| `UBound()` não cacheado no For...Next | −5 |
| Magic number (literal numérico sem constante) | −5 |
| Concatenação com `+` em vez de `&` | −5 |
| Verificação de string vazia com `= ""` | −5 |
| Nome de variável genérico (tmp, temp, var) | −5 |

**Score ≤ 0** fica fixo em 0.

| Score | Qualidade | O que fazer |
|-------|-----------|-------------|
| 90–100 | ✅ Excellent | Pode ir para PR |
| 75–89 | 🟡 Good | Melhorias menores recomendadas |
| 60–74 | 🟠 Moderate technical debt | Revisar violações antes do PR |
| 40–59 | 🔴 High technical debt | Corrigir erros antes de prosseguir |
| 0–39 | 🚫 Critical — do not approve | Não abrir PR até corrigir críticos |

---

## Regras detectadas em detalhe

### 🔴 Críticos

**`VB6_MISSING_OPTION_EXPLICIT`**
Todo módulo VB6 deve ter `Option Explicit` como primeira declaração.
Sem ela, variáveis não declaradas são aceitas silenciosamente — fonte de bugs difíceis de rastrear.

```vb
' ❌ Errado — sem Option Explicit
Private Sub cmdSalvar_Click()
    nomCliente = txtNome.Text  ' Typo em "nomCliente" passa despercebido
End Sub

' ✅ Correto
Option Explicit

Private Sub cmdSalvar_Click()
    p_sNomeCliente = txtNome.Text  ' Typo causaria erro de compilação
End Sub
```

---

**`VB6_SQL_INJECTION_CONCAT`**
Query SQL construída com concatenação de string e variável.

```vb
' ❌ SQL Injection — usuário pode injetar código SQL
Set p_rsDados = p_objConn.Execute("SELECT * FROM Usuarios WHERE Login = '" & txtLogin.Text & "'")

' ✅ ADODB.Command com parâmetro
Dim p_cmmBusca As ADODB.Command
Set p_cmmBusca = New ADODB.Command
p_cmmBusca.ActiveConnection = p_objConn
p_cmmBusca.CommandText = "SELECT * FROM Usuarios WHERE Login = ?"
p_cmmBusca.Prepared = True
p_cmmBusca.Parameters.Append p_cmmBusca.CreateParameter("Login", adVarChar, adParamInput, 50, txtLogin.Text)
Set p_rsDados = p_cmmBusca.Execute()
Set p_cmmBusca = Nothing
```

---

### 🟠 Erros

**`VB6_MISSING_ERROR_HANDLER`**
Todo Sub/Function deve ter tratamento de erro estruturado com `ProErro`.

```vb
' ❌ Sem error handler — exceção não tratada encerra o processo
Public Function BuscarFuncionario(v_lCodigo As Long) As Boolean
    Set p_rsDados = p_objDados.BuscarPorId(v_lCodigo)
    BuscarFuncionario = True
End Function

' ✅ Estrutura Prosoft obrigatória
Public Function BuscarFuncionario(v_lCodigo As Long) As Boolean

    Const sROTINA_NOME As String = "BuscarFuncionario"
    Call ProErro.InicializarMetodoPublico(p_objErro)
    On Error GoTo ErrBuscarFuncionario

    Set p_rsDados = p_objDados.BuscarPorId(v_lCodigo)
    BuscarFuncionario = True

ExitBuscarFuncionario:
    Exit Function

ErrBuscarFuncionario:
    Call ProErro.Criar(Err.Number, Err.Description, TypeName(Me), sROTINA_NOME, p_objErro)
    GoTo ExitBuscarFuncionario

End Function
```

---

**`VB6_FORM_SQL_DIRECT`** _(apenas `.frm`)_
Forms não devem executar SQL. Devem delegar para `clsN` ou `clsD`.

```vb
' ❌ Form fazendo acesso a dados diretamente
Private Sub cmdSalvar_Click()
    p_objConn.Execute "INSERT INTO Funcionarios (Nome) VALUES ('" & txtNome.Text & "')"
End Sub

' ✅ Form delegando para classe de negócio
Private Sub cmdSalvar_Click()
    Dim p_blOk As Boolean
    p_blOk = p_objFuncionario.Salvar(txtNome.Text, txtCodigo.Text)
    If p_blOk Then
        MsgBox "Salvo com sucesso."
    End If
End Sub
```

---

**`VB6_CLN_SQL_DIRECT`** _(apenas `clsN*.cls`)_
Classe de negócio (`clsN`) não deve acessar banco — isso é responsabilidade de `clsD`.

```vb
' ❌ clsNFuncionario executando SQL
Public Function Buscar(v_lId As Long) As Boolean
    Set p_rsDados = p_objConn.Execute("SELECT * FROM Funcionarios WHERE Id = " & v_lId)
End Function

' ✅ clsNFuncionario delegando para clsD
Public Function Buscar(v_lId As Long) As Boolean
    Dim p_objDados As clsDFuncionario
    Set p_objDados = New clsDFuncionario
    Set p_rsDados = p_objDados.BuscarPorId(v_lId)
    Set p_objDados = Nothing
End Function
```

---

### 🟡 Warnings

**`VB6_VARIANT_OVERUSE`** — usar tipos específicos no lugar de `Variant`

**`VB6_UBOUND_IN_LOOP`** — cachear `UBound()` antes do loop

```vb
' ❌
For i = 0 To UBound(aItens)

' ✅
Dim lMax As Long
lMax = UBound(aItens)
For i = 0 To lMax
```

**`VB6_STRING_CONCAT_IN_LOOP`** — usar array + `Join()` no lugar de `&` em loop

```vb
' ❌ — realoca memória a cada iteração
For i = 0 To lMax
    sResultado = sResultado & aLinhas(i) & vbCrLf
Next i

' ✅
ReDim aBuffer(lMax)
For i = 0 To lMax
    aBuffer(i) = aLinhas(i)
Next i
sResultado = Join(aBuffer, vbCrLf)
```

**`VB6_EMPTY_STRING_CHECK`** — `Len()` é mais rápido que `= ""`

```vb
' ❌
If sNome = "" Then

' ✅
If Len(sNome) = 0 Then
```

---

## Usando com Claude Code — skill `/vb6-code-review`

Dentro do Claude Code (IDE), execute:

```text
/vb6-code-review frmCadastro.frm
```

Isso roda o script automático **e** faz revisão manual aprofundada dos padrões Prosoft, incluindo:
- Estrutura completa de error handler (`ProErro.Criar`, `ExitMetodo`, `ErrMetodo`)
- Prefixos de escopo+tipo nas variáveis (`p_sNome`, `v_lCodigo`)
- Verificação de `Set obj = Nothing` em todos os objetos
- Performance avançada (ADODB.Command com Prepared, cache de Fields)
- Geração de relatório salvo em `.codeguardian/vb6-review-YYYY-MM-DD-HHmm.md`

---

## Fluxo recomendado antes de commit

```text
1. Escreve/altera o arquivo VB6
        ↓
2. Roda o script
   python code_guardian/vb6_rule_engine.py <arquivo> --format text
        ↓
3. Score ≥ 75?
   ├── Sim → pode commitar
   └── Não → corrigir críticos e erros, re-analisar
        ↓
4. Antes de abrir PR → revisão completa no Claude Code
   /vb6-code-review <arquivo>
```

---

## Scan de projeto completo

Para verificar o estado de toda a base de código VB6:

```bash
# Escanear projeto inteiro
python code_guardian/vb6_rule_engine.py --scan --dir C:/projetos/MeuSistema --format text

# Saída resumida no final do scan:
# ────────────────────────────────────────────────────────────
# VB6 Rule Engine — 47 arquivo(s) analisado(s)
# Total: 312 issue(s) — 🔴 8 critical  🟠 41 error  🟡 215 warning  🔵 48 info
# Score médio: 52 / 100 — High technical debt
```

Para salvar o resultado em arquivo:

```bash
python code_guardian/vb6_rule_engine.py --scan --dir ./src --format text > relatorio-vb6.txt
```

---

## Saída JSON (integração com outras ferramentas)

```bash
python code_guardian/vb6_rule_engine.py frmCadastro.frm --format json
```

```json
{
  "issues": [
    {
      "file": "frmCadastro.frm",
      "line": 1,
      "severity": "critical",
      "category": "Declarações Obrigatórias",
      "rule_id": "VB6_MISSING_OPTION_EXPLICIT",
      "message": "Option Explicit ausente...",
      "source": "vb6_rule_engine"
    }
  ],
  "score": {
    "value": 40,
    "label": "High technical debt",
    "penalties": [
      { "rule_id": "VB6_MISSING_OPTION_EXPLICIT", "penalty": 15, "count": 1 },
      { "rule_id": "VB6_SQL_INJECTION_CONCAT",   "penalty": 20, "count": 3 }
    ]
  }
}
```

---

## Referência rápida de comandos

```bash
# Arquivo único — saída texto
python code_guardian/vb6_rule_engine.py frmCadastro.frm --format text

# Apenas erros (leitura rápida)
python code_guardian/vb6_rule_engine.py frmCadastro.frm --severity error --format text

# Classe de negócio
python code_guardian/vb6_rule_engine.py clsNFuncionario.cls --format text

# Projeto inteiro
python code_guardian/vb6_rule_engine.py --scan --dir ./src --format text

# Salvar resultado em arquivo
python code_guardian/vb6_rule_engine.py --scan --dir ./src --format text > relatorio-vb6.txt

# Saída JSON (para integração)
python code_guardian/vb6_rule_engine.py frmCadastro.frm --format json

# Review completo com IA no Claude Code
# /vb6-code-review frmCadastro.frm
```

---

## Documentação relacionada

| Documento | Conteúdo |
|-----------|----------|
| [00-Inicio-Rapido.md](00-Inicio-Rapido.md) | Visão geral do Code Guardian (C#) |
| [08-Uso-rule-engine.md](08-Uso-rule-engine.md) | Rule Engine para C# |
| [16-Fluxo-Desenvolvedor.md](16-Fluxo-Desenvolvedor.md) | Fluxo diário com git hooks (C#) |
| `.amazonq/rules/vb6-code-review.md` | Sistema de score e ordem de revisão |
| `.amazonq/rules/vb6-error-handling.md` | Estrutura obrigatória ProErro |
| `.amazonq/rules/vb6-architecture.md` | Separação clsN / clsD / frm |
| `.amazonq/rules/vb6-performance.md` | Otimizações de loop, string e banco |
| `.amazonq/rules/vb6-naming-conventions.md` | Prefixos obrigatórios de variáveis |
