Private Sub cmdImprimir_Click()
    Dim sql As String
    sql = "SELECT * FROM Relatorio WHERE id = " & txtId.Text
    conn.Execute sql
End Sub
