Option Explicit

Private Sub cmdSalvar_Click()
    Const sROTINA_NOME As String = "cmdSalvar_Click"
    On Error GoTo ErrcmdSalvar_Click
    MsgBox "Salvo"
ExitcmdSalvar_Click:
    Exit Sub
ErrcmdSalvar_Click:
    GoTo ExitcmdSalvar_Click
End Sub
