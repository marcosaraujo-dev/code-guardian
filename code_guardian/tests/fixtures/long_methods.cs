using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class ReportService
    {
        public async Task<string> GenerateFullReport(int userId, DateTime startDate, DateTime endDate)
        {
            // Este metodo tem mais de 30 linhas intencionalmente
            var report = new System.Text.StringBuilder();
            report.AppendLine("=== Relatorio Completo ===");
            report.AppendLine($"Usuario: {userId}");
            report.AppendLine($"Periodo: {startDate:yyyy-MM-dd} a {endDate:yyyy-MM-dd}");
            report.AppendLine("");

            // Secao 1
            report.AppendLine("--- Secao 1: Dados Gerais ---");
            report.AppendLine("Item 1: processando...");
            report.AppendLine("Item 2: processando...");
            report.AppendLine("Item 3: processando...");
            report.AppendLine("Item 4: processando...");
            report.AppendLine("Item 5: processando...");
            await Task.Delay(10);

            // Secao 2
            report.AppendLine("--- Secao 2: Estatisticas ---");
            report.AppendLine("Total de transacoes: calculando...");
            report.AppendLine("Valor total: calculando...");
            report.AppendLine("Media por transacao: calculando...");
            report.AppendLine("Maior transacao: calculando...");
            report.AppendLine("Menor transacao: calculando...");
            await Task.Delay(10);

            // Secao 3
            report.AppendLine("--- Secao 3: Resumo ---");
            report.AppendLine("Status geral: OK");
            report.AppendLine("Alertas: nenhum");
            report.AppendLine("Recomendacoes: nenhuma");
            await Task.Delay(10);

            // Secao 4
            report.AppendLine("--- Secao 4: Rodape ---");
            report.AppendLine($"Gerado em: {DateTime.UtcNow:yyyy-MM-dd HH:mm:ss}");
            report.AppendLine("Sistema: Code Guardian Reports");
            report.AppendLine("Versao: 1.0");
            report.AppendLine("=== Fim do Relatorio ===");

            return report.ToString();
        }
    }
}
