using System;
using System.ComponentModel.Design;
using System.IO;
using CodeGuardian.VS.Analysis;
using Microsoft.VisualStudio.Shell;
using Task = System.Threading.Tasks.Task;

namespace CodeGuardian.VS.Commands
{
    /// <summary>
    /// Comando "Analyze with Code Guardian" no context menu do Solution Explorer.
    /// Executa scan completo do diretorio da solution.
    /// </summary>
    public sealed class AnalyzeSolutionCommand
    {
        public const int CommandId = 0x0102;
        public static readonly Guid CommandSet = new Guid("cba21ca3-11fa-4bbd-ab57-fc1d83a2ea95");

        private readonly AsyncPackage _package;
        private readonly IGuardianAnalysisService _analysisService;

        private AnalyzeSolutionCommand(AsyncPackage package, IMenuCommandService commandService, IGuardianAnalysisService analysisService)
        {
            _package = package;
            _analysisService = analysisService;

            var menuItem = new OleMenuCommand(Execute, new CommandID(CommandSet, CommandId));
            menuItem.BeforeQueryStatus += AtualizarEstado;
            commandService.AddCommand(menuItem);
        }

        public static async Task InitializeAsync(AsyncPackage package)
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync(package.DisposalToken);

            var commandService = await package.GetServiceAsync(typeof(IMenuCommandService)) as IMenuCommandService;
            var analysisService = await package.GetServiceAsync(typeof(SGuardianAnalysisService)) as IGuardianAnalysisService;

            if (commandService != null && analysisService != null)
                _ = new AnalyzeSolutionCommand(package, commandService, analysisService);
        }

        private void AtualizarEstado(object sender, EventArgs e)
        {
            ThreadHelper.ThrowIfNotOnUIThread();

            if (sender is OleMenuCommand comando)
            {
                var solutionDir = ObterDiretorioDaSolution();
                comando.Enabled = !string.IsNullOrEmpty(solutionDir);
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
            var solutionDir = ObterDiretorioDaSolution();

            if (string.IsNullOrEmpty(solutionDir))
                return;

            var dte = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
            if (dte != null)
                dte.StatusBar.Text = "Code Guardian: Analisando solucao...";

            await _analysisService.AnalyzeSolutionAsync(solutionDir!);
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
    }
}
