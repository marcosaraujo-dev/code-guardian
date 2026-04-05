using System.Collections.Generic;
using Newtonsoft.Json;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Espelho completo do JSON retornado pelo runner.py.
    /// </summary>
    public class GuardianResult
    {
        [JsonProperty("risk_score")]
        public int RiskScore { get; set; }

        [JsonProperty("risk_label")]
        public string RiskLabel { get; set; } = string.Empty;

        [JsonProperty("has_blockers")]
        public bool HasBlockers { get; set; }

        [JsonProperty("summary")]
        public SummaryResult Summary { get; set; } = new SummaryResult();

        [JsonProperty("files")]
        public List<FileResult> Files { get; set; } = new List<FileResult>();
    }

    /// <summary>
    /// Contadores de issues por severidade.
    /// </summary>
    public class SummaryResult
    {
        [JsonProperty("critical")]
        public int Critical { get; set; }

        [JsonProperty("error")]
        public int Error { get; set; }

        [JsonProperty("warning")]
        public int Warning { get; set; }

        [JsonProperty("info")]
        public int Info { get; set; }
    }

    /// <summary>
    /// Resultado de análise de um arquivo individual.
    /// </summary>
    public class FileResult
    {
        [JsonProperty("file")]
        public string File { get; set; } = string.Empty;

        [JsonProperty("issues")]
        public List<IssueResult> Issues { get; set; } = new List<IssueResult>();

        [JsonProperty("metrics")]
        public MetricsResult? Metrics { get; set; }
    }

    /// <summary>
    /// Issue individual encontrado pelo rule_engine ou pela IA.
    /// </summary>
    public class IssueResult
    {
        [JsonProperty("file")]
        public string File { get; set; } = string.Empty;

        [JsonProperty("line")]
        public int Line { get; set; }

        [JsonProperty("severity")]
        public string Severity { get; set; } = string.Empty;  // critical | error | warning | info

        [JsonProperty("category")]
        public string Category { get; set; } = string.Empty;

        [JsonProperty("rule_id")]
        public string RuleId { get; set; } = string.Empty;

        [JsonProperty("message")]
        public string Message { get; set; } = string.Empty;

        [JsonProperty("source")]
        public string Source { get; set; } = string.Empty;
    }

    /// <summary>
    /// Métricas de qualidade de código geradas pelo metrics.py.
    /// </summary>
    public class MetricsResult
    {
        [JsonProperty("total_lines")]
        public int TotalLines { get; set; }

        [JsonProperty("max_method_lines")]
        public int MaxMethodLines { get; set; }

        [JsonProperty("max_nesting")]
        public int MaxNesting { get; set; }

        [JsonProperty("constructor_deps")]
        public int ConstructorDeps { get; set; }
    }
}
