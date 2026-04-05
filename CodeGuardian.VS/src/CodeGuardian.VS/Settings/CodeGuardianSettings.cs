namespace CodeGuardian.VS.Settings
{
    /// <summary>
    /// POCO com todas as configurações do Code Guardian.
    /// Espelhado da CodeGuardianOptionsPage para uso fora do UI thread.
    /// </summary>
    public sealed class CodeGuardianSettings
    {
        /// <summary>Caminho para o executável Python (ex: "python", "py" ou caminho absoluto).</summary>
        public string PythonExecutable { get; set; } = "python";

        /// <summary>Analisar automaticamente ao salvar arquivos .cs.</summary>
        public bool AnalyzeOnSave { get; set; } = true;

        /// <summary>Usar --rules-only (sem IA, mais rápido).</summary>
        public bool RulesOnly { get; set; } = true;

        /// <summary>Severidade mínima para exibir issues: info | warning | error | critical.</summary>
        public string MinimumSeverity { get; set; } = "warning";

        /// <summary>Timeout da análise Python em segundos.</summary>
        public int AnalysisTimeoutSeconds { get; set; } = 30;

        /// <summary>Caminho manual do runner.py (deixar vazio para descoberta automática).</summary>
        public string RunnerScriptPath { get; set; } = string.Empty;

        /// <summary>Configurações com valores padrão para uso quando o package não está disponível.</summary>
        public static CodeGuardianSettings Padrao => new CodeGuardianSettings();
    }
}
