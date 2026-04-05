using System.ComponentModel;
using CodeGuardian.VS.Settings;
using Microsoft.VisualStudio.Shell;

namespace CodeGuardian.VS.Settings
{
    /// <summary>
    /// Página de opções do Code Guardian em Tools > Options > Code Guardian > General.
    /// </summary>
    public sealed class CodeGuardianOptionsPage : DialogPage
    {
        [Category("Python")]
        [DisplayName("Executável Python")]
        [Description("Caminho para python.exe ou simplesmente 'python' / 'py'. Ex: C:\\Python311\\python.exe")]
        public string PythonExecutable { get; set; } = "python";

        [Category("Análise")]
        [DisplayName("Analisar ao Salvar")]
        [Description("Executa o Code Guardian automaticamente ao salvar arquivos .cs.")]
        public bool AnalyzeOnSave { get; set; } = true;

        [Category("Análise")]
        [DisplayName("Apenas Regras (sem IA)")]
        [Description("Usa --rules-only para análise mais rápida, sem chamar a IA.")]
        public bool RulesOnly { get; set; } = true;

        [Category("Análise")]
        [DisplayName("Severidade Mínima")]
        [Description("Oculta issues abaixo desta severidade. Valores: info | warning | error | critical")]
        public string MinimumSeverity { get; set; } = "warning";

        [Category("Análise")]
        [DisplayName("Timeout (segundos)")]
        [Description("Tempo máximo de espera para o processo Python. Padrão: 30 segundos.")]
        public int AnalysisTimeoutSeconds { get; set; } = 30;

        [Category("Avançado")]
        [DisplayName("Caminho do runner.py")]
        [Description("Deixe vazio para descoberta automática. Preencha apenas se o runner.py estiver em local não padrão.")]
        public string RunnerScriptPath { get; set; } = string.Empty;

        /// <summary>
        /// Converte a página de opções em um POCO imutável para uso thread-safe.
        /// </summary>
        public CodeGuardianSettings ToSettings() => new CodeGuardianSettings
        {
            PythonExecutable = PythonExecutable,
            AnalyzeOnSave = AnalyzeOnSave,
            RulesOnly = RulesOnly,
            MinimumSeverity = MinimumSeverity,
            AnalysisTimeoutSeconds = AnalysisTimeoutSeconds,
            RunnerScriptPath = RunnerScriptPath,
        };
    }
}
