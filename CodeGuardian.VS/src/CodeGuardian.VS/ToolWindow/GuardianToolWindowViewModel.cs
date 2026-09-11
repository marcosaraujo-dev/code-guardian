using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows.Data;
using System.Windows.Media;
using CodeGuardian.VS.Analysis;
using CodeGuardian.VS.GitHooks;
using Microsoft.VisualStudio.Shell;
using Newtonsoft.Json.Linq;

namespace CodeGuardian.VS.ToolWindow
{
    /// <summary>
    /// ViewModel da Tool Window do Code Guardian.
    /// Subscreve AnalysisCompleted e expõe dados para o WPF via INotifyPropertyChanged.
    /// </summary>
    public sealed class GuardianToolWindowViewModel : INotifyPropertyChanged, IDisposable
    {
        private readonly IGuardianAnalysisService? _analysisService;
        private readonly HookInstallService?        _hookService;

        // ── Campos de analise ──────────────────────────────────────────────

        private int    _riskScore;
        private string _riskLabel   = "Nenhuma análise";
        private Brush  _riskColor   = Brushes.Gray;
        private double _riskProgress;
        private int    _countCritical;
        private int    _countError;
        private int    _countWarning;
        private int    _countInfo;
        private bool   _isAnalyzing;
        private string _statusMessage = "Pronto";

        // ── Campos de dependências ─────────────────────────────────────────

        private bool   _hasDependencyError;
        private string _dependencyErrorMessage = string.Empty;

        // ── Campos de histórico / tendência ───────────────────────────────

        private string _tendenciaLabel = string.Empty;
        private Brush  _tendenciaCor   = Brushes.Gray;

        // ── Campos de filtros de issues ────────────────────────────────────

        private string _filtroSeveridade      = "Todos";
        private string _filtroTexto           = string.Empty;
        private string _filtroSeveridadeUpper = "TODOS";
        private string _filtroTextoUpper      = string.Empty;
        private ICollectionView? _issuesView;

        // ── Brushes estáticas frozen — alocadas uma única vez, thread-safe para WPF ──

        private static Brush MakeFrozen(byte r, byte g, byte b)
        {
            var brush = new SolidColorBrush(Color.FromRgb(r, g, b));
            brush.Freeze();
            return brush;
        }

        private static readonly Brush _brushVerde    = MakeFrozen(0x2E, 0xCC, 0x71);
        private static readonly Brush _brushCinza    = MakeFrozen(0x88, 0x88, 0x88);
        private static readonly Brush _brushIAVerde  = MakeFrozen(0x27, 0xAE, 0x60);
        private static readonly Brush _brushIACinza  = MakeFrozen(0x44, 0x44, 0x44);
        private static readonly Brush _brushHookRed  = MakeFrozen(0xC0, 0x39, 0x2B);
        private static readonly Brush _brushAmarelo  = MakeFrozen(0xF1, 0xC4, 0x0F);
        private static readonly Brush _brushLaranja  = MakeFrozen(0xE6, 0x7E, 0x22);
        private static readonly Brush _brushVermelho = MakeFrozen(0xE7, 0x4C, 0x3C);

        // ── Campos de toggle IA ────────────────────────────────────────────

        private bool _usarIA;

        // ── Campos de dependências verificadas ────────────────────────────

        private bool _dependencyChecked;

        // ── Campos de git hooks ────────────────────────────────────────────

        private bool    _hookInstalado;
        private string? _gitDirAtual;
        private string? _solutionDirAtual;

        // ── Propriedades de analise ────────────────────────────────────────

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
            private set
            {
                _isAnalyzing = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(IsNotAnalyzing));
            }
        }

        /// <summary>Inverso de IsAnalyzing — usado para desabilitar botões durante a análise.</summary>
        public bool IsNotAnalyzing => !_isAnalyzing;

        public string StatusMessage
        {
            get => _statusMessage;
            private set { _statusMessage = value; OnPropertyChanged(); }
        }

        // ── Propriedades de dependências ───────────────────────────────────

        /// <summary>True quando Python ou runner.py não estão acessíveis.</summary>
        public bool HasDependencyError
        {
            get => _hasDependencyError;
            private set { _hasDependencyError = value; OnPropertyChanged(); }
        }

        /// <summary>Mensagem explicando qual dependência está faltando.</summary>
        public string DependencyErrorMessage
        {
            get => _dependencyErrorMessage;
            private set { _dependencyErrorMessage = value; OnPropertyChanged(); }
        }

        // ── Propriedades de tendência ──────────────────────────────────────

        /// <summary>Símbolo de tendência do Risk Score: ▼ melhorou, ▲ piorou, ─ estável.</summary>
        public string TendenciaLabel
        {
            get => _tendenciaLabel;
            private set { _tendenciaLabel = value; OnPropertyChanged(); }
        }

        /// <summary>Cor da tendência: verde (melhorou), vermelho (piorou), cinza (estável).</summary>
        public Brush TendenciaCor
        {
            get => _tendenciaCor;
            private set { _tendenciaCor = value; OnPropertyChanged(); }
        }

        // ── Propriedades de filtros ────────────────────────────────────────

        /// <summary>Vista filtrada da coleção Issues — use no binding da ListBox.</summary>
        public ICollectionView IssuesView
        {
            get
            {
                if (_issuesView == null)
                {
                    _issuesView = CollectionViewSource.GetDefaultView(Issues);
                    _issuesView.Filter = AplicarFiltro;
                }
                return _issuesView;
            }
        }

        /// <summary>Filtro por severidade: "Todos", "CRITICAL", "ERROR", "WARNING", "INFO".</summary>
        public string FiltroSeveridade
        {
            get => _filtroSeveridade;
            set
            {
                _filtroSeveridade      = value;
                _filtroSeveridadeUpper = value.ToUpperInvariant();
                OnPropertyChanged();
                _issuesView?.Refresh();
            }
        }

        /// <summary>Filtro por texto livre (mensagem, arquivo ou ruleId).</summary>
        public string FiltroTexto
        {
            get => _filtroTexto;
            set
            {
                _filtroTexto      = value;
                _filtroTextoUpper = value.ToUpperInvariant();
                OnPropertyChanged();
                _issuesView?.Refresh();
            }
        }

        private bool AplicarFiltro(object obj)
        {
            if (obj is not IssueViewModel issue)
                return false;

            var severidadeOk = _filtroSeveridadeUpper == "TODOS"
                               || issue.SeverityLabel == _filtroSeveridadeUpper;

            if (!severidadeOk)
                return false;

            if (string.IsNullOrEmpty(_filtroTextoUpper))
                return true;

            return issue.Message.ToUpperInvariant().IndexOf(_filtroTextoUpper, StringComparison.Ordinal) >= 0
                   || issue.NomeArquivo.ToUpperInvariant().IndexOf(_filtroTextoUpper, StringComparison.Ordinal) >= 0
                   || issue.RuleId.ToUpperInvariant().IndexOf(_filtroTextoUpper, StringComparison.Ordinal) >= 0;
        }

        // ── Propriedades de toggle IA ──────────────────────────────────────

        /// <summary>Quando true, habilita análise com IA (desativa rules-only) para esta sessão.</summary>
        public bool UsarIA
        {
            get => _usarIA;
            set
            {
                _usarIA = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(ToggleIALabel));
                OnPropertyChanged(nameof(ToggleIABackground));
                _analysisService?.SetRulesOnlyOverride(!value);
            }
        }

        public string ToggleIALabel      => _usarIA ? "IA: ON"  : "IA: OFF";
        public Brush  ToggleIABackground => _usarIA ? _brushIAVerde : _brushIACinza;

        // ── Propriedades de git hooks ──────────────────────────────────────

        /// <summary>Indica se os hooks do Code Guardian estao instalados no repositorio atual.</summary>
        public bool HookInstalado
        {
            get => _hookInstalado;
            set
            {
                _hookInstalado = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(HookStatusLabel));
                OnPropertyChanged(nameof(HookStatusColor));
                OnPropertyChanged(nameof(HookBotaoLabel));
                OnPropertyChanged(nameof(HookBotaoBackground));
            }
        }

        /// <summary>Texto do status do hook: "Ativo" ou "Inativo".</summary>
        public string HookStatusLabel => _hookInstalado ? "Ativo" : "Inativo";

        /// <summary>Cor do indicador de status do hook.</summary>
        public Brush HookStatusColor => _hookInstalado ? _brushVerde : _brushCinza;

        /// <summary>Label do botao de toggle: "Desabilitar" ou "Habilitar".</summary>
        public string HookBotaoLabel => _hookInstalado ? "Desabilitar" : "Habilitar";

        /// <summary>Cor de fundo do botao de toggle.</summary>
        public Brush HookBotaoBackground => _hookInstalado ? _brushHookRed : _brushIAVerde;

        // ── Colecoes ───────────────────────────────────────────────────────

        /// <summary>Métricas por arquivo para o TreeView expansível.</summary>
        public ObservableCollection<FileMetricsViewModel> FileMetrics { get; }
            = new ObservableCollection<FileMetricsViewModel>();

        /// <summary>Lista de issues individuais para exibição na tool window.</summary>
        public ObservableCollection<IssueViewModel> Issues { get; }
            = new ObservableCollection<IssueViewModel>();

        /// <summary>Último resultado de análise — usado para gerar o relatório HTML.</summary>
        private GuardianResult? _ultimoResultado;
        public GuardianResult? UltimoResultado => _ultimoResultado;

        // ── Construtor ─────────────────────────────────────────────────────

        public GuardianToolWindowViewModel(
            IGuardianAnalysisService? analysisService,
            HookInstallService?       hookService)
        {
            _analysisService = analysisService;
            _hookService     = hookService;

            if (_analysisService != null)
            {
                _analysisService.AnalysisCompleted += AoAnaliseCompleta;
                _analysisService.AnalysisFailed    += AoAnaliseFalhou;
                _analysisService.ScanProgress      += AoProgresso;
            }
        }

        // ── Metodos de git hooks ───────────────────────────────────────────

        /// <summary>
        /// Atualiza a propriedade HookInstalado consultando o servico de hooks.
        /// Deve ser chamado sempre que a solution mudar.
        /// </summary>
        public void AtualizarStatusHook(string? gitDir, string? solutionDir = null)
        {
            _gitDirAtual      = gitDir;
            _solutionDirAtual = solutionDir;
            HookInstalado     = gitDir != null
                                && _hookService != null
                                && _hookService.AreHooksInstalled(gitDir);
        }

        /// <summary>
        /// Instala ou remove os hooks conforme o estado atual.
        /// </summary>
        public async System.Threading.Tasks.Task ToggleHookAsync(string solutionDir)
        {
            if (_hookService == null)
                return;

            var gitDir = HookInstallService.EncontrarDiretorioGit(solutionDir);
            if (gitDir == null)
                return;

            if (HookInstalado)
                await _hookService.UninstallHooksAsync(gitDir);
            else
                await _hookService.InstallHooksAsync(gitDir);

            HookInstalado = _hookService.AreHooksInstalled(gitDir);
        }

        // ── Metodos de analise ─────────────────────────────────────────────

        /// <summary>
        /// Verifica se Python e o runner.py estão acessíveis e atualiza o banner de aviso.
        /// Deve ser chamado ao abrir a tool window.
        /// </summary>
        public async System.Threading.Tasks.Task VerificarDependenciasAsync(string? solutionDir = null)
        {
            if (_dependencyChecked) return;

            var status = await Analysis.DependencyChecker.CheckAsync(solutionDir).ConfigureAwait(false);
            _dependencyChecked = true;

            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

            if (!status.TudoOk)
            {
                HasDependencyError    = true;
                DependencyErrorMessage = status.MontarMensagemErro();
                StatusMessage          = "Dependências ausentes — veja o aviso acima";
            }
            else
            {
                HasDependencyError    = false;
                DependencyErrorMessage = string.Empty;
            }
        }

        /// <summary>Chamado pelo code-behind do botão "Analisar Arquivo".</summary>
        public async System.Threading.Tasks.Task AnalisarArquivoAsync(string? filePath)
        {
            if (_analysisService == null || IsAnalyzing)
                return;

            if (HasDependencyError)
            {
                StatusMessage = "Configure as dependências antes de analisar (veja o aviso acima)";
                return;
            }

            if (string.IsNullOrEmpty(filePath) || !filePath!.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
            {
                StatusMessage = "Nenhum arquivo .cs ativo no editor";
                return;
            }

            IsAnalyzing   = true;
            StatusMessage = $"Analisando {Path.GetFileName(filePath)}...";
            await _analysisService.AnalyzeFileAsync(filePath);
        }

        /// <summary>Chamado pelo code-behind do botão "Análise Incremental".</summary>
        public async System.Threading.Tasks.Task AnalisarIncrementalAsync(string? solutionDir)
        {
            if (_analysisService == null || IsAnalyzing)
                return;

            if (HasDependencyError)
            {
                StatusMessage = "Configure as dependências antes de analisar (veja o aviso acima)";
                return;
            }

            if (string.IsNullOrEmpty(solutionDir))
            {
                StatusMessage = "Nenhuma solution aberta";
                return;
            }

            IsAnalyzing   = true;
            StatusMessage = "Detectando arquivos modificados no git...";
            await _analysisService.AnalyzeIncrementalAsync(solutionDir!);
        }

        /// <summary>Chamado pelo code-behind do botão "Analisar Solution".</summary>
        public async System.Threading.Tasks.Task AnalisarSolucaoAsync(string? solutionDir)
        {
            if (_analysisService == null || IsAnalyzing)
                return;

            if (HasDependencyError)
            {
                StatusMessage = "Configure as dependências antes de analisar (veja o aviso acima)";
                return;
            }

            if (string.IsNullOrEmpty(solutionDir))
            {
                StatusMessage = "Nenhuma solution aberta";
                return;
            }

            IsAnalyzing   = true;
            StatusMessage = "Preparando varredura da solution...";
            await _analysisService.AnalyzeSolutionAsync(solutionDir!);
        }

        public void LimparAnalise()
        {
            Issues.Clear();
            FileMetrics.Clear();
            RiskScore    = 0;
            RiskLabel    = "Nenhuma análise";
            RiskProgress = 0;
            RiskColor    = Brushes.Gray;
            CountCritical = 0;
            CountError    = 0;
            CountWarning  = 0;
            CountInfo     = 0;
            TendenciaLabel = string.Empty;
            StatusMessage  = "Pronto";
            _ultimoResultado = null;
        }

        public void MarcarAnalisando(string arquivo)
        {
            IsAnalyzing   = true;
            StatusMessage = $"Analisando {Path.GetFileName(arquivo)}...";
        }

        public void AtualizarProgresso(ScanProgressEventArgs args)
        {
            IsAnalyzing   = true;
            StatusMessage = args.Texto;
        }

        private void AtualizarTendencia(int scoreAtual, string? solutionDir)
        {
            try
            {
                if (solutionDir == null) return;

                var metricsPath = Path.Combine(solutionDir, ".codeguardian", "guardian-metrics.json");
                if (!File.Exists(metricsPath)) return;

                var json   = File.ReadAllText(metricsPath);
                var doc    = Newtonsoft.Json.Linq.JObject.Parse(json);
                var runs   = doc["runs"] as JArray;
                if (runs == null || runs.Count < 2) return;

                var entradaAnterior = runs[runs.Count - 2];
                if (entradaAnterior == null) return;
                var scoreAnterior = entradaAnterior["riskScore"]?.Value<int>() ?? scoreAtual;
                var diff          = scoreAtual - scoreAnterior;

                if (diff < -2)
                {
                    TendenciaLabel = $"▼ {Math.Abs(diff)} pts";
                    TendenciaCor   = _brushVerde;
                }
                else if (diff > 2)
                {
                    TendenciaLabel = $"▲ {diff} pts";
                    TendenciaCor   = _brushVermelho;
                }
                else
                {
                    TendenciaLabel = "─ estável";
                    TendenciaCor   = _brushCinza;
                }
            }
            catch { /* histórico indisponível — sem tendência */ }
        }

        private void AoProgresso(object sender, ScanProgressEventArgs e)
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
                AtualizarProgresso(e);
            });
        }

        private void AoAnaliseFalhou(object sender, AnalysisFailedEventArgs e)
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                IsAnalyzing = false;

                StatusMessage = e.ErrorType switch
                {
                    AnalysisErrorType.PythonNotFound => "Python não encontrado — configure em Tools > Options > Code Guardian",
                    AnalysisErrorType.RunnerNotFound => "Scripts não encontrados — configure em Tools > Options > Code Guardian",
                    AnalysisErrorType.Timeout        => "Análise cancelada por timeout — aumente o limite em Options",
                    AnalysisErrorType.ScriptError    => "Erro ao executar o script — veja o Output Window",
                    _                                => e.ErrorMessage,
                };

                if (e.ErrorType is AnalysisErrorType.PythonNotFound or AnalysisErrorType.RunnerNotFound)
                {
                    HasDependencyError     = true;
                    DependencyErrorMessage = e.ErrorType == AnalysisErrorType.PythonNotFound
                        ? "Python não instalado ou não encontrado no PATH do sistema."
                        : "Scripts do Code Guardian não localizados no projeto.";
                }
            });
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

            RiskScore    = resultado.RiskScore;
            RiskLabel    = resultado.RiskLabel;
            RiskProgress = Math.Min(100, resultado.RiskScore);
            RiskColor    = CalcularCorRisco(resultado.RiskScore);

            CountCritical = resultado.Summary.Critical;
            CountError    = resultado.Summary.Error;
            CountWarning  = resultado.Summary.Warning;
            CountInfo     = resultado.Summary.Info;

            AtualizarMetricasDeArquivos(resultado);
            AtualizarListaDeIssues(resultado);

            IsAnalyzing = false;
            var total = CountCritical + CountError + CountWarning + CountInfo;
            StatusMessage = total == 0
                ? "Nenhum issue encontrado"
                : $"{total} issue(s) encontrado(s)";

            AtualizarTendencia(resultado.RiskScore, _solutionDirAtual);

            // Revalida status dos hooks apos analise (podem ter sido alterados externamente)
            if (_gitDirAtual != null)
                AtualizarStatusHook(_gitDirAtual);
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
            var html     = HtmlReportGenerator.Gerar(resultado);
            var tempPath = Path.Combine(Path.GetTempPath(), "code_guardian_report.html");
            File.WriteAllText(tempPath, html, System.Text.Encoding.UTF8);
            System.Diagnostics.Process.Start(
                new System.Diagnostics.ProcessStartInfo(tempPath) { UseShellExecute = true });
        }

        /// <summary>
        /// Exporta o resultado atual como SARIF 2.1.0 e acumula histórico de métricas.
        /// </summary>
        public async System.Threading.Tasks.Task ExportarSarifAsync(string? solutionDir)
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

            if (_ultimoResultado == null)
            {
                StatusMessage = "Execute uma análise antes de exportar o SARIF";
                return;
            }

            if (string.IsNullOrEmpty(solutionDir))
            {
                StatusMessage = "Nenhuma solution aberta";
                return;
            }

            var ctx = ColetarContextoGit(solutionDir!);
            ctx.RepositoryRoot = solutionDir;

            var caminhoSarif = SarifReportGenerator.SalvarArquivo(_ultimoResultado, solutionDir!, ctx);
            StatusMessage = $"SARIF exportado → .codeguardian/guardian-report.sarif";

            var abrir = System.Windows.MessageBox.Show(
                $"Relatório SARIF gerado com sucesso!\n\n{caminhoSarif}\n\n" +
                "O arquivo guardian-metrics.json com histórico de execuções também foi atualizado.\n\n" +
                "Deseja abrir a pasta?",
                "Code Guardian — SARIF exportado",
                System.Windows.MessageBoxButton.YesNo,
                System.Windows.MessageBoxImage.Information);

            if (abrir == System.Windows.MessageBoxResult.Yes)
                System.Diagnostics.Process.Start("explorer.exe", $"/select,\"{caminhoSarif}\"");
        }

        private static SarifReportGenerator.ExecutionContext ColetarContextoGit(string solutionDir)
        {
            var ctx = new SarifReportGenerator.ExecutionContext();
            try
            {
                ctx.GitBranch = ExecutarGit("rev-parse --abbrev-ref HEAD", solutionDir);
                ctx.GitCommit = ExecutarGit("rev-parse --short HEAD",      solutionDir);
                var remote = ExecutarGit("remote get-url origin",           solutionDir);
                if (!string.IsNullOrEmpty(remote))
                    ctx.RepositoryUrl = remote;
            }
            // guardian: suppress EMPTY_CATCH
            catch { }
            return ctx;
        }

        private static string? ExecutarGit(string args, string workingDir)
        {
            try
            {
                var psi = new System.Diagnostics.ProcessStartInfo("git", args)
                {
                    WorkingDirectory       = workingDir,
                    RedirectStandardOutput = true,
                    UseShellExecute        = false,
                    CreateNoWindow         = true
                };
                using var proc = System.Diagnostics.Process.Start(psi);
                var saida = proc?.StandardOutput.ReadToEnd()?.Trim();
                proc?.WaitForExit(3000);
                return string.IsNullOrEmpty(saida) ? null : saida;
            }
            catch { return null; }
        }

        private static Brush CalcularCorRisco(int score) =>
            score switch
            {
                <= 10 => _brushVerde,
                <= 30 => _brushAmarelo,
                <= 60 => _brushLaranja,
                _     => _brushVermelho,
            };

        public void Dispose()
        {
            if (_analysisService != null)
            {
                _analysisService.AnalysisCompleted -= AoAnaliseCompleta;
                _analysisService.AnalysisFailed    -= AoAnaliseFalhou;
                _analysisService.ScanProgress      -= AoProgresso;
            }
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
        // Brushes estáticas frozen — compartilhadas por todas as instâncias de IssueViewModel
        private static Brush _MakeFrozen(byte r, byte g, byte b)
        {
            var brush = new SolidColorBrush(Color.FromRgb(r, g, b));
            brush.Freeze();
            return brush;
        }

        private static readonly Brush _brushCritical = _MakeFrozen(0xE7, 0x4C, 0x3C);
        private static readonly Brush _brushError    = _MakeFrozen(0xE6, 0x7E, 0x22);
        private static readonly Brush _brushWarning  = _MakeFrozen(0xF1, 0xC4, 0x0F);
        private static readonly Brush _brushInfo     = _MakeFrozen(0x34, 0x98, 0xDB);

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

        /// <summary>Texto formatado para copiar para área de transferência.</summary>
        public string TextoParaCopiar { get; }

        public IssueViewModel(IssueResult issue)
        {
            SeverityLabel  = issue.Severity.ToUpperInvariant();
            RuleId         = issue.RuleId;
            Message        = issue.Message;
            CaminhoCompleto = issue.File;
            NomeArquivo    = Path.GetFileName(issue.File);
            Line           = issue.Line;
            Category       = issue.Category;

            TextoParaCopiar = $"[{issue.Severity.ToUpperInvariant()}] {issue.RuleId} — {Path.GetFileName(issue.File)}:{issue.Line} — {issue.Message}";

            SeverityColor = SeverityLabel switch
            {
                "CRITICAL" => _brushCritical,
                "ERROR"    => _brushError,
                "WARNING"  => _brushWarning,
                _          => _brushInfo,
            };
        }
    }

    /// <summary>
    /// ViewModel de métricas de um arquivo individual para o TreeView.
    /// </summary>
    public sealed class FileMetricsViewModel
    {
        private const int LimiteLinhasMetodo  = 30;
        private const int LimiteNesting       = 5;
        private const int LimiteDependencias  = 5;
        private const int LimiteTotalLinhas   = 300;

        // Duas brushes estáticas frozen para os estados OK/alerta das métricas
        private static Brush MetricaFrozen(byte r, byte g, byte b)
        {
            var brush = new SolidColorBrush(Color.FromRgb(r, g, b));
            brush.Freeze();
            return brush;
        }

        private static readonly Brush _brushMetricaOk    = MetricaFrozen(0x2E, 0xCC, 0x71);
        private static readonly Brush _brushMetricaAlerta = MetricaFrozen(0xE6, 0x7E, 0x22);

        public string NomeArquivo    { get; }
        public string CaminhoCompleto { get; }
        public int    TotalLinhas    { get; }
        public int    MaxMethodLines { get; }
        public int    MaxNesting     { get; }
        public int    ConstructorDeps { get; }

        public Brush CorTotalLinhas  { get; }
        public Brush CorMaxMethod    { get; }
        public Brush CorMaxNesting   { get; }
        public Brush CorDependencias { get; }

        public FileMetricsViewModel(FileResult fileResult)
        {
            CaminhoCompleto = fileResult.File;
            NomeArquivo     = Path.GetFileName(fileResult.File);

            var m = fileResult.Metrics!;
            TotalLinhas    = m.TotalLines;
            MaxMethodLines = m.MaxMethodLines;
            MaxNesting     = m.MaxNesting;
            ConstructorDeps = m.ConstructorDeps;

            CorTotalLinhas  = CorMetrica(TotalLinhas,    LimiteTotalLinhas);
            CorMaxMethod    = CorMetrica(MaxMethodLines,  LimiteLinhasMetodo);
            CorMaxNesting   = CorMetrica(MaxNesting,      LimiteNesting);
            CorDependencias = CorMetrica(ConstructorDeps, LimiteDependencias);
        }

        private static Brush CorMetrica(int valor, int limite) =>
            valor > limite ? _brushMetricaAlerta : _brushMetricaOk;
    }
}
