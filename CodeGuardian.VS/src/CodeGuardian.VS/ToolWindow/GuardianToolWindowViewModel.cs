using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Media;
using CodeGuardian.VS.Analysis;
using Microsoft.VisualStudio.Shell;

namespace CodeGuardian.VS.ToolWindow
{
    /// <summary>
    /// ViewModel da Tool Window do Code Guardian.
    /// Subscreve AnalysisCompleted e expõe dados para o WPF via INotifyPropertyChanged.
    /// </summary>
    public sealed class GuardianToolWindowViewModel : INotifyPropertyChanged, IDisposable
    {
        private readonly IGuardianAnalysisService? _analysisService;

        private int _riskScore;
        private string _riskLabel = "Nenhuma análise";
        private Brush _riskColor = Brushes.Gray;
        private double _riskProgress;
        private int _countCritical;
        private int _countError;
        private int _countWarning;
        private int _countInfo;
        private bool _isAnalyzing;
        private string _statusMessage = "Pronto";

        public int RiskScore
        {
            get => _riskScore;
            private set { _riskScore = value; OnPropertyChanged(); }
        }

        public string RiskLabel
        {
            get => _riskLabel;
            private set { _riskLabel = value; OnPropertyChanged(); }
        }

        public Brush RiskColor
        {
            get => _riskColor;
            private set { _riskColor = value; OnPropertyChanged(); }
        }

        /// <summary>Progresso de 0 a 100 para a barra visual de risco.</summary>
        public double RiskProgress
        {
            get => _riskProgress;
            private set { _riskProgress = value; OnPropertyChanged(); }
        }

        public int CountCritical
        {
            get => _countCritical;
            private set { _countCritical = value; OnPropertyChanged(); }
        }

        public int CountError
        {
            get => _countError;
            private set { _countError = value; OnPropertyChanged(); }
        }

        public int CountWarning
        {
            get => _countWarning;
            private set { _countWarning = value; OnPropertyChanged(); }
        }

        public int CountInfo
        {
            get => _countInfo;
            private set { _countInfo = value; OnPropertyChanged(); }
        }

        public bool IsAnalyzing
        {
            get => _isAnalyzing;
            private set { _isAnalyzing = value; OnPropertyChanged(); }
        }

        public string StatusMessage
        {
            get => _statusMessage;
            private set { _statusMessage = value; OnPropertyChanged(); }
        }

        /// <summary>Métricas por arquivo para o TreeView expansível.</summary>
        public ObservableCollection<FileMetricsViewModel> FileMetrics { get; }
            = new ObservableCollection<FileMetricsViewModel>();

        /// <summary>Lista de issues individuais para exibição na tool window.</summary>
        public ObservableCollection<IssueViewModel> Issues { get; }
            = new ObservableCollection<IssueViewModel>();

        /// <summary>Último resultado de análise — usado para gerar o relatório HTML.</summary>
        private GuardianResult? _ultimoResultado;
        public GuardianResult? UltimoResultado => _ultimoResultado;

        public GuardianToolWindowViewModel(IGuardianAnalysisService? analysisService)
        {
            _analysisService = analysisService;
            if (_analysisService != null)
                _analysisService.AnalysisCompleted += AoAnaliseCompleta;
        }

        public void MarcarAnalisando(string arquivo)
        {
            IsAnalyzing = true;
            StatusMessage = $"Analisando {System.IO.Path.GetFileName(arquivo)}...";
        }

        private void AoAnaliseCompleta(object sender, AnalysisCompletedEventArgs e)
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
                AtualizarComResultado(e.Result);
            });
        }

        public void AtualizarComResultado(GuardianResult resultado)
        {
            _ultimoResultado = resultado;

            RiskScore = resultado.RiskScore;
            RiskLabel = resultado.RiskLabel;
            RiskProgress = Math.Min(100, resultado.RiskScore);
            RiskColor = CalcularCorRisco(resultado.RiskScore);

            CountCritical = resultado.Summary.Critical;
            CountError = resultado.Summary.Error;
            CountWarning = resultado.Summary.Warning;
            CountInfo = resultado.Summary.Info;

            AtualizarMetricasDeArquivos(resultado);
            AtualizarListaDeIssues(resultado);

            IsAnalyzing = false;
            var total = CountCritical + CountError + CountWarning + CountInfo;
            StatusMessage = total == 0
                ? "Nenhum issue encontrado"
                : $"{total} issue(s) encontrado(s)";
        }

        private void AtualizarMetricasDeArquivos(GuardianResult resultado)
        {
            FileMetrics.Clear();

            foreach (var fileResult in resultado.Files)
            {
                if (fileResult.Metrics == null)
                    continue;

                FileMetrics.Add(new FileMetricsViewModel(fileResult));
            }
        }

        private void AtualizarListaDeIssues(GuardianResult resultado)
        {
            Issues.Clear();

            foreach (var fileResult in resultado.Files)
            {
                foreach (var issue in fileResult.Issues)
                {
                    Issues.Add(new IssueViewModel(issue));
                }
            }
        }

        /// <summary>
        /// Gera o relatório HTML e abre no navegador padrão.
        /// </summary>
        public void AbrirRelatorio(GuardianResult resultado)
        {
            var html = HtmlReportGenerator.Gerar(resultado);
            var tempPath = System.IO.Path.Combine(
                System.IO.Path.GetTempPath(),
                "code_guardian_report.html");
            System.IO.File.WriteAllText(tempPath, html, System.Text.Encoding.UTF8);
            System.Diagnostics.Process.Start(
                new System.Diagnostics.ProcessStartInfo(tempPath) { UseShellExecute = true });
        }

        private static Brush CalcularCorRisco(int score) =>
            score switch
            {
                <= 10 => new SolidColorBrush(Color.FromRgb(0x2E, 0xCC, 0x71)),   // verde
                <= 30 => new SolidColorBrush(Color.FromRgb(0xF1, 0xC4, 0x0F)),   // amarelo
                <= 60 => new SolidColorBrush(Color.FromRgb(0xE6, 0x7E, 0x22)),   // laranja
                _ => new SolidColorBrush(Color.FromRgb(0xE7, 0x4C, 0x3C)),        // vermelho
            };

        public void Dispose()
        {
            if (_analysisService != null)
                _analysisService.AnalysisCompleted -= AoAnaliseCompleta;
        }

        public event PropertyChangedEventHandler? PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string? nome = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nome));
    }

    /// <summary>
    /// ViewModel de um issue individual para exibição na lista da tool window.
    /// </summary>
    public sealed class IssueViewModel
    {
        /// <summary>Rótulo de severidade em maiúsculas (ex: "CRITICAL", "ERROR", "WARNING", "INFO").</summary>
        public string SeverityLabel { get; }

        /// <summary>Cor associada à severidade para o indicador visual.</summary>
        public Brush SeverityColor { get; }

        /// <summary>Identificador da regra que gerou o issue (ex: "SEC001").</summary>
        public string RuleId { get; }

        /// <summary>Mensagem descritiva do issue.</summary>
        public string Message { get; }

        /// <summary>Nome curto do arquivo (sem caminho).</summary>
        public string NomeArquivo { get; }

        /// <summary>Caminho completo do arquivo — exibido no tooltip.</summary>
        public string CaminhoCompleto { get; }

        /// <summary>Número da linha onde o issue foi encontrado.</summary>
        public int Line { get; }

        /// <summary>Categoria do issue (ex: "Security", "Performance").</summary>
        public string Category { get; }

        public IssueViewModel(IssueResult issue)
        {
            SeverityLabel = issue.Severity.ToUpperInvariant();
            RuleId = issue.RuleId;
            Message = issue.Message;
            CaminhoCompleto = issue.File;
            NomeArquivo = System.IO.Path.GetFileName(issue.File);
            Line = issue.Line;
            Category = issue.Category;

            SeverityColor = SeverityLabel switch
            {
                "CRITICAL" => new SolidColorBrush(Color.FromRgb(0xE7, 0x4C, 0x3C)),
                "ERROR"    => new SolidColorBrush(Color.FromRgb(0xE6, 0x7E, 0x22)),
                "WARNING"  => new SolidColorBrush(Color.FromRgb(0xF1, 0xC4, 0x0F)),
                _          => new SolidColorBrush(Color.FromRgb(0x34, 0x98, 0xDB)),
            };
        }
    }

    /// <summary>
    /// ViewModel de métricas de um arquivo individual para o TreeView.
    /// </summary>
    public sealed class FileMetricsViewModel
    {
        private const int LimiteLinhasMetodo = 30;
        private const int LimiteNesting = 5;
        private const int LimiteDependencias = 5;
        private const int LimiteTotalLinhas = 300;

        public string NomeArquivo { get; }
        public string CaminhoCompleto { get; }
        public int TotalLinhas { get; }
        public int MaxMethodLines { get; }
        public int MaxNesting { get; }
        public int ConstructorDeps { get; }

        public Brush CorTotalLinhas { get; }
        public Brush CorMaxMethod { get; }
        public Brush CorMaxNesting { get; }
        public Brush CorDependencias { get; }

        public FileMetricsViewModel(FileResult fileResult)
        {
            CaminhoCompleto = fileResult.File;
            NomeArquivo = System.IO.Path.GetFileName(fileResult.File);

            var m = fileResult.Metrics!;
            TotalLinhas = m.TotalLines;
            MaxMethodLines = m.MaxMethodLines;
            MaxNesting = m.MaxNesting;
            ConstructorDeps = m.ConstructorDeps;

            CorTotalLinhas = CorMetrica(TotalLinhas, LimiteTotalLinhas);
            CorMaxMethod = CorMetrica(MaxMethodLines, LimiteLinhasMetodo);
            CorMaxNesting = CorMetrica(MaxNesting, LimiteNesting);
            CorDependencias = CorMetrica(ConstructorDeps, LimiteDependencias);
        }

        private static Brush CorMetrica(int valor, int limite) =>
            valor > limite
                ? new SolidColorBrush(Color.FromRgb(0xE6, 0x7E, 0x22))   // laranja — acima do limite
                : new SolidColorBrush(Color.FromRgb(0x2E, 0xCC, 0x71));   // verde — dentro do limite
    }
}
