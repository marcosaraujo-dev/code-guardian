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
            try
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                var janela = await _package.ShowToolWindowAsync(
                    toolWindowType: typeof(GuardianToolWindow),
                    id: 0,
                    create: true,
                    cancellationToken: _package.DisposalToken);

                if (janela == null)
                {
                    System.Windows.MessageBox.Show(
                        "ShowToolWindowAsync retornou null.\nVerifique se o ProvideToolWindow está registrado corretamente.",
                        "Code Guardian — Diagnóstico",
                        System.Windows.MessageBoxButton.OK,
                        System.Windows.MessageBoxImage.Warning);
                    return;
                }

                if (janela.Frame is IVsWindowFrame frame)
                    Microsoft.VisualStudio.ErrorHandler.ThrowOnFailure(frame.Show());
                else
                    System.Windows.MessageBox.Show(
                        $"Frame inválido. janela.Frame = {janela.Frame?.GetType().FullName ?? "null"}",
                        "Code Guardian — Diagnóstico",
                        System.Windows.MessageBoxButton.OK,
                        System.Windows.MessageBoxImage.Warning);
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show(
                    $"Erro ao abrir janela:\n\n{ex.GetType().Name}: {ex.Message}\n\n{ex.StackTrace}",
                    "Code Guardian — Erro",
                    System.Windows.MessageBoxButton.OK,
                    System.Windows.MessageBoxImage.Error);
            }
        }
    }
}
