using System;
using System.ComponentModel.Design;
using System.IO;
using CodeGuardian.VS.Analysis;
using Microsoft.VisualStudio.Shell;
using Task = System.Threading.Tasks.Task;

namespace CodeGuardian.VS.Commands
{
    /// <summary>
    /// Comando "Analyze Current File" no menu Tools.
    /// Analisa o arquivo .cs atualmente aberto no editor ativo.
    /// </summary>
    public sealed class AnalyzeFileCommand
    {
        public const int CommandId = 0x0101;
        public static readonly Guid CommandSet = new Guid("cba21ca3-11fa-4bbd-ab57-fc1d83a2ea95");

        private readonly AsyncPackage _package;
        private readonly IGuardianAnalysisService _analysisService;

        private AnalyzeFileCommand(AsyncPackage package, IMenuCommandService commandService, IGuardianAnalysisService analysisService)
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
                _ = new AnalyzeFileCommand(package, commandService, analysisService);
        }

        private void AtualizarEstado(object sender, EventArgs e)
        {
            ThreadHelper.ThrowIfNotOnUIThread();

            if (sender is OleMenuCommand comando)
            {
                var arquivo = ObterArquivoAtual();
                comando.Enabled = arquivo != null && arquivo.EndsWith(".cs", StringComparison.OrdinalIgnoreCase);
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
            var arquivo = ObterArquivoAtual();

            if (string.IsNullOrEmpty(arquivo))
                return;

            // Execucao em background — nao bloquear a UI thread
            await _analysisService.AnalyzeFileAsync(arquivo!);
        }

        private static string? ObterArquivoAtual()
        {
            ThreadHelper.ThrowIfNotOnUIThread();

            var dte = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
            return dte?.ActiveDocument?.FullName;
        }
    }
}
