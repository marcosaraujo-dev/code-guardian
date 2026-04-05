using System;
using System.ComponentModel.Design;
using System.IO;
using CodeGuardian.VS.GitHooks;
using Microsoft.VisualStudio.Shell;
using Task = System.Threading.Tasks.Task;

namespace CodeGuardian.VS.Commands
{
    /// <summary>
    /// Comando "Code Guardian: Install Git Hooks" no menu Tools.
    /// </summary>
    public sealed class InstallHooksCommand
    {
        public const int CommandId = 0x0103;
        public static readonly Guid CommandSet = new Guid("cba21ca3-11fa-4bbd-ab57-fc1d83a2ea95");

        private readonly AsyncPackage _package;
        private readonly HookInstallService _hookService;

        private InstallHooksCommand(AsyncPackage package, IMenuCommandService commandService, HookInstallService hookService)
        {
            _package = package;
            _hookService = hookService;

            var menuItem = new OleMenuCommand(Execute, new CommandID(CommandSet, CommandId));
            commandService.AddCommand(menuItem);
        }

        public static async Task InitializeAsync(AsyncPackage package, HookInstallService hookService)
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync(package.DisposalToken);

            var commandService = await package.GetServiceAsync(typeof(IMenuCommandService)) as IMenuCommandService;

            if (commandService != null)
                _ = new InstallHooksCommand(package, commandService, hookService);
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

            await _hookService.InstallHooksAsync(solutionDir!);
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
