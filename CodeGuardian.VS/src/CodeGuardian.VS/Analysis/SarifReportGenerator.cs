using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Gera relatório no formato SARIF 2.1.0 a partir de um GuardianResult.
    /// SARIF é consumido nativamente por GitHub Actions (Security > Code Scanning)
    /// e Azure DevOps Pipelines, permitindo monitorar tendências de qualidade no CI/CD.
    /// </summary>
    public static class SarifReportGenerator
    {
        private const string SchemaUri   = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json";
        private const string ToolName    = "Code Guardian";
        private const string ToolVersion = "1.0.6";
        private const string InfoUri     = "https://github.com/cygnusforge/codeguardian";

        /// <summary>
        /// Contexto opcional de execução — metadados para monitoramento no CI/CD.
        /// </summary>
        public class ExecutionContext
        {
            /// <summary>Caminho raiz do repositório (usado para tornar URIs relativas).</summary>
            public string? RepositoryRoot { get; set; }

            /// <summary>Branch git atual (ex: main, feature/x).</summary>
            public string? GitBranch { get; set; }

            /// <summary>Hash do commit git (SHA curto ou longo).</summary>
            public string? GitCommit { get; set; }

            /// <summary>URL do repositório remoto (ex: https://github.com/org/repo).</summary>
            public string? RepositoryUrl { get; set; }

            /// <summary>ID único desta execução — útil para correlacionar runs no CI.</summary>
            public string RunId { get; set; } = Guid.NewGuid().ToString("N").Substring(0, 8);
        }

        // ── Ponto de entrada ───────────────────────────────────────────────

        /// <summary>
        /// Gera o JSON SARIF 2.1.0 completo.
        /// </summary>
        /// <param name="resultado">Resultado retornado pelo runner.py.</param>
        /// <param name="ctx">Metadados de contexto de execução (opcional).</param>
        /// <returns>JSON SARIF serializado como string UTF-8.</returns>
        public static string Gerar(GuardianResult resultado, ExecutionContext? ctx = null)
        {
            var rules   = ExtrairRegras(resultado);
            var results = ExtrairResultados(resultado, ctx?.RepositoryRoot);

            var run = new
            {
                automationDetails = new
                {
                    id          = $"code-guardian/{ctx?.RunId ?? Guid.NewGuid().ToString("N").Substring(0, 8)}",
                    description = new { text = "Análise estática pelo Code Guardian" }
                },
                tool = new
                {
                    driver = new
                    {
                        name            = ToolName,
                        version         = ToolVersion,
                        informationUri  = InfoUri,
                        rules           = rules
                    }
                },
                results = results,
                properties = CriarPropriedadesDeRun(resultado, ctx)
            };

            var sarif = new
            {
                version  = "2.1.0",
                schema   = SchemaUri,
                runs     = new[] { run }
            };

            return JsonConvert.SerializeObject(sarif, Formatting.Indented);
        }

        /// <summary>
        /// Salva o relatório SARIF em disco e retorna o caminho do arquivo gerado.
        /// Por convenção, o arquivo é salvo em <paramref name="outputDir"/>/.codeguardian/guardian-report.sarif.
        /// </summary>
        public static string SalvarArquivo(GuardianResult resultado, string outputDir, ExecutionContext? ctx = null)
        {
            var guardianDir = Path.Combine(outputDir, ".codeguardian");
            Directory.CreateDirectory(guardianDir);

            var caminhoSarif = Path.Combine(guardianDir, "guardian-report.sarif");
            File.WriteAllText(caminhoSarif, Gerar(resultado, ctx), new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));

            SalvarResumoMonitoramento(resultado, guardianDir, ctx);

            return caminhoSarif;
        }

        // ── Construção das regras (driver.rules) ───────────────────────────

        private static List<object> ExtrairRegras(GuardianResult resultado)
        {
            var regrasPorId = new Dictionary<string, (string categoria, string severidade, string mensagemExemplo)>();

            foreach (var file in resultado.Files)
            {
                foreach (var issue in file.Issues)
                {
                    if (!string.IsNullOrEmpty(issue.RuleId) && !regrasPorId.ContainsKey(issue.RuleId))
                        regrasPorId[issue.RuleId] = (issue.Category, issue.Severity, issue.Message);
                }
            }

            var regras = new List<object>();
            foreach (var kv in regrasPorId)
            {
                var (categoria, severidade, mensagem) = kv.Value;
                regras.Add(new
                {
                    id = kv.Key,
                    name = NormalizarNomeRegra(kv.Key),
                    shortDescription = new { text = MontarDescricaoRegra(kv.Key, categoria) },
                    fullDescription  = new { text = mensagem },
                    defaultConfiguration = new
                    {
                        level = MapearNivelSarif(severidade)
                    },
                    properties = new
                    {
                        tags = new[] { categoria.ToLowerInvariant() },
                        precision = "medium",
                        @problem_severity = severidade.ToLowerInvariant()
                    }
                });
            }

            return regras;
        }

        // ── Construção dos resultados (results[]) ──────────────────────────

        private static List<object> ExtrairResultados(GuardianResult resultado, string? repositoryRoot)
        {
            var resultados = new List<object>();

            foreach (var file in resultado.Files)
            {
                foreach (var issue in file.Issues)
                {
                    var uriArquivo = CriarUriArquivo(issue.File, repositoryRoot);

                    resultados.Add(new
                    {
                        ruleId  = issue.RuleId,
                        level   = MapearNivelSarif(issue.Severity),
                        message = new { text = issue.Message },
                        locations = new[]
                        {
                            new
                            {
                                physicalLocation = new
                                {
                                    artifactLocation = new
                                    {
                                        uri       = uriArquivo.uri,
                                        uriBaseId = uriArquivo.baseId
                                    },
                                    region = new { startLine = Math.Max(1, issue.Line) }
                                }
                            }
                        },
                        properties = new
                        {
                            severity = issue.Severity.ToLowerInvariant(),
                            category = issue.Category,
                            source   = issue.Source
                        }
                    });
                }
            }

            return resultados;
        }

        // ── Propriedades do run — metadados para monitoramento ─────────────

        private static object CriarPropriedadesDeRun(GuardianResult resultado, ExecutionContext? ctx)
        {
            var props = new Dictionary<string, object>
            {
                ["riskScore"]          = resultado.RiskScore,
                ["riskLabel"]          = resultado.RiskLabel,
                ["hasBlockers"]        = resultado.HasBlockers,
                ["analysisTimestamp"]  = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                ["totalFiles"]         = resultado.Files.Count,
                ["summary"] = new
                {
                    critical = resultado.Summary.Critical,
                    error    = resultado.Summary.Error,
                    warning  = resultado.Summary.Warning,
                    info     = resultado.Summary.Info,
                    total    = resultado.Summary.Critical + resultado.Summary.Error
                              + resultado.Summary.Warning + resultado.Summary.Info
                }
            };

            if (ctx != null)
            {
                if (!string.IsNullOrEmpty(ctx.GitBranch))     props["gitBranch"]     = ctx.GitBranch!;
                if (!string.IsNullOrEmpty(ctx.GitCommit))     props["gitCommit"]     = ctx.GitCommit!;
                if (!string.IsNullOrEmpty(ctx.RepositoryUrl)) props["repositoryUrl"] = ctx.RepositoryUrl!;
                props["runId"] = ctx.RunId;
            }

            return props;
        }

        // ── Arquivo de resumo para monitoramento externo ───────────────────

        /// <summary>
        /// Salva um JSON compacto de resumo em .codeguardian/guardian-metrics.json.
        /// Acumula histórico de execuções para análise de tendência.
        /// </summary>
        private static void SalvarResumoMonitoramento(GuardianResult resultado, string guardianDir, ExecutionContext? ctx)
        {
            var caminhoMetrics = Path.Combine(guardianDir, "guardian-metrics.json");

            var entradas = CarregarHistorico(caminhoMetrics);

            entradas.Add(new
            {
                timestamp  = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                riskScore  = resultado.RiskScore,
                riskLabel  = resultado.RiskLabel,
                hasBlockers = resultado.HasBlockers,
                critical   = resultado.Summary.Critical,
                error      = resultado.Summary.Error,
                warning    = resultado.Summary.Warning,
                info       = resultado.Summary.Info,
                totalFiles = resultado.Files.Count,
                gitBranch  = ctx?.GitBranch,
                gitCommit  = ctx?.GitCommit,
                runId      = ctx?.RunId
            });

            // Manter últimas 100 execuções
            if (entradas.Count > 100)
                entradas.RemoveRange(0, entradas.Count - 100);

            File.WriteAllText(
                caminhoMetrics,
                JsonConvert.SerializeObject(new { runs = entradas }, Formatting.Indented),
                new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
        }

        private static List<dynamic> CarregarHistorico(string caminho)
        {
            try
            {
                if (!File.Exists(caminho))
                    return new List<dynamic>();

                var json = File.ReadAllText(caminho);
                var obj  = JsonConvert.DeserializeObject<dynamic>(json);
                var runs = obj?.runs as Newtonsoft.Json.Linq.JArray;
                if (runs == null)
                    return new List<dynamic>();

                return runs.ToObject<List<dynamic>>() ?? new List<dynamic>();
            }
            catch
            {
                return new List<dynamic>();
            }
        }

        // ── Helpers ────────────────────────────────────────────────────────

        /// <summary>
        /// Mapeia severidade do CodeGuardian para nível SARIF.
        /// critical/error → error | warning → warning | info → note
        /// </summary>
        private static string MapearNivelSarif(string severity)
        {
            return severity.ToLowerInvariant() switch
            {
                "critical" => "error",
                "error"    => "error",
                "warning"  => "warning",
                "info"     => "note",
                _          => "warning"
            };
        }

        /// <summary>
        /// Cria URI do arquivo para o SARIF. Se possível, torna relativa à raiz do repositório.
        /// </summary>
        private static (string uri, string baseId) CriarUriArquivo(string filePath, string? repositoryRoot)
        {
            if (!string.IsNullOrEmpty(repositoryRoot) && filePath.StartsWith(repositoryRoot, StringComparison.OrdinalIgnoreCase))
            {
                var relativo = filePath.Substring(repositoryRoot!.Length).TrimStart('\\', '/').Replace('\\', '/');
                return (relativo, "%SRCROOT%");
            }

            var uri = new Uri(filePath).AbsoluteUri;
            return (uri, string.Empty);
        }

        private static string NormalizarNomeRegra(string ruleId)
        {
            // "SEC001" → "Sec001" (PascalCase compatível com SARIF)
            if (string.IsNullOrEmpty(ruleId))
                return ruleId;

            var partes = ruleId.Split(new[] { '_', '-', ' ' }, StringSplitOptions.RemoveEmptyEntries);
            var sb = new StringBuilder();
            foreach (var p in partes)
                sb.Append(char.ToUpperInvariant(p[0])).Append(p.Substring(1).ToLowerInvariant());
            return sb.ToString();
        }

        private static string MontarDescricaoRegra(string ruleId, string categoria)
        {
            if (!string.IsNullOrEmpty(categoria))
                return $"[{categoria}] {ruleId}";
            return ruleId;
        }
    }
}
