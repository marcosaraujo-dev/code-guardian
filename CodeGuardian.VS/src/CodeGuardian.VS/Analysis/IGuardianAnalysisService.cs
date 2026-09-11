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
        /// Disparado quando a análise falha (Python ausente, runner.py não encontrado, timeout, etc.).
        /// </summary>
        event EventHandler<AnalysisFailedEventArgs> AnalysisFailed;

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

        /// <summary>
        /// Sobrepõe a configuração RulesOnly para esta sessão.
        /// null = respeitar configuração de Tools > Options.
        /// </summary>
        void SetRulesOnlyOverride(bool? valor);

        /// <summary>
        /// Executa scan apenas nos arquivos modificados desde o último commit (git diff).
        /// </summary>
        Task AnalyzeIncrementalAsync(string solutionDir, CancellationToken ct = default);

        /// <summary>
        /// Disparado durante o scan de solution com o progresso atual.
        /// </summary>
        event EventHandler<ScanProgressEventArgs> ScanProgress;
    }

    /// <summary>
    /// Progresso do scan de solution.
    /// </summary>
    public class ScanProgressEventArgs : EventArgs
    {
        public int    ArquivoAtual  { get; set; }
        public int    TotalArquivos { get; set; }
        public string NomeArquivo  { get; set; } = string.Empty;

        public string Texto => TotalArquivos > 0
            ? $"Arquivo {ArquivoAtual} de {TotalArquivos} — {NomeArquivo}"
            : $"Analisando {NomeArquivo}...";
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

    /// <summary>
    /// Tipo do erro que impediu a análise.
    /// </summary>
    public enum AnalysisErrorType
    {
        PythonNotFound,
        RunnerNotFound,
        Timeout,
        ScriptError,
        Unknown
    }

    /// <summary>
    /// Argumentos do evento AnalysisFailed.
    /// </summary>
    public class AnalysisFailedEventArgs : EventArgs
    {
        public AnalysisErrorType ErrorType    { get; set; }
        public string            ErrorMessage { get; set; } = string.Empty;
    }
}
