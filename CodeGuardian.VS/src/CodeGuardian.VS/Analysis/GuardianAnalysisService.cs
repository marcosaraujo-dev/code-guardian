using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using CodeGuardian.VS.Settings;
using Microsoft.VisualStudio.Shell;
using Newtonsoft.Json;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Serviço singleton que orquestra a execução do runner.py,
    /// parseia o JSON retornado e notifica os consumidores via evento AnalysisCompleted.
    /// </summary>
    public sealed class GuardianAnalysisService : IGuardianAnalysisService
    {
        private readonly PythonProcessRunner _runner;
        private readonly AnalysisCache _cache;
        private readonly SemaphoreSlim _semaforo = new SemaphoreSlim(1, 1);

        public event EventHandler<AnalysisCompletedEventArgs>? AnalysisCompleted;

        public GuardianAnalysisService()
        {
            _runner = new PythonProcessRunner();
            _cache = new AnalysisCache();
        }

        /// <inheritdoc />
        public async Task AnalyzeFileAsync(string filePath, CancellationToken ct = default)
        {
            if (string.IsNullOrWhiteSpace(filePath))
                return;

            // Invalidar cache ao iniciar nova análise (salvo indica mudança)
            _cache.Invalidate(filePath);

            await ExecutarAnaliseAsync(
                args: new[] { "--file", filePath, "--format", "json" },
                filePath: filePath,
                isFullScan: false,
                ct: ct);
        }

        /// <inheritdoc />
        public async Task AnalyzeSolutionAsync(string solutionDir, CancellationToken ct = default)
        {
            if (string.IsNullOrWhiteSpace(solutionDir))
                return;

            _cache.Clear();

            await ExecutarAnaliseAsync(
                args: new[] { "--scan", "--dir", solutionDir, "--format", "json" },
                filePath: solutionDir,
                isFullScan: true,
                ct: ct);
        }

        /// <inheritdoc />
        public GuardianResult? GetCachedResult(string filePath) => _cache.GetOrNull(filePath);

        private async Task ExecutarAnaliseAsync(
            string[] args,
            string filePath,
            bool isFullScan,
            CancellationToken ct)
        {
            // Evitar análises concorrentes que causariam conflito de resultados
            await _semaforo.WaitAsync(ct);
            try
            {
                var configuracoes = ObterConfiguracoes();
                var runnerPath = LocalizarRunnerPy(filePath);

                if (runnerPath == null)
                {
                    await LogarErroAsync("runner.py não encontrado. Configure o caminho em Tools > Options > Code Guardian.");
                    return;
                }

                var argsFinais = AdicionarFlagsDeConfiguracao(args, configuracoes);
                var workingDir = EncontrarRaizGit(Path.GetDirectoryName(filePath) ?? filePath)
                                 ?? Path.GetDirectoryName(runnerPath)!;

                var timeout = TimeSpan.FromSeconds(configuracoes.AnalysisTimeoutSeconds);
                using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
                cts.CancelAfter(timeout);

                string json;
                try
                {
                    json = await _runner.RunAsync(
                        pythonExe: configuracoes.PythonExecutable,
                        scriptPath: runnerPath,
                        args: argsFinais,
                        workingDir: workingDir,
                        ct: cts.Token);
                }
                catch (PythonNotFoundException ex)
                {
                    await LogarErroAsync($"Python não encontrado: {ex.Message}");
                    return;
                }
                catch (OperationCanceledException)
                {
                    await LogarErroAsync($"Análise cancelada (timeout de {configuracoes.AnalysisTimeoutSeconds}s atingido).");
                    return;
                }
                catch (GuardianScriptException ex)
                {
                    await LogarErroAsync($"Erro no script: {ex.Message}");
                    return;
                }

                var resultado = ParsearJson(json);
                if (resultado == null)
                    return;

                _cache.Set(filePath, resultado);

                AnalysisCompleted?.Invoke(this, new AnalysisCompletedEventArgs
                {
                    FilePath = filePath,
                    Result = resultado,
                    IsFullScan = isFullScan,
                });
            }
            finally
            {
                _semaforo.Release();
            }
        }

        private static string[] AdicionarFlagsDeConfiguracao(string[] args, CodeGuardianSettings cfg)
        {
            var lista = new System.Collections.Generic.List<string>(args);

            if (cfg.RulesOnly && !lista.Contains("--rules-only"))
                lista.Add("--rules-only");

            return lista.ToArray();
        }

        private static GuardianResult? ParsearJson(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
                return null;

            // O runner.py pode emitir texto antes do JSON; encontrar o início do objeto
            var inicio = json.IndexOf('{');
            if (inicio < 0)
                return null;

            try
            {
                return JsonConvert.DeserializeObject<GuardianResult>(json.Substring(inicio));
            }
            catch (JsonException)
            {
                return null;
            }
        }

        /// <summary>
        /// Descobre o caminho do runner.py subindo a árvore de diretórios.
        /// Usa o campo RunnerScriptPath de Settings como fallback.
        /// </summary>
        private string? LocalizarRunnerPy(string pontoDepartida)
        {
            var cfg = ObterConfiguracoes();

            // Override configurado pelo usuário
            if (!string.IsNullOrWhiteSpace(cfg.RunnerScriptPath) && File.Exists(cfg.RunnerScriptPath))
                return cfg.RunnerScriptPath;

            var diretorio = File.Exists(pontoDepartida)
                ? Path.GetDirectoryName(pontoDepartida)
                : pontoDepartida;

            while (!string.IsNullOrEmpty(diretorio))
            {
                var candidato = Path.Combine(diretorio, "code_guardian", "runner.py");
                if (File.Exists(candidato))
                    return candidato;

                var pai = Path.GetDirectoryName(diretorio);
                if (pai == diretorio)
                    break;

                diretorio = pai;
            }

            return null;
        }

        /// <summary>
        /// Encontra a raiz do repositório git subindo a árvore de diretórios.
        /// </summary>
        private static string? EncontrarRaizGit(string? diretorioInicio)
        {
            var atual = diretorioInicio;

            while (!string.IsNullOrEmpty(atual))
            {
                if (Directory.Exists(Path.Combine(atual, ".git")))
                    return atual;

                var pai = Path.GetDirectoryName(atual);
                if (pai == atual)
                    break;

                atual = pai;
            }

            return null;
        }

        private static CodeGuardianSettings ObterConfiguracoes()
        {
            // GlobalProvider é um singleton thread-safe para lookup do serviço;
            // GetService é o único acesso a VS thread-affine aqui, suprimido intencionalmente.
#pragma warning disable VSTHRD010
            var settingsProvider = ServiceProvider.GlobalProvider?.GetService(typeof(ICodeGuardianSettingsProvider))
                                   as ICodeGuardianSettingsProvider;
#pragma warning restore VSTHRD010
            return settingsProvider?.GetSettings() ?? CodeGuardianSettings.Padrao;
        }

        private static async Task LogarErroAsync(string mensagem)
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
            var outputWindow = ServiceProvider.GlobalProvider.GetService(typeof(Microsoft.VisualStudio.Shell.Interop.SVsOutputWindow))
                as Microsoft.VisualStudio.Shell.Interop.IVsOutputWindow;

            if (outputWindow == null)
                return;

            var guidPane = Microsoft.VisualStudio.VSConstants.OutputWindowPaneGuid.GeneralPane_guid;
            outputWindow.GetPane(ref guidPane, out var pane);
            pane?.OutputStringThreadSafe($"[Code Guardian] {mensagem}{Environment.NewLine}");
        }
    }
}
