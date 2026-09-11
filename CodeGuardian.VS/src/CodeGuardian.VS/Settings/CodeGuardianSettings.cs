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

        /// <summary>Provider primário de IA: gemini, claude, openai, ollama.</summary>
        public string IAProviderPrimario { get; set; } = "ollama";

        /// <summary>Provider fallback quando o primário falha: gemini, claude, openai, ollama, none.</summary>
        public string IAProviderFallback { get; set; } = "none";

        /// <summary>Chave de API do Google Gemini (injetada como GEMINI_API_KEY).</summary>
        public string GeminiApiKey { get; set; } = string.Empty;

        /// <summary>Chave de API da Anthropic/Claude (injetada como ANTHROPIC_API_KEY).</summary>
        public string ClaudeApiKey { get; set; } = string.Empty;

        /// <summary>Chave de API da OpenAI (injetada como OPENAI_API_KEY).</summary>
        public string OpenAIApiKey { get; set; } = string.Empty;

        /// <summary>URL do servidor Ollama local.</summary>
        public string OllamaUrl { get; set; } = "http://localhost:11434";

        /// <summary>Modelo Ollama a usar.</summary>
        public string OllamaModel { get; set; } = "qwen2.5-coder:32b";

        /// <summary>Configurações com valores padrão para uso quando o package não está disponível.</summary>
        public static CodeGuardianSettings Padrao => new CodeGuardianSettings();
    }
}
