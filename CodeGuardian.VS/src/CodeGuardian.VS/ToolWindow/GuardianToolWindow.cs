using System;
using System.IO;
using System.Runtime.InteropServices;
using CodeGuardian.VS.Analysis;
using CodeGuardian.VS.GitHooks;
using Microsoft.VisualStudio.Shell;

namespace CodeGuardian.VS.ToolWindow
{
    /// <summary>
    /// Tool Window do Code Guardian — acessivel via Tools > Code Guardian.
    /// </summary>
    [Guid("c3d4e5f6-a7b8-9012-cdef-012345678902")]
    public sealed class GuardianToolWindow : ToolWindowPane
    {
        private GuardianToolWindowControl?   _controle;
        private GuardianToolWindowViewModel? _viewModel;

        /// <summary>Expõe o ViewModel para que comandos externos possam acessar o último resultado.</summary>
        public GuardianToolWindowViewModel? ViewModel => _viewModel;

        public GuardianToolWindow() : base(null)
        {
            Caption = "Code Guardian";
        }

        protected override void Initialize()
        {
            base.Initialize();

            try
            {
                var service = ((System.IServiceProvider?)Package)
                              ?.GetService(typeof(SGuardianAnalysisService))
                              as IGuardianAnalysisService;

                var hookService = (Package as CodeGuardian.VS.Package.CodeGuardianPackage)?.HookService;

                _viewModel = new GuardianToolWindowViewModel(service, hookService);
                _viewModel.PropertyChanged += AoViewModelAlterado;
                _controle  = new GuardianToolWindowControl { DataContext = _viewModel };
                Content    = _controle;

                ThreadHelper.ThrowIfNotOnUIThread();
                var dte     = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                var solPath = dte?.Solution?.FullName;
                if (!string.IsNullOrEmpty(solPath))
                {
                    var solDir = Path.GetDirectoryName(solPath);
                    var gitDir = HookInstallService.EncontrarDiretorioGit(solDir!);
                    _viewModel.AtualizarStatusHook(gitDir, solDir);
                }
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show(
                    $"Erro ao inicializar Code Guardian:\n\n{ex.GetType().Name}: {ex.Message}\n\n{ex.StackTrace}",
                    "Code Guardian — Erro",
                    System.Windows.MessageBoxButton.OK,
                    System.Windows.MessageBoxImage.Error);
            }
        }

        private void AoViewModelAlterado(object sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            if (e.PropertyName == nameof(GuardianToolWindowViewModel.CountCritical) ||
                e.PropertyName == nameof(GuardianToolWindowViewModel.CountError))
            {
                AtualizarCaption();
            }
        }

        private void AtualizarCaption()
        {
            var criticos = _viewModel?.CountCritical ?? 0;
            var erros    = _viewModel?.CountError    ?? 0;
            var total    = criticos + erros;
            Caption = total > 0 ? $"Code Guardian ({total})" : "Code Guardian";
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                if (_viewModel != null)
                    _viewModel.PropertyChanged -= AoViewModelAlterado;
                _viewModel?.Dispose();
            }

            base.Dispose(disposing);
        }
    }
}
