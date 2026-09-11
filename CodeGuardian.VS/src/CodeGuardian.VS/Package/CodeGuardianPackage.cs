using System;
using System.Collections.Concurrent;
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
        private const int DEBOUNCE_DELAY_MS = 1500;

        private GuardianAnalysisService? _analysisService;
        private GuardianErrorListService? _errorListService;
        private HookInstallService? _hookService;
        private uint _rdtCookie;
        private IVsRunningDocumentTable? _rdt;

        // Debounce: evita disparar análise múltipla quando o arquivo é salvo rapidamente
        private readonly ConcurrentDictionary<string, CancellationTokenSource> _debounceTokens =
            new ConcurrentDictionary<string, CancellationTokenSource>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Expoe o servico de hooks para que a Tool Window possa consultar e alterar o estado.
        /// </summary>
        public HookInstallService? HookService => _hookService;

        protected override async Task InitializeAsync(CancellationToken cancellationToken, IProgress<ServiceProgressData> progress)
        {
            // 1. Registrar ICodeGuardianSettingsProvider (this) como servico sincrono
            AddService(typeof(ICodeGuardianSettingsProvider), (container, ct, type) =>
                System.Threading.Tasks.Task.FromResult<object>(this), promote: true);

            // 2. Registrar GuardianAnalysisService como servico async
            AddService(typeof(SGuardianAnalysisService), (container, ct, type) =>
            {
                _analysisService = new GuardianAnalysisService();
                return System.Threading.Tasks.Task.FromResult<object>(_analysisService);
            }, promote: true);

            await GetServiceAsync(typeof(SGuardianAnalysisService));

            await JoinableTaskFactory.SwitchToMainThreadAsync(cancellationToken);

            // 3. Assinar IVsRunningDocumentTable para eventos de save
            _rdt = await GetServiceAsync(typeof(SVsRunningDocumentTable)) as IVsRunningDocumentTable;
            _rdt?.AdviseRunningDocTableEvents(this, out _rdtCookie);

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
            await ExportSarifCommand.InitializeAsync(this);

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
            ThreadHelper.ThrowIfNotOnUIThread();

            if (_rdt == null || _analysisService == null)
                return VSConstants.S_OK;

            _rdt.GetDocumentInfo(docCookie, out _, out _, out _, out var moniker, out _, out _, out _);
            if (string.IsNullOrEmpty(moniker) || !moniker.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                return VSConstants.S_OK;

            var cfg = GetSettings();
            if (!cfg.AnalyzeOnSave)
                return VSConstants.S_OK;

            // Debounce: cancelar análise pendente se o arquivo for salvo novamente em menos de 1.5s
            if (_debounceTokens.TryRemove(moniker, out var anterior))
                anterior.Cancel();

            var debounce = new CancellationTokenSource();
            _debounceTokens[moniker] = debounce;

            var capturedMoniker = moniker;
            _ = JoinableTaskFactory.RunAsync(async () =>
            {
                try
                {
                    await System.Threading.Tasks.Task.Delay(DEBOUNCE_DELAY_MS, debounce.Token).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    return; // Novo save chegou para este arquivo — esta análise é descartada
                }

                _debounceTokens.TryRemove(capturedMoniker, out _);
                if (_analysisService != null)
                    await _analysisService.AnalyzeFileAsync(capturedMoniker);
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
                // Cancelar todas as análises com debounce pendentes
                foreach (var cts in _debounceTokens.Values)
                    cts.Cancel();
                _debounceTokens.Clear();

                if (_rdtCookie != 0)
                {
                    _rdt?.UnadviseRunningDocTableEvents(_rdtCookie);
                    _rdtCookie = 0;
                }

                _errorListService?.Dispose();
            }

            base.Dispose(disposing);
        }
    }
}
