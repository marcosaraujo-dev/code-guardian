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

        [Category("IA")]
        [DisplayName("Provider Primário")]
        [Description("Provider de IA para análise: gemini, claude, openai, ollama. Requer chave configurada abaixo.")]
        public string IAProviderPrimario { get; set; } = "ollama";

        [Category("IA")]
        [DisplayName("Provider Fallback")]
        [Description("Provider usado quando o primário falha: gemini, claude, openai, ollama, none.")]
        public string IAProviderFallback { get; set; } = "none";

        [Category("IA")]
        [DisplayName("Gemini API Key")]
        [Description("Chave de API do Google Gemini. Obtida em https://aistudio.google.com/app/apikey")]
        public string GeminiApiKey { get; set; } = string.Empty;

        [Category("IA")]
        [DisplayName("Claude API Key (Anthropic)")]
        [Description("Chave de API da Anthropic. Obtida em https://console.anthropic.com/")]
        public string ClaudeApiKey { get; set; } = string.Empty;

        [Category("IA")]
        [DisplayName("OpenAI API Key")]
        [Description("Chave de API da OpenAI. Obtida em https://platform.openai.com/api-keys")]
        public string OpenAIApiKey { get; set; } = string.Empty;

        [Category("IA")]
        [DisplayName("Ollama URL")]
        [Description("URL do servidor Ollama local. Padrão: http://localhost:11434")]
        public string OllamaUrl { get; set; } = "http://localhost:11434";

        [Category("IA")]
        [DisplayName("Ollama Modelo")]
        [Description("Modelo Ollama a usar. Ex: qwen2.5-coder:32b, codellama:13b, deepseek-coder:6.7b")]
        public string OllamaModel { get; set; } = "qwen2.5-coder:32b";

        /// <summary>
        /// Converte a página de opções em um POCO imutável para uso thread-safe.
        /// </summary>
        public CodeGuardianSettings ToSettings() => new CodeGuardianSettings
        {
            PythonExecutable       = PythonExecutable,
            AnalyzeOnSave          = AnalyzeOnSave,
            RulesOnly              = RulesOnly,
            MinimumSeverity        = MinimumSeverity,
            AnalysisTimeoutSeconds = AnalysisTimeoutSeconds,
            RunnerScriptPath       = RunnerScriptPath,
            IAProviderPrimario     = IAProviderPrimario,
            IAProviderFallback     = IAProviderFallback,
            GeminiApiKey           = GeminiApiKey,
            ClaudeApiKey           = ClaudeApiKey,
            OpenAIApiKey           = OpenAIApiKey,
            OllamaUrl              = OllamaUrl,
            OllamaModel            = OllamaModel,
        };
    }
}
