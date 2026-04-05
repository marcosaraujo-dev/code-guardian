' Formulário de cadastro de funcionários
' ARQUIVO DE TESTE - contém propositalmente anti-patterns para validação do vb6_rule_engine.py

' Falta: Option Explicit

Private Sub cmdSalvar_Click()
    ' Anti-pattern: lógica de negócio direto no form, sem tratamento de erro
    Dim resultado As Variant  ' AP: Variant
    Dim temp As String        ' AP: nome genérico

    ' AP: SQL direto no form
    Set p_rsDados = p_objConn.Execute("SELECT * FROM Funcionarios WHERE Codigo = " & txtCodigo.Text)

    ' AP: verificação de string vazia com =
    If txtNome.Text = "" Then
        MsgBox "Informe o nome"
    End If

    ' AP: magic number
    If p_iCount > 100 Then
        MsgBox "Limite excedido"
    End If

    ' AP: loop com UBound direto e concatenação dentro
    Dim sResultado As String
    For i = 0 To UBound(aItens)
        sResultado = sResultado & aItens(i) & vbCrLf  ' AP: concat em loop
        ' AP: SQL dentro de loop
        Set p_rsItem = p_objConn.Execute("SELECT * FROM Itens WHERE Id = " & i)
    Next i

    ' AP: objeto não liberado (sem Set p_rsDados = Nothing)
End Sub

Private Sub cmdCancelar_Click()
    ' AP: sem On Error GoTo, sem sROTINA_NOME
    Unload Me
End Sub

' TODO: implementar validação completa do CPF
