using System.Collections.Generic;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Resultado da verificação de dependências do Code Guardian.
    /// </summary>
    public sealed class DependencyStatus
    {
        public bool PythonOk      { get; set; }
        public bool RunnerOk      { get; set; }
        public string? PythonVersion { get; set; }
        public string? RunnerPath    { get; set; }

        public bool TudoOk => PythonOk && RunnerOk;

        public string MontarMensagemErro()
        {
            if (TudoOk) return string.Empty;

            var partes = new List<string>();

            if (!PythonOk)
                partes.Add("Python não encontrado (PATH, %LOCALAPPDATA%\\Python e %LOCALAPPDATA%\\Programs\\Python pesquisados)");

            if (!RunnerOk)
                partes.Add("scripts do Code Guardian não localizados — reinstale a extensão ou configure o caminho manualmente");

            return string.Join(". ", partes) + ". Configure em Tools > Options > Code Guardian.";
        }
    }
}
