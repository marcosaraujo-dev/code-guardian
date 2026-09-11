using System;
using System.ComponentModel.Design;
using System.Diagnostics;
using System.IO;
using CodeGuardian.VS.Analysis;
using CodeGuardian.VS.ToolWindow;
using Microsoft.VisualStudio.Shell;
using Task = System.Threading.Tasks.Task;

namespace CodeGuardian.VS.Commands
{
    /// <summary>
    /// Comando "Code Guardian: Exportar SARIF" no menu Tools.
    /// Gera guardian-report.sarif em .codeguardian/ na raiz da solution e abre a pasta.
    /// </summary>
    public sealed class ExportSarifCommand
    {
        public const int CommandId = 0x0104;
        public static readonly Guid CommandSet = new Guid("cba21ca3-11fa-4bbd-ab57-fc1d83a2ea95");

        private readonly AsyncPackage _package;

        private ExportSarifCommand(AsyncPackage package, IMenuCommandService commandService)
        {
            _package = package;

            var menuItem = new OleMenuCommand(Execute, new CommandID(CommandSet, CommandId));
            menuItem.BeforeQueryStatus += AtualizarEstado;
            commandService.AddCommand(menuItem);
        }

        public static async Task InitializeAsync(AsyncPackage package)
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync(package.DisposalToken);

            var commandService = await package.GetServiceAsync(typeof(IMenuCommandService)) as IMenuCommandService;
            if (commandService != null)
                _ = new ExportSarifCommand(package, commandService);
        }

        private void AtualizarEstado(object sender, EventArgs e)
        {
            ThreadHelper.ThrowIfNotOnUIThread();
            if (sender is OleMenuCommand comando)
            {
                var vm = ObterViewModel();
                comando.Enabled = vm?.UltimoResultado != null;
                comando.Visible = true;
            }
        }

        private void Execute(object sender, EventArgs e)
        {
            _ = ExecutarAsync();
        }

        private async Task ExecutarAsync()
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

            var vm = ObterViewModel();
            if (vm?.UltimoResultado == null)
            {
                System.Windows.MessageBox.Show(
                    "Execute uma análise antes de exportar o SARIF.",
                    "Code Guardian — Exportar SARIF",
                    System.Windows.MessageBoxButton.OK,
                    System.Windows.MessageBoxImage.Information);
                return;
            }

            var dte          = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
            var solutionPath = dte?.Solution?.FullName;
            var solutionDir  = string.IsNullOrEmpty(solutionPath) ? null : Path.GetDirectoryName(solutionPath);

            if (string.IsNullOrEmpty(solutionDir))
            {
                System.Windows.MessageBox.Show(
                    "Nenhuma solution aberta. Abra uma solution antes de exportar.",
                    "Code Guardian — Exportar SARIF",
                    System.Windows.MessageBoxButton.OK,
                    System.Windows.MessageBoxImage.Warning);
                return;
            }

            var ctx = ColetarContextoGit(solutionDir!);
            ctx.RepositoryRoot = solutionDir;

            var caminhoSarif = SarifReportGenerator.SalvarArquivo(vm.UltimoResultado, solutionDir!, ctx);

            if (dte != null)
                dte.StatusBar.Text = $"Code Guardian: SARIF exportado → {caminhoSarif}";

            var abrir = System.Windows.MessageBox.Show(
                $"Relatório SARIF exportado com sucesso!\n\n{caminhoSarif}\n\n" +
                "O arquivo guardian-metrics.json com histórico de execuções também foi atualizado.\n\n" +
                "Deseja abrir a pasta?",
                "Code Guardian — SARIF exportado",
                System.Windows.MessageBoxButton.YesNo,
                System.Windows.MessageBoxImage.Information);

            if (abrir == System.Windows.MessageBoxResult.Yes)
                Process.Start("explorer.exe", $"/select,\"{caminhoSarif}\"");
        }

        // ── Lê contexto do git para enriquecer o SARIF ────────────────────

        private static SarifReportGenerator.ExecutionContext ColetarContextoGit(string solutionDir)
        {
            var ctx = new SarifReportGenerator.ExecutionContext();

            try
            {
                ctx.GitBranch = ExecutarGit("rev-parse --abbrev-ref HEAD", solutionDir);
                ctx.GitCommit = ExecutarGit("rev-parse --short HEAD",      solutionDir);

                var remoteUrl = ExecutarGit("remote get-url origin", solutionDir);
                if (!string.IsNullOrEmpty(remoteUrl))
                    ctx.RepositoryUrl = remoteUrl;
            }
            catch
            {
                // git pode não estar disponível — contexto fica parcial
            }

            return ctx;
        }

        private static string? ExecutarGit(string args, string workingDir)
        {
            try
            {
                var psi = new ProcessStartInfo("git", args)
                {
                    WorkingDirectory       = workingDir,
                    RedirectStandardOutput = true,
                    UseShellExecute        = false,
                    CreateNoWindow         = true
                };

                using var proc = Process.Start(psi);
                var saida = proc?.StandardOutput.ReadToEnd()?.Trim();
                proc?.WaitForExit(3000);
                return string.IsNullOrEmpty(saida) ? null : saida;
            }
            catch
            {
                return null;
            }
        }

        private GuardianToolWindowViewModel? ObterViewModel()
        {
            ThreadHelper.ThrowIfNotOnUIThread();

            var janela = _package.FindToolWindow(typeof(GuardianToolWindow), 0, create: false);
            return (janela as GuardianToolWindow)?.ViewModel;
        }
    }
}
