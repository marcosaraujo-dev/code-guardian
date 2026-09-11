using System;
using System.IO;
using System.Threading.Tasks;
using Microsoft.VisualStudio.Imaging;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Shell.Interop;

namespace CodeGuardian.VS.GitHooks
{
    /// <summary>
    /// Gerencia a instalacao e remocao dos git hooks do Code Guardian.
    /// Scripts Python sao bundlados no VSIX e copiados para
    /// %LOCALAPPDATA%\CodeGuardian\scripts ao instalar os hooks.
    /// </summary>
    public sealed class HookInstallService
    {
        private const string MarcadorPreCommit  = "Code Guardian Hook pre-commit";
        private const string MarcadorPrepareMsg = "Code Guardian Hook prepare-commit-msg";

        private static readonly string UserScriptsDir =
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "CodeGuardian",
                "scripts");

        private readonly IAsyncServiceProvider _serviceProvider;

        // Cache de verificação de hooks — evita leitura de arquivo a cada análise
        private string? _hookCacheGitDir;
        private bool    _hookCacheResult;

        public HookInstallService(IAsyncServiceProvider serviceProvider)
            => _serviceProvider = serviceProvider;

        // ── Chamado no InitializeAsync do Package ──────────────────────────

        /// <summary>
        /// Sincroniza scripts bundlados, verifica hooks e os instala automaticamente se possivel.
        /// Exibe InfoBar apenas quando ha conflito com hook de terceiro.
        /// </summary>
        public async Task CheckAndPromptAsync()
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
            var solutionDir = ObterDiretorioDaSolution();

            // Todo I/O de arquivo em background para nao travar a UI thread
            string? gitDir = null;
            bool instalado = false;
            bool temConflito = false;

            await Task.Run(() =>
            {
                SincronizarScripts();

                if (string.IsNullOrEmpty(solutionDir))
                    return;

                gitDir = EncontrarDiretorioGit(solutionDir!);
                if (gitDir == null)
                    return;

                instalado = AreHooksInstalled(gitDir);
                if (instalado)
                    return;

                // Verifica se ha hook de terceiro que impediria a instalacao
                var preCommitPath = Path.Combine(gitDir, "hooks", "pre-commit");
                temConflito = File.Exists(preCommitPath)
                              && !File.ReadAllText(preCommitPath).Contains(MarcadorPreCommit);

                // Instala silenciosamente quando nao ha conflito
                if (!temConflito)
                    InstalarHooksSilencioso(gitDir);
            });

            if (gitDir == null || instalado || !temConflito)
                return;

            // Somente exibe InfoBar quando ha conflito com hook de terceiro
            var hookConflitante = Path.Combine(gitDir, "hooks", "pre-commit");
            await ExibirInfoBarConflitAsync(gitDir, hookConflitante);
        }

        // ── Instala os hooks ───────────────────────────────────────────────

        /// <summary>
        /// Copia scripts bundlados e grava os arquivos de hook no repositorio.
        /// </summary>
        public async Task InstallHooksAsync(string gitDir)
        {
            var hooksDir = Path.Combine(gitDir, "hooks");

            // I/O em background para nao bloquear a UI thread
            var (preCommitEscrito, prepareMsgEscrito) = await Task.Run(() =>
            {
                SincronizarScripts();
                Directory.CreateDirectory(hooksDir);
                var pre = EscreverHook(hooksDir, "pre-commit",         MarcadorPreCommit,  GerarPreCommit());
                var msg = EscreverHook(hooksDir, "prepare-commit-msg", MarcadorPrepareMsg, GerarPrepareCommitMsg());
                return (pre, msg);
            });

            // Invalidar cache após alteração dos hooks
            _hookCacheGitDir = null;

            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
            var dte = await _serviceProvider.GetServiceAsync(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
            if (dte == null)
                return;

            if (!preCommitEscrito)
            {
                dte.StatusBar.Text =
                    "Code Guardian: hook 'pre-commit' ja existe de outra ferramenta. " +
                    "Adicione manualmente ou remova o hook existente e tente novamente.";

                System.Windows.MessageBox.Show(
                    "Nao foi possivel instalar o hook 'pre-commit' porque ja existe um arquivo " +
                    "de hook criado por outra ferramenta (ex: Husky, Git Flow).\n\n" +
                    $"Caminho: {Path.Combine(hooksDir, "pre-commit")}\n\n" +
                    "Opcoes:\n" +
                    "  1. Remova ou renomeie o hook existente e instale novamente.\n" +
                    "  2. Adicione manualmente o conteudo do Code Guardian ao hook existente.",
                    "Code Guardian — Conflito de Hook",
                    System.Windows.MessageBoxButton.OK,
                    System.Windows.MessageBoxImage.Warning);
                return;
            }

            dte.StatusBar.Text = preCommitEscrito && prepareMsgEscrito
                ? "Code Guardian: Git hooks instalados com sucesso."
                : "Code Guardian: pre-commit instalado. prepare-commit-msg ignorado (hook de terceiro existente).";
        }

        // ── Remove os hooks ────────────────────────────────────────────────

        /// <summary>
        /// Remove os arquivos de hook criados pelo Code Guardian.
        /// </summary>
        public Task UninstallHooksAsync(string gitDir)
        {
            var hooksDir = Path.Combine(gitDir, "hooks");
            RemoverHook(hooksDir, "pre-commit",         MarcadorPreCommit);
            RemoverHook(hooksDir, "prepare-commit-msg", MarcadorPrepareMsg);
            // Invalidar cache após remoção dos hooks
            _hookCacheGitDir = null;
            return Task.CompletedTask;
        }

        // ── Verifica se o pre-commit do Code Guardian esta instalado ───────

        /// <summary>
        /// Retorna true se o pre-commit hook contem o marcador do Code Guardian.
        /// Resultado é cacheado por gitDir — invalidado em InstallHooksAsync/UninstallHooksAsync.
        /// </summary>
        public bool AreHooksInstalled(string gitDir)
        {
            if (_hookCacheGitDir == gitDir)
                return _hookCacheResult;

            var hookPath = Path.Combine(gitDir, "hooks", "pre-commit");
            _hookCacheResult = File.Exists(hookPath) && File.ReadAllText(hookPath).Contains(MarcadorPreCommit);
            _hookCacheGitDir = gitDir;
            return _hookCacheResult;
        }

        // ── Localiza o diretorio .git subindo na arvore ────────────────────

        /// <summary>
        /// Caminha para cima na arvore de diretorios ate encontrar .git.
        /// Retorna o caminho completo de .git ou null se nao encontrado.
        /// </summary>
        public static string? EncontrarDiretorioGit(string inicio)
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

        // ── Instalacao silenciosa (sem feedback de UI) ─────────────────────

        private static void InstalarHooksSilencioso(string gitDir)
        {
            var hooksDir = Path.Combine(gitDir, "hooks");
            Directory.CreateDirectory(hooksDir);
            EscreverHook(hooksDir, "pre-commit",         MarcadorPreCommit,  GerarPreCommit());
            EscreverHook(hooksDir, "prepare-commit-msg", MarcadorPrepareMsg, GerarPrepareCommitMsg());
        }

        // ── Sincroniza scripts bundlados → %LOCALAPPDATA%\CodeGuardian\scripts ──

        private static void SincronizarScripts()
        {
            var srcDir = Path.Combine(
                Path.GetDirectoryName(typeof(HookInstallService).Assembly.Location)!,
                "scripts");

            if (!Directory.Exists(srcDir))
                return;

            Directory.CreateDirectory(UserScriptsDir);

            foreach (var origem in Directory.GetFiles(srcDir, "*.py"))
            {
                var destino = Path.Combine(UserScriptsDir, Path.GetFileName(origem));
                var srcInfo = new FileInfo(origem);

                if (File.Exists(destino))
                {
                    var dstInfo = new FileInfo(destino);
                    if (dstInfo.Length == srcInfo.Length && dstInfo.LastWriteTimeUtc == srcInfo.LastWriteTimeUtc)
                        continue;
                }

                File.Copy(origem, destino, overwrite: true);
            }
        }

        // ── Gera conteudo do pre-commit ────────────────────────────────────

        private static string GerarPreCommit()
        {
            var bashRunner = ToBashPath(Path.Combine(UserScriptsDir, "runner.py"));

            return
                "#!/bin/sh\n" +
                "# Code Guardian Hook pre-commit\n" +
                "# Executa analise estatica nos arquivos staged antes de commitar.\n" +
                "# Para pular: git commit --no-verify\n" +
                "\n" +
                $"GUARDIAN=\"{bashRunner}\"\n" +
                "\n" +
                "if ! command -v python3 > /dev/null 2>&1 && ! command -v python > /dev/null 2>&1; then\n" +
                "    echo \"[guardian] Python nao encontrado -- hook pulado.\"\n" +
                "    exit 0\n" +
                "fi\n" +
                "PYTHON=python3\n" +
                "command -v python3 > /dev/null 2>&1 || PYTHON=python\n" +
                "\n" +
                "if [ ! -f \"$GUARDIAN\" ]; then\n" +
                "    echo \"[guardian] Scripts nao encontrados -- reinstale o Code Guardian.\"\n" +
                "    exit 0\n" +
                "fi\n" +
                "\n" +
                "STAGED=$(git diff --cached --name-only --diff-filter=d | grep -i \"\\.cs$\" | grep -v \"/Migrations/\" | grep -v \"\\.Designer\\.cs\" | grep -v \"/obj/\" | grep -v \"/bin/\")\n" +
                "if [ -z \"$STAGED\" ]; then exit 0; fi\n" +
                "\n" +
                "GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)\n" +
                "REPORT_DIR=\"$GIT_ROOT/.codeguardian\"\n" +
                "REPORT_HTML=\"$REPORT_DIR/last-commit-report.html\"\n" +
                "SUMMARY_FILE=\"$REPORT_DIR/last-commit-summary.txt\"\n" +
                "mkdir -p \"$REPORT_DIR\"\n" +
                "rm -f \"$SUMMARY_FILE\"\n" +
                "\n" +
                "echo \"\"\n" +
                "echo \"[guardian] Verificando arquivos antes do commit...\"\n" +
                "echo \"\"\n" +
                "\n" +
                "$PYTHON \"$GUARDIAN\" --staged --rules-only --severity warning --fail-on error --timeout 60 --output \"$REPORT_HTML\" --summary-file \"$SUMMARY_FILE\"\n" +
                "EXIT_CODE=$?\n" +
                "\n" +
                "if [ $EXIT_CODE -ne 0 ]; then\n" +
                "    rm -f \"$SUMMARY_FILE\"\n" +
                "    echo \"\"\n" +
                "    echo \"[guardian] BLOQUEADO: issues criticas encontradas.\"\n" +
                "    echo \"   Relatorio: $REPORT_HTML\"\n" +
                "    echo \"   Para pular: git commit --no-verify\"\n" +
                "    echo \"\"\n" +
                "    exit 1\n" +
                "fi\n" +
                "\n" +
                "echo \"\"\n" +
                "echo \"[guardian] Nenhum bloqueador. Commit liberado.\"\n" +
                "echo \"   Relatorio: $REPORT_HTML\"\n" +
                "echo \"\"\n" +
                "exit 0\n";
        }

        // ── Gera conteudo do prepare-commit-msg ───────────────────────────

        private static string GerarPrepareCommitMsg()
        {
            var bashTrailer = ToBashPath(Path.Combine(UserScriptsDir, "_append_guardian_trailer.py"));

            return
                "#!/bin/sh\n" +
                "# Code Guardian Hook prepare-commit-msg\n" +
                "# Injeta trailer Guardian-Review na mensagem do commit apos analise bem-sucedida.\n" +
                "\n" +
                $"TRAILER_SCRIPT=\"{bashTrailer}\"\n" +
                "if [ ! -f \"$TRAILER_SCRIPT\" ]; then exit 0; fi\n" +
                "\n" +
                "if ! command -v python3 > /dev/null 2>&1 && ! command -v python > /dev/null 2>&1; then\n" +
                "    exit 0\n" +
                "fi\n" +
                "PYTHON=python3\n" +
                "command -v python3 > /dev/null 2>&1 || PYTHON=python\n" +
                "\n" +
                "$PYTHON \"$TRAILER_SCRIPT\" \"$1\" \"${2:-}\"\n" +
                "exit 0\n";
        }

        // ── Helpers ────────────────────────────────────────────────────────

        /// <summary>
        /// Converte caminho Windows para caminho bash compativel com Git for Windows.
        /// Exemplo: C:\foo\bar → /c/foo/bar
        /// </summary>
        private static string ToBashPath(string windowsPath)
        {
            var p = windowsPath.Replace('\\', '/');
            if (p.Length >= 2 && p[1] == ':')
                p = "/" + char.ToLowerInvariant(p[0]) + p.Substring(2);
            return p;
        }

        /// <summary>
        /// Grava o arquivo de hook. Se ja existir um hook de terceiro (sem o marcador), nao sobrescreve
        /// e retorna false. Retorna true quando o arquivo foi gravado com sucesso.
        /// </summary>
        private static bool EscreverHook(string hooksDir, string hookName, string marker, string content)
        {
            var hookPath = Path.Combine(hooksDir, hookName);

            if (File.Exists(hookPath))
            {
                var existing = File.ReadAllText(hookPath);
                if (!existing.Contains(marker))
                    return false; // hook de terceiro — nao sobrescreve
            }

            File.WriteAllText(
                hookPath,
                content,
                new System.Text.UTF8Encoding(encoderShouldEmitUTF8Identifier: false));

            return true;
        }

        private static void RemoverHook(string hooksDir, string hookName, string marker)
        {
            var hookPath = Path.Combine(hooksDir, hookName);
            if (!File.Exists(hookPath))
                return;

            if (File.ReadAllText(hookPath).Contains(marker))
                File.Delete(hookPath);
        }

        private async Task ExibirInfoBarConflitAsync(string gitDir, string hookConflitante)
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

            var shell = await _serviceProvider.GetServiceAsync(typeof(SVsShell)) as IVsShell;
            if (shell == null)
                return;

            shell.GetProperty((int)__VSSPROPID7.VSSPROPID_MainWindowInfoBarHost, out var hostObj);
            if (hostObj is not IVsInfoBarHost host)
                return;

            var nomeHook   = Path.GetFileName(hookConflitante);
            var caminhoRel = hookConflitante.Replace(
                Path.GetDirectoryName(Path.GetDirectoryName(gitDir)) + Path.DirectorySeparatorChar,
                string.Empty);

            var modelo = new InfoBarModel(
                textSpans: new IVsInfoBarTextSpan[]
                {
                    new InfoBarTextSpan(
                        $"Code Guardian: hook '{nomeHook}' ja existe de outra ferramenta " +
                        $"({caminhoRel}). Remova-o ou mescle manualmente.  ")
                },
                actionItems: new IVsInfoBarActionItem[]
                {
                    new InfoBarHyperlink("Como resolver")
                },
                image: KnownMonikers.StatusWarning,
                isCloseButtonVisible: true);

            var factory = await _serviceProvider.GetServiceAsync(typeof(SVsInfoBarUIFactory)) as IVsInfoBarUIFactory;
            if (factory == null)
                return;

            var uiElement = factory.CreateInfoBar(modelo);
            var handler   = new InfoBarEventHandler(uiElement, () => ExibirInstrucoesConflitoAsync(hookConflitante));
            uiElement.Advise(handler, out handler.Cookie);
            host.AddInfoBar(uiElement);
        }

        private static Task ExibirInstrucoesConflitoAsync(string hookConflitante)
        {
            System.Windows.MessageBox.Show(
                $"O arquivo abaixo foi criado por outra ferramenta (ex: Husky, Git Flow, Lefthook) " +
                $"e o Code Guardian nao pode sobrescreve-lo automaticamente:\n\n" +
                $"  {hookConflitante}\n\n" +
                "Para resolver, escolha uma opcao:\n\n" +
                "  1. Remova o hook existente e reabra a solution\n" +
                "     (o Code Guardian instalara automaticamente).\n\n" +
                "  2. Adicione ao final do hook existente o conteudo\n" +
                "     gerado pelo Code Guardian (Tools > Code Guardian > Instalar Hooks).",
                "Code Guardian — Conflito de Hook",
                System.Windows.MessageBoxButton.OK,
                System.Windows.MessageBoxImage.Warning);
            return Task.CompletedTask;
        }

        private static string? ObterDiretorioDaSolution()
        {
            ThreadHelper.ThrowIfNotOnUIThread();
            var dte = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
            var path = dte?.Solution?.FullName;
            return string.IsNullOrEmpty(path) ? null : Path.GetDirectoryName(path);
        }

        // ── Handler de eventos da InfoBar ──────────────────────────────────

        private sealed class InfoBarEventHandler : IVsInfoBarUIEvents
        {
            private readonly IVsInfoBarUIElement _elemento;
            private readonly Func<Task> _aoClicar;
            public uint Cookie;

            public InfoBarEventHandler(IVsInfoBarUIElement elemento, Func<Task> aoClicar)
            {
                _elemento = elemento;
                _aoClicar = aoClicar;
            }

            public void OnClosed(IVsInfoBarUIElement infoBarUIElement)
            {
                ThreadHelper.ThrowIfNotOnUIThread();
                infoBarUIElement.Unadvise(Cookie);
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
