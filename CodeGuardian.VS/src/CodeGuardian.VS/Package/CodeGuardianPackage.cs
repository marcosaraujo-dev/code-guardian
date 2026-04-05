using System;
using System.Runtime.InteropServices;
using System.Threading;
using CodeGuardian.VS.Analysis;
using CodeGuardian.VS.Commands;
using CodeGuardian.VS.ErrorList;
using CodeGuardian.VS.GitHooks;
using CodeGuardian.VS.Settings;
using CodeGuardian.VS.ToolWindow;
using Microsoft.VisualStudio;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Shell.Interop;
using Microsoft.VisualStudio.ComponentModelHost;
using Microsoft.VisualStudio.Shell.TableManager;
using Task = System.Threading.Tasks.Task;

namespace CodeGuardian.VS.Package
{
    /// <summary>
    /// Entry point do pacote Code Guardian VSIX.
    /// Carregado automaticamente quando uma solution esta aberta (BackgroundLoad).
    /// </summary>
    [PackageRegistration(UseManagedResourcesOnly = true, AllowsBackgroundLoading = true)]
    [ProvideAutoLoad(VSConstants.UICONTEXT.SolutionExists_string, PackageAutoLoadFlags.BackgroundLoad)]
    [ProvideMenuResource("Menus.ctmenu", 1)]
    [ProvideToolWindow(typeof(GuardianToolWindow))]
    [ProvideOptionPage(typeof(CodeGuardianOptionsPage), "Code Guardian", "General", 0, 0, true)]
    [ProvideService(typeof(SGuardianAnalysisService), IsAsyncQueryable = true)]
    [Guid("a246d773-b62f-480f-bc88-fcd1db7ceacf")]
    public sealed class CodeGuardianPackage : AsyncPackage, IVsRunningDocTableEvents, ICodeGuardianSettingsProvider
    {
        private GuardianAnalysisService? _analysisService;
        private GuardianErrorListService? _errorListService;
        private HookInstallService? _hookService;
        private uint _rdtCookie;

        protected override async Task InitializeAsync(CancellationToken cancellationToken, IProgress<ServiceProgressData> progress)
        {
            // 1. Registrar ICodeGuardianSettingsProvider (this) como servico sincrono
            //    Permite que GuardianAnalysisService acesse configuracoes sem depender do Package diretamente
            AddService(typeof(ICodeGuardianSettingsProvider), (container, ct, type) =>
                System.Threading.Tasks.Task.FromResult<object>(this), promote: true);

            // 2. Registrar GuardianAnalysisService como servico async
            AddService(typeof(SGuardianAnalysisService), (container, ct, type) =>
            {
                _analysisService = new GuardianAnalysisService();
                return System.Threading.Tasks.Task.FromResult<object>(_analysisService);
            }, promote: true);

            // Aguardar o servico ser construido antes de prosseguir
            await GetServiceAsync(typeof(SGuardianAnalysisService));

            await JoinableTaskFactory.SwitchToMainThreadAsync(cancellationToken);

            // 3. Assinar IVsRunningDocumentTable para eventos de save
            var rdt = await GetServiceAsync(typeof(SVsRunningDocumentTable)) as IVsRunningDocumentTable;
            rdt?.AdviseRunningDocTableEvents(this, out _rdtCookie);

            // 4. Inicializar Error List
            var componentModel = await GetServiceAsync(typeof(SComponentModel)) as IComponentModel;
            var tableManagerProvider = componentModel?.GetService<ITableManagerProvider>();
            if (tableManagerProvider != null && _analysisService != null)
            {
                var tableManager = tableManagerProvider.GetTableManager(StandardTables.ErrorsTable);
                _errorListService = new GuardianErrorListService(tableManager, _analysisService);
            }

            // 5. Inicializar Hook Service e verificar hooks
            _hookService = new HookInstallService(this);
            await _hookService.CheckAndPromptAsync();

            // 6. Registrar comandos de menu
            await OpenToolWindowCommand.InitializeAsync(this);
            await AnalyzeFileCommand.InitializeAsync(this);
            await AnalyzeSolutionCommand.InitializeAsync(this);

            if (_hookService != null)
                await InstallHooksCommand.InitializeAsync(this, _hookService);
        }

        // ------------------------------------------------------------------
        // ICodeGuardianSettingsProvider
        // ------------------------------------------------------------------

        public CodeGuardianSettings GetSettings()
        {
            // GetDialogPage pode ser chamado em qualquer thread para leitura
            var pagina = GetDialogPage(typeof(CodeGuardianOptionsPage)) as CodeGuardianOptionsPage;
            return pagina?.ToSettings() ?? CodeGuardianSettings.Padrao;
        }

        // ------------------------------------------------------------------
        // IVsRunningDocTableEvents — eventos de save de documentos
        // ------------------------------------------------------------------

        public int OnAfterSave(uint docCookie)
        {
            _ = JoinableTaskFactory.RunAsync(async () =>
            {
                await JoinableTaskFactory.SwitchToMainThreadAsync();

#pragma warning disable VSTHRD103 // já estamos no main thread após SwitchToMainThreadAsync
                var rdt = GetService(typeof(SVsRunningDocumentTable)) as IVsRunningDocumentTable;
#pragma warning restore VSTHRD103
                if (rdt == null) return;

                rdt.GetDocumentInfo(docCookie,
                    out _,  // grfRDTFlags
                    out _,  // dwReadLocks
                    out _,  // dwEditLocks
                    out var moniker,
                    out _,  // pHier
                    out _,  // itemId
                    out _); // ppunkDocData

                if (string.IsNullOrEmpty(moniker))
                    return;

                if (!moniker.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                    return;

                var cfg = GetSettings();
                if (!cfg.AnalyzeOnSave)
                    return;

                if (_analysisService != null)
                    await _analysisService.AnalyzeFileAsync(moniker);
            });

            return VSConstants.S_OK;
        }

        public int OnAfterFirstDocumentLock(uint docCookie, uint dwRDTLockType, uint dwReadLocksRemaining, uint dwEditLocksRemaining) => VSConstants.S_OK;
        public int OnBeforeLastDocumentUnlock(uint docCookie, uint dwRDTLockType, uint dwReadLocksRemaining, uint dwEditLocksRemaining) => VSConstants.S_OK;
        public int OnAfterAttributeChange(uint docCookie, uint grfAttribs) => VSConstants.S_OK;
        public int OnBeforeDocumentWindowShow(uint docCookie, int fFirstShow, IVsWindowFrame pFrame) => VSConstants.S_OK;
        public int OnAfterDocumentWindowHide(uint docCookie, IVsWindowFrame pFrame) => VSConstants.S_OK;

        // ------------------------------------------------------------------

        protected override void Dispose(bool disposing)
        {
            ThreadHelper.ThrowIfNotOnUIThread();
            if (disposing)
            {

                if (_rdtCookie != 0)
                {
                    var rdt = GetService(typeof(SVsRunningDocumentTable)) as IVsRunningDocumentTable;
                    rdt?.UnadviseRunningDocTableEvents(_rdtCookie);
                    _rdtCookie = 0;
                }

                _errorListService?.Dispose();
            }

            base.Dispose(disposing);
        }
    }
}
