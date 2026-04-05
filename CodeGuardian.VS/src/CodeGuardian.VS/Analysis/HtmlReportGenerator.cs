using System;
using System.Text;
using CodeGuardian.VS.Analysis;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Gera um relatório HTML auto-contido com os resultados de análise do Code Guardian.
    /// Não possui dependências externas — usa apenas StringBuilder.
    /// </summary>
    public static class HtmlReportGenerator
    {
        /// <summary>
        /// Gera o HTML completo do relatório de análise.
        /// </summary>
        /// <param name="resultado">Resultado de análise retornado pelo runner.py.</param>
        /// <returns>String HTML auto-contida, pronta para salvar em arquivo e abrir no navegador.</returns>
        public static string Gerar(GuardianResult resultado)
        {
            var sb = new StringBuilder();
            var timestamp = DateTime.Now.ToString("dd/MM/yyyy HH:mm:ss");

            AppendCabecalho(sb, timestamp);
            AppendCardResumo(sb, resultado);
            AppendTabelaMetricas(sb, resultado);
            AppendTabelaIssues(sb, resultado);
            AppendRodape(sb);

            return sb.ToString();
        }

        // -----------------------------------------------------------------------
        // Seções do relatório
        // -----------------------------------------------------------------------

        private static void AppendCabecalho(StringBuilder sb, string timestamp)
        {
            sb.AppendLine("<!DOCTYPE html>");
            sb.AppendLine("<html lang=\"pt-BR\">");
            sb.AppendLine("<head>");
            sb.AppendLine("  <meta charset=\"UTF-8\" />");
            sb.AppendLine("  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />");
            sb.AppendLine("  <title>Code Guardian — Relatório de Análise</title>");
            sb.AppendLine("  <style>");
            AppendEstilos(sb);
            sb.AppendLine("  </style>");
            sb.AppendLine("</head>");
            sb.AppendLine("<body>");
            sb.AppendLine("  <div class=\"container\">");
            sb.AppendLine("    <header>");

            // Logo embutida como base64 para o relatório ser auto-contido
            var logoSrc = CarregarLogoBase64();
            if (logoSrc.Length > 0)
                sb.AppendLine($"      <img src=\"{logoSrc}\" alt=\"Code Guardian\" class=\"logo\" />");

            sb.AppendLine("      <p class=\"timestamp\">Gerado em " + EscapeHtml(timestamp) + "</p>");
            sb.AppendLine("    </header>");
        }

        /// <summary>
        /// Lê o logo do diretório da extensão e retorna como data URL base64.
        /// </summary>
        private static string CarregarLogoBase64()
        {
            try
            {
                var assemblyDir = System.IO.Path.GetDirectoryName(
                    typeof(HtmlReportGenerator).Assembly.Location);
                if (assemblyDir == null) return string.Empty;

                var logoPath = System.IO.Path.Combine(assemblyDir, "Resources", "logo-codeguardian.png");
                if (!System.IO.File.Exists(logoPath)) return string.Empty;

                var bytes = System.IO.File.ReadAllBytes(logoPath);
                return "data:image/png;base64," + Convert.ToBase64String(bytes);
            }
            catch
            {
                return string.Empty;
            }
        }

        private static void AppendCardResumo(StringBuilder sb, GuardianResult resultado)
        {
            var corRisco = CorRisco(resultado.RiskScore);
            sb.AppendLine("    <section class=\"section\">");
            sb.AppendLine("      <h2>Resumo</h2>");
            sb.AppendLine("      <div class=\"cards-resumo\">");
            sb.AppendLine("        <div class=\"card\">");
            sb.AppendLine($"          <span class=\"risk-score\" style=\"color:{corRisco}\">{resultado.RiskScore}</span>");
            sb.AppendLine($"          <span class=\"risk-label\" style=\"color:{corRisco}\">{EscapeHtml(resultado.RiskLabel)}</span>");
            sb.AppendLine("          <span class=\"risk-sub\">Risk Score (0–100)</span>");
            sb.AppendLine("        </div>");

            AppendCardContador(sb, "CRITICAL", resultado.Summary.Critical, "#E74C3C");
            AppendCardContador(sb, "ERROR",    resultado.Summary.Error,    "#E67E22");
            AppendCardContador(sb, "WARNING",  resultado.Summary.Warning,  "#F1C40F");
            AppendCardContador(sb, "INFO",     resultado.Summary.Info,     "#3498DB");

            sb.AppendLine("      </div>");
            sb.AppendLine("    </section>");
        }

        private static void AppendCardContador(StringBuilder sb, string label, int count, string cor)
        {
            sb.AppendLine("        <div class=\"card\">");
            sb.AppendLine($"          <span class=\"count-valor\" style=\"color:{cor}\">{count}</span>");
            sb.AppendLine($"          <span class=\"count-label\" style=\"color:{cor}\">{label}</span>");
            sb.AppendLine("        </div>");
        }

        private static void AppendTabelaMetricas(StringBuilder sb, GuardianResult resultado)
        {
            sb.AppendLine("    <section class=\"section\">");
            sb.AppendLine("      <h2>Métricas por Arquivo</h2>");

            if (resultado.Files.Count == 0)
            {
                sb.AppendLine("      <p class=\"vazio\">Nenhum arquivo analisado.</p>");
                sb.AppendLine("    </section>");
                return;
            }

            sb.AppendLine("      <table>");
            sb.AppendLine("        <thead>");
            sb.AppendLine("          <tr>");
            sb.AppendLine("            <th>Arquivo</th>");
            sb.AppendLine("            <th>Total Linhas</th>");
            sb.AppendLine("            <th>Maior Método</th>");
            sb.AppendLine("            <th>Nesting Máx.</th>");
            sb.AppendLine("            <th>Deps (ctor)</th>");
            sb.AppendLine("          </tr>");
            sb.AppendLine("        </thead>");
            sb.AppendLine("        <tbody>");

            foreach (var fileResult in resultado.Files)
            {
                if (fileResult.Metrics == null)
                    continue;

                var m = fileResult.Metrics;
                var nomeArquivo = System.IO.Path.GetFileName(fileResult.File);

                sb.AppendLine("          <tr>");
                sb.AppendLine($"            <td title=\"{EscapeHtml(fileResult.File)}\">{EscapeHtml(nomeArquivo)}</td>");
                sb.AppendLine($"            <td class=\"{ClasseMetrica(m.TotalLines, 300)}\">{m.TotalLines}</td>");
                sb.AppendLine($"            <td class=\"{ClasseMetrica(m.MaxMethodLines, 30)}\">{m.MaxMethodLines}</td>");
                sb.AppendLine($"            <td class=\"{ClasseMetrica(m.MaxNesting, 5)}\">{m.MaxNesting}</td>");
                sb.AppendLine($"            <td class=\"{ClasseMetrica(m.ConstructorDeps, 5)}\">{m.ConstructorDeps}</td>");
                sb.AppendLine("          </tr>");
            }

            sb.AppendLine("        </tbody>");
            sb.AppendLine("      </table>");
            sb.AppendLine("    </section>");
        }

        private static void AppendTabelaIssues(StringBuilder sb, GuardianResult resultado)
        {
            sb.AppendLine("    <section class=\"section\">");
            sb.AppendLine("      <h2>Issues Encontrados</h2>");

            // Contar total de issues
            var totalIssues = 0;
            foreach (var f in resultado.Files)
                totalIssues += f.Issues.Count;

            if (totalIssues == 0)
            {
                sb.AppendLine("      <p class=\"vazio\">Nenhum issue encontrado.</p>");
                sb.AppendLine("    </section>");
                return;
            }

            sb.AppendLine("      <table>");
            sb.AppendLine("        <thead>");
            sb.AppendLine("          <tr>");
            sb.AppendLine("            <th>Sev.</th>");
            sb.AppendLine("            <th>Rule ID</th>");
            sb.AppendLine("            <th>Categoria</th>");
            sb.AppendLine("            <th>Mensagem</th>");
            sb.AppendLine("            <th>Arquivo : Linha</th>");
            sb.AppendLine("          </tr>");
            sb.AppendLine("        </thead>");
            sb.AppendLine("        <tbody>");

            foreach (var fileResult in resultado.Files)
            {
                foreach (var issue in fileResult.Issues)
                {
                    var nomeArquivo = System.IO.Path.GetFileName(issue.File);
                    var cor = CorSeveridade(issue.Severity);
                    var severityLabel = issue.Severity.ToUpperInvariant();

                    sb.AppendLine("          <tr>");
                    sb.AppendLine($"            <td><span class=\"badge\" style=\"background:{cor}\">{EscapeHtml(severityLabel)}</span></td>");
                    sb.AppendLine($"            <td class=\"rule-id\">{EscapeHtml(issue.RuleId)}</td>");
                    sb.AppendLine($"            <td>{EscapeHtml(issue.Category)}</td>");
                    sb.AppendLine($"            <td>{EscapeHtml(issue.Message)}</td>");
                    sb.AppendLine($"            <td title=\"{EscapeHtml(issue.File)}\" class=\"arquivo-linha\">{EscapeHtml(nomeArquivo)} : {issue.Line}</td>");
                    sb.AppendLine("          </tr>");
                }
            }

            sb.AppendLine("        </tbody>");
            sb.AppendLine("      </table>");
            sb.AppendLine("    </section>");
        }

        private static void AppendRodape(StringBuilder sb)
        {
            sb.AppendLine("  </div>");
            sb.AppendLine("  <footer>");
            sb.AppendLine("    <p>Code Guardian &mdash; Análise automatizada de código</p>");
            sb.AppendLine("  </footer>");
            sb.AppendLine("</body>");
            sb.AppendLine("</html>");
        }

        // -----------------------------------------------------------------------
        // CSS inline (tema escuro)
        // -----------------------------------------------------------------------

        private static void AppendEstilos(StringBuilder sb)
        {
            sb.AppendLine(@"
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #1e1e1e;
      color: #cccccc;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      font-size: 14px;
      line-height: 1.5;
    }
    .container { max-width: 1100px; margin: 0 auto; padding: 24px 16px; }
    header { margin-bottom: 24px; }
    header .logo { height: 56px; margin-bottom: 10px; display: block; }
    header h1 {
      font-size: 22px;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 4px;
    }
    .timestamp { font-size: 12px; color: #888888; }
    .section { margin-bottom: 32px; }
    .section h2 {
      font-size: 13px;
      font-weight: 700;
      color: #aaaaaa;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }
    /* Cards de resumo */
    .cards-resumo {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .card {
      background: #2d2d2d;
      border-radius: 6px;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 110px;
    }
    .risk-score { font-size: 42px; font-weight: 700; line-height: 1; }
    .risk-label { font-size: 15px; font-weight: 700; margin-top: 4px; }
    .risk-sub { font-size: 11px; color: #888888; margin-top: 4px; }
    .count-valor { font-size: 32px; font-weight: 700; line-height: 1; }
    .count-label { font-size: 12px; font-weight: 700; margin-top: 6px; letter-spacing: 0.06em; }
    /* Tabelas */
    table {
      width: 100%;
      border-collapse: collapse;
      background: #2d2d2d;
      border-radius: 6px;
      overflow: hidden;
    }
    th {
      background: #252525;
      color: #aaaaaa;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 10px 12px;
      text-align: left;
    }
    td {
      padding: 8px 12px;
      border-bottom: 1px solid #333333;
      color: #cccccc;
      vertical-align: top;
    }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #333333; }
    .metrica-ok { color: #2ecc71; }
    .metrica-aviso { color: #e67e22; }
    /* Badge de severidade */
    .badge {
      display: inline-block;
      padding: 2px 7px;
      border-radius: 3px;
      font-size: 10px;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: 0.05em;
      white-space: nowrap;
    }
    .rule-id { font-family: monospace; font-size: 12px; white-space: nowrap; }
    .arquivo-linha { font-family: monospace; font-size: 12px; white-space: nowrap; color: #888888; }
    .vazio { color: #666666; font-style: italic; }
    footer {
      margin-top: 40px;
      text-align: center;
      font-size: 12px;
      color: #555555;
      padding: 16px 0;
      border-top: 1px solid #333333;
    }
");
        }

        // -----------------------------------------------------------------------
        // Utilitários
        // -----------------------------------------------------------------------

        private static string CorSeveridade(string severity)
        {
            var upper = severity.ToUpperInvariant();
            if (upper == "CRITICAL") return "#E74C3C";
            if (upper == "ERROR")    return "#E67E22";
            if (upper == "WARNING")  return "#F1C40F";
            return "#3498DB";
        }

        private static string CorRisco(int score)
        {
            if (score <= 10) return "#2ECC71";
            if (score <= 30) return "#F1C40F";
            if (score <= 60) return "#E67E22";
            return "#E74C3C";
        }

        private static string ClasseMetrica(int valor, int limite)
            => valor > limite ? "metrica-aviso" : "metrica-ok";

        private static string EscapeHtml(string texto)
        {
            if (string.IsNullOrEmpty(texto))
                return string.Empty;

            return texto
                .Replace("&", "&amp;")
                .Replace("<", "&lt;")
                .Replace(">", "&gt;")
                .Replace("\"", "&quot;")
                .Replace("'", "&#39;");
        }
    }
}
