using System;
using System.IO;
using System.Threading.Tasks;
using CodeGuardian.VS.Analysis;
using CodeGuardian.VS.Settings;
using Microsoft.VisualStudio;
using Microsoft.VisualStudio.Imaging;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Shell.Interop;

namespace CodeGuardian.VS.GitHooks
{
    /// <summary>
    /// Verifica se os git hooks do Code Guardian estao instalados e,
    /// caso negativo, exibe InfoBar no VS com opcao de instalar.
    /// </summary>
    public sealed class HookInstallService
    {
        private const string MarcadorHook = "Code Guardian Hook pre-commit";

        private readonly IAsyncServiceProvider _serviceProvider;
        private readonly PythonProcessRunner _runner;

        public HookInstallService(IAsyncServiceProvider serviceProvider)
        {
            _serviceProvider = serviceProvider;
            _runner = new PythonProcessRunner();
        }

        /// <summary>
        /// Verifica os hooks e exibe InfoBar se nao instalados.
        /// Deve ser chamado no InitializeAsync do package, apos SwitchToMainThreadAsync.
        /// </summary>
        public async Task CheckAndPromptAsync()
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

            var solutionDir = ObterDiretorioDaSolution();
            if (string.IsNullOrEmpty(solutionDir))
                return;

            var gitDir = EncontrarDiretorioGit(solutionDir!);
            if (gitDir == null)
                return;

            if (AreHooksInstalled(gitDir))
                return;

            await ExibirInfoBarAsync(gitDir, solutionDir!);
        }

        /// <summary>
        /// Instala os hooks via install_hooks.py.
        /// </summary>
        public async Task InstallHooksAsync(string solutionDir)
        {
            var runnerPath = LocalizarInstallHooksPy(solutionDir);
            if (runnerPath == null)
            {
                await MostrarMensagemAsync("install_hooks.py nao encontrado. Verifique o repositorio Code Guardian.");
                return;
            }

            var gitRoot = EncontrarDiretorioGit(solutionDir) ?? solutionDir;
            var cfg = CodeGuardianSettings.Padrao;

            try
            {
                await _runner.RunAsync(
                    pythonExe: cfg.PythonExecutable,
                    scriptPath: runnerPath,
                    args: new[] { "install" },
                    workingDir: gitRoot);

                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
                var dte = await _serviceProvider.GetServiceAsync(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                if (dte != null)
                    dte.StatusBar.Text = "Code Guardian: Hooks instalados com sucesso.";
            }
            catch (Exception ex)
            {
                await MostrarMensagemAsync($"Erro ao instalar hooks: {ex.Message}");
            }
        }

        /// <summary>
        /// Retorna true se o pre-commit hook contem o marcador do Code Guardian.
        /// </summary>
        public bool AreHooksInstalled(string gitDir)
        {
            var hookPath = Path.Combine(gitDir, "hooks", "pre-commit");
            if (!File.Exists(hookPath))
                return false;

            return File.ReadAllText(hookPath).Contains(MarcadorHook);
        }

        private async Task ExibirInfoBarAsync(string gitDir, string solutionDir)
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

            var shell = await _serviceProvider.GetServiceAsync(typeof(SVsShell)) as IVsShell;
            if (shell == null)
                return;

            shell.GetProperty((int)__VSSPROPID7.VSSPROPID_MainWindowInfoBarHost, out var hostObj);
            var host = hostObj as IVsInfoBarHost;
            if (host == null)
                return;

            var modelo = new InfoBarModel(
                textSpans: new IVsInfoBarTextSpan[]
                {
                    new InfoBarTextSpan("Code Guardian: Git hooks nao estao instalados.  ")
                },
                actionItems: new IVsInfoBarActionItem[]
                {
                    new InfoBarHyperlink("Instalar agora")
                },
                image: KnownMonikers.StatusWarning,
                isCloseButtonVisible: true);

            var infoBarFactory = await _serviceProvider.GetServiceAsync(typeof(SVsInfoBarUIFactory)) as IVsInfoBarUIFactory;
            if (infoBarFactory == null)
                return;

            var uiElement = infoBarFactory.CreateInfoBar(modelo);
            uiElement.Advise(new InfoBarEventHandler(async () =>
            {
                await InstallHooksAsync(solutionDir);
            }), out _);

            host.AddInfoBar(uiElement);
        }

        private static string? ObterDiretorioDaSolution()
        {
            ThreadHelper.ThrowIfNotOnUIThread();

            var dte = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
            var solutionPath = dte?.Solution?.FullName;

            if (string.IsNullOrEmpty(solutionPath))
                return null;

            return Path.GetDirectoryName(solutionPath);
        }

        private static string? EncontrarDiretorioGit(string inicio)
        {
            var atual = inicio;
            while (!string.IsNullOrEmpty(atual))
            {
                if (Directory.Exists(Path.Combine(atual, ".git")))
                    return Path.Combine(atual, ".git");

                var pai = Path.GetDirectoryName(atual);
                if (pai == atual) break;
                atual = pai;
            }
            return null;
        }

        private static string? LocalizarInstallHooksPy(string diretorio)
        {
            var atual = diretorio;
            while (!string.IsNullOrEmpty(atual))
            {
                var candidato = Path.Combine(atual, "code_guardian", "install_hooks.py");
                if (File.Exists(candidato))
                    return candidato;

                var pai = Path.GetDirectoryName(atual);
                if (pai == atual) break;
                atual = pai;
            }
            return null;
        }

        private static async Task MostrarMensagemAsync(string mensagem)
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

            var outputWindow = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(SVsOutputWindow))
                as IVsOutputWindow;

            var guidPane = VSConstants.OutputWindowPaneGuid.GeneralPane_guid;
            IVsOutputWindowPane? pane = null;
            outputWindow?.GetPane(ref guidPane, out pane);
            pane?.OutputStringThreadSafe($"[Code Guardian] {mensagem}{Environment.NewLine}");
        }

        /// <summary>
        /// Handler de eventos da InfoBar para o botao "Instalar agora".
        /// </summary>
        private sealed class InfoBarEventHandler : IVsInfoBarUIEvents
        {
            private readonly Func<Task> _aoClicar;

            public InfoBarEventHandler(Func<Task> aoClicar)
            {
                _aoClicar = aoClicar;
            }

            public void OnClosed(IVsInfoBarUIElement infoBarUIElement)
            {
                // Nao e necessario tratamento adicional ao fechar
            }

            public void OnActionItemClicked(IVsInfoBarUIElement infoBarUIElement, IVsInfoBarActionItem actionItem)
            {
                _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
                {
                    await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
                    infoBarUIElement.Close();
                    await _aoClicar();
                });
            }
        }
    }
}
