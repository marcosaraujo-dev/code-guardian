using System;
using System.ComponentModel.Design;
using CodeGuardian.VS.ToolWindow;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Shell.Interop;
using Task = System.Threading.Tasks.Task;

namespace CodeGuardian.VS.Commands
{
    /// <summary>
    /// Comando "Code Guardian" no menu Tools — abre a Tool Window.
    /// CommandId = 0x0100 (corresponde a cmdOpenToolWindow no .vsct).
    /// </summary>
    public sealed class OpenToolWindowCommand
    {
        public const int CommandId = 0x0100;
        public static readonly Guid CommandSet = new Guid("cba21ca3-11fa-4bbd-ab57-fc1d83a2ea95");

        private readonly AsyncPackage _package;

        private OpenToolWindowCommand(AsyncPackage package, IMenuCommandService commandService)
        {
            _package = package;
            var menuItem = new OleMenuCommand(Execute, new CommandID(CommandSet, CommandId));
            commandService.AddCommand(menuItem);
        }

        public static async Task InitializeAsync(AsyncPackage package)
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync(package.DisposalToken);

            var commandService = await package.GetServiceAsync(typeof(IMenuCommandService)) as IMenuCommandService;
            if (commandService != null)
                _ = new OpenToolWindowCommand(package, commandService);
        }

        private void Execute(object sender, EventArgs e)
        {
            _ = ExecutarAsync();
        }

        private async Task ExecutarAsync()
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

            var janela = await _package.ShowToolWindowAsync(
                toolWindowType: typeof(GuardianToolWindow),
                id: 0,
                create: true,
                cancellationToken: _package.DisposalToken);

            if (janela?.Frame is IVsWindowFrame frame)
                Microsoft.VisualStudio.ErrorHandler.ThrowOnFailure(frame.Show());
        }
    }
}
