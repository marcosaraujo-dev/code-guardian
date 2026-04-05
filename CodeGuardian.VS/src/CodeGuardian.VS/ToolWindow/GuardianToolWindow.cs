using System;
using System.Runtime.InteropServices;
using CodeGuardian.VS.Analysis;
using Microsoft.VisualStudio.Shell;

namespace CodeGuardian.VS.ToolWindow
{
    /// <summary>
    /// Tool Window do Code Guardian — acessivel via Tools > Code Guardian.
    /// </summary>
    [Guid("c3d4e5f6-a7b8-9012-cdef-012345678902")]
    public sealed class GuardianToolWindow : ToolWindowPane
    {
        private GuardianToolWindowControl? _controle;
        private GuardianToolWindowViewModel? _viewModel;

        public GuardianToolWindow() : base(null)
        {
            Caption = "Code Guardian";
        }

        protected override void Initialize()
        {
            base.Initialize();

            // Package é herdado de ToolWindowPane — contém referência ao package pai
            var service = ((System.IServiceProvider?)Package)
                          ?.GetService(typeof(SGuardianAnalysisService))
                          as IGuardianAnalysisService;

            _viewModel = new GuardianToolWindowViewModel(service);
            _controle = new GuardianToolWindowControl
            {
                DataContext = _viewModel,
            };

            Content = _controle;
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
                _viewModel?.Dispose();

            base.Dispose(disposing);
        }
    }
}
