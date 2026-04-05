using System;
using System.Threading;
using System.Threading.Tasks;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Contrato do serviço central de análise do Code Guardian.
    /// </summary>
    public interface IGuardianAnalysisService
    {
        /// <summary>
        /// Disparado quando a análise de um arquivo ou da solution é concluída.
        /// </summary>
        event EventHandler<AnalysisCompletedEventArgs> AnalysisCompleted;

        /// <summary>
        /// Analisa um arquivo C# específico em background.
        /// </summary>
        Task AnalyzeFileAsync(string filePath, CancellationToken ct = default);

        /// <summary>
        /// Executa scan completo do diretório da solution.
        /// </summary>
        Task AnalyzeSolutionAsync(string solutionDir, CancellationToken ct = default);

        /// <summary>
        /// Retorna resultado em cache para um arquivo, ou null se expirado/inexistente.
        /// </summary>
        GuardianResult? GetCachedResult(string filePath);
    }

    /// <summary>
    /// Tipo marker para bridge MEF/AsyncPackage.
    /// Componentes MEF obtêm o serviço via ServiceProvider.GetService(typeof(SGuardianAnalysisService)).
    /// </summary>
    public class SGuardianAnalysisService { }

    /// <summary>
    /// Argumentos do evento AnalysisCompleted.
    /// </summary>
    public class AnalysisCompletedEventArgs : EventArgs
    {
        public string FilePath { get; set; } = string.Empty;
        public GuardianResult Result { get; set; } = new GuardianResult();
        public bool IsFullScan { get; set; }
    }
}
