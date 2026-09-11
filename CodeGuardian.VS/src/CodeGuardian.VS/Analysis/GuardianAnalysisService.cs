using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
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
        private bool? _rulesOnlyOverride;

        public event EventHandler<AnalysisCompletedEventArgs>? AnalysisCompleted;
        public event EventHandler<AnalysisFailedEventArgs>?    AnalysisFailed;
        public event EventHandler<ScanProgressEventArgs>?      ScanProgress;

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

            var totalArquivos = ContarArquivosCS(solutionDir);
            ScanProgress?.Invoke(this, new ScanProgressEventArgs
            {
                ArquivoAtual  = 0,
                TotalArquivos = totalArquivos,
                NomeArquivo   = $"{totalArquivos} arquivo(s) encontrado(s)"
            });

            await ExecutarAnaliseAsync(
                args: new[] { "--scan", "--dir", solutionDir, "--format", "json" },
                filePath: solutionDir,
                isFullScan: true,
                ct: ct);
        }

        /// <inheritdoc />
        public async Task AnalyzeIncrementalAsync(string solutionDir, CancellationToken ct = default)
        {
            if (string.IsNullOrWhiteSpace(solutionDir))
                return;

            var arquivos = ObterArquivosModificadosGit(solutionDir);

            if (arquivos.Length == 0)
            {
                AnalysisCompleted?.Invoke(this, new AnalysisCompletedEventArgs
                {
                    FilePath   = solutionDir,
                    Result     = new GuardianResult { RiskLabel = "Nenhum arquivo modificado" },
                    IsFullScan = true
                });
                return;
            }

            _cache.Clear();
            var resultados = new List<GuardianResult>();

            for (var i = 0; i < arquivos.Length; i++)
            {
                ct.ThrowIfCancellationRequested();

                var arquivo = arquivos[i];
                ScanProgress?.Invoke(this, new ScanProgressEventArgs
                {
                    ArquivoAtual  = i + 1,
                    TotalArquivos = arquivos.Length,
                    NomeArquivo   = Path.GetFileName(arquivo)
                });

                var resultado = await ExecutarAnaliseSimplesAsync(arquivo, ct);
                if (resultado != null)
                    resultados.Add(resultado);
            }

            var combinado = MergeResultados(resultados, arquivos.Length);
            _cache.Set(solutionDir, combinado);

            AnalysisCompleted?.Invoke(this, new AnalysisCompletedEventArgs
            {
                FilePath   = solutionDir,
                Result     = combinado,
                IsFullScan = true
            });
        }

        /// <inheritdoc />
        public GuardianResult? GetCachedResult(string filePath) => _cache.GetOrNull(filePath);

        /// <inheritdoc />
        public void SetRulesOnlyOverride(bool? valor) => _rulesOnlyOverride = valor;

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
                var runnerPath = LocalizarRunnerPy(filePath, configuracoes);

                if (runnerPath == null)
                {
                    const string msgRunner = "runner.py não encontrado. Configure o caminho em Tools > Options > Code Guardian.";
                    await LogarErroAsync(msgRunner);
                    NotificarFalha(AnalysisErrorType.RunnerNotFound, msgRunner);
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
                        envVars: ObterEnvVarsIA(configuracoes),
                        ct: cts.Token);
                }
                catch (PythonNotFoundException ex)
                {
                    await LogarErroAsync($"Python não encontrado: {ex.Message}");
                    NotificarFalha(AnalysisErrorType.PythonNotFound, ex.Message);
                    return;
                }
                catch (OperationCanceledException)
                {
                    var msgTimeout = $"Análise cancelada (timeout de {configuracoes.AnalysisTimeoutSeconds}s atingido).";
                    await LogarErroAsync(msgTimeout);
                    NotificarFalha(AnalysisErrorType.Timeout, msgTimeout);
                    return;
                }
                catch (GuardianScriptException ex)
                {
                    await LogarErroAsync($"Erro no script: {ex.Message}");
                    NotificarFalha(AnalysisErrorType.ScriptError, ex.Message);
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

        private static Dictionary<string, string> ObterEnvVarsIA(CodeGuardianSettings cfg)
        {
            var vars = new Dictionary<string, string>();

            // API keys — passadas como variáveis de ambiente consumidas por cada provider
            if (!string.IsNullOrWhiteSpace(cfg.GeminiApiKey))
                vars["GEMINI_API_KEY"] = cfg.GeminiApiKey;

            if (!string.IsNullOrWhiteSpace(cfg.ClaudeApiKey))
                vars["ANTHROPIC_API_KEY"] = cfg.ClaudeApiKey;

            if (!string.IsNullOrWhiteSpace(cfg.OpenAIApiKey))
                vars["OPENAI_API_KEY"] = cfg.OpenAIApiKey;

            // Seleção de provider/modelo — sobrescrevem config.json sem editá-lo
            if (!string.IsNullOrWhiteSpace(cfg.IAProviderPrimario))
                vars["GUARDIAN_AI_PRIMARY"] = cfg.IAProviderPrimario;

            if (!string.IsNullOrWhiteSpace(cfg.IAProviderFallback))
                vars["GUARDIAN_AI_FALLBACK"] = cfg.IAProviderFallback;

            if (!string.IsNullOrWhiteSpace(cfg.OllamaUrl))
                vars["GUARDIAN_OLLAMA_URL"] = cfg.OllamaUrl;

            if (!string.IsNullOrWhiteSpace(cfg.OllamaModel))
                vars["GUARDIAN_OLLAMA_MODEL"] = cfg.OllamaModel;

            return vars;
        }

        private string[] AdicionarFlagsDeConfiguracao(string[] args, CodeGuardianSettings cfg)
        {
            var lista = new System.Collections.Generic.List<string>(args);

            var rulesOnly = _rulesOnlyOverride ?? cfg.RulesOnly;
            if (rulesOnly && !lista.Contains("--rules-only"))
                lista.Add("--rules-only");
            else if (!rulesOnly)
                lista.Remove("--rules-only");

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
        private string? LocalizarRunnerPy(string pontoDepartida, CodeGuardianSettings cfg)
        {
            // Override configurado pelo usuário
            if (!string.IsNullOrWhiteSpace(cfg.RunnerScriptPath) && File.Exists(cfg.RunnerScriptPath))
                return cfg.RunnerScriptPath;

            // Preferir scripts do projeto (sempre mais atualizados que os bundlados)
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

            // Fallback: scripts bundlados (quando o projeto não contém code_guardian/)
            if (File.Exists(PythonLocator.BundledRunnerPath))
                return PythonLocator.BundledRunnerPath;

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

        private void NotificarFalha(AnalysisErrorType tipo, string mensagem)
        {
            AnalysisFailed?.Invoke(this, new AnalysisFailedEventArgs
            {
                ErrorType    = tipo,
                ErrorMessage = mensagem,
            });
        }

        private async Task<GuardianResult?> ExecutarAnaliseSimplesAsync(string filePath, CancellationToken ct)
        {
            var cfg        = ObterConfiguracoes();
            var runnerPath = LocalizarRunnerPy(filePath, cfg);
            if (runnerPath == null)
                return null;

            var args       = AdicionarFlagsDeConfiguracao(new[] { "--file", filePath, "--format", "json" }, cfg);
            var workingDir = EncontrarRaizGit(Path.GetDirectoryName(filePath) ?? filePath)
                             ?? Path.GetDirectoryName(runnerPath)!;

            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(TimeSpan.FromSeconds(cfg.AnalysisTimeoutSeconds));

            try
            {
                var json = await _runner.RunAsync(cfg.PythonExecutable, runnerPath, args, workingDir, ObterEnvVarsIA(cfg), cts.Token);
                return ParsearJson(json);
            }
            catch { return null; }
        }

        private static GuardianResult MergeResultados(List<GuardianResult> resultados, int totalArquivos)
        {
            if (resultados.Count == 0)
                return new GuardianResult { RiskLabel = "Nenhum issue encontrado" };

            var merged = new GuardianResult
            {
                Files = resultados.SelectMany(r => r.Files).ToList()
            };

            merged.Summary.Critical = resultados.Sum(r => r.Summary.Critical);
            merged.Summary.Error    = resultados.Sum(r => r.Summary.Error);
            merged.Summary.Warning  = resultados.Sum(r => r.Summary.Warning);
            merged.Summary.Info     = resultados.Sum(r => r.Summary.Info);

            var maxScore    = resultados.Max(r => r.RiskScore);
            merged.RiskScore = Math.Min(100, maxScore);
            merged.RiskLabel = resultados.FirstOrDefault(r => r.RiskScore == maxScore)?.RiskLabel
                               ?? "Incremental";
            merged.HasBlockers = resultados.Any(r => r.HasBlockers);

            return merged;
        }

        private static string[] ObterArquivosModificadosGit(string solutionDir)
        {
            try
            {
                var psi = new ProcessStartInfo("git", "diff HEAD --name-only")
                {
                    WorkingDirectory       = solutionDir,
                    RedirectStandardOutput = true,
                    UseShellExecute        = false,
                    CreateNoWindow         = true
                };

                using var proc = Process.Start(psi);
                var saida = proc?.StandardOutput.ReadToEnd() ?? string.Empty;
                proc?.WaitForExit(5000);

                return saida
                    .Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries)
                    .Where(l => l.EndsWith(".cs", StringComparison.OrdinalIgnoreCase)
                                && !l.Contains("/obj/") && !l.Contains("/bin/")
                                && !l.EndsWith(".Designer.cs", StringComparison.OrdinalIgnoreCase))
                    .Select(l => Path.GetFullPath(Path.Combine(solutionDir, l.Replace('/', '\\'))))
                    .Where(File.Exists)
                    .ToArray();
            }
            catch { return Array.Empty<string>(); }
        }

        private static int ContarArquivosCS(string diretorio)
        {
            try
            {
                return Directory
                    .EnumerateFiles(diretorio, "*.cs", SearchOption.AllDirectories)
                    .Count(f => !f.Contains("\\obj\\") && !f.Contains("\\bin\\")
                                && !f.EndsWith(".Designer.cs", StringComparison.OrdinalIgnoreCase));
            }
            catch { return 0; }
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
