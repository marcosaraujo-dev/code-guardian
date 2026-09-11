using System;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Microsoft.VisualStudio.Shell;

namespace CodeGuardian.VS.ToolWindow
{
    /// <summary>
    /// Code-behind do GuardianToolWindowControl.
    /// Handlers de botão ficam aqui pois precisam de APIs do VS (DTE).
    /// </summary>
    public partial class GuardianToolWindowControl : System.Windows.Controls.UserControl
    {
        public GuardianToolWindowControl()
        {
            InitializeComponent();
            Loaded += OnControlLoaded;
        }

        private void OnControlLoaded(object sender, RoutedEventArgs e)
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                var dte          = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                var solutionPath = dte?.Solution?.FullName;
                var solutionDir  = string.IsNullOrEmpty(solutionPath) ? null : Path.GetDirectoryName(solutionPath);

                if (DataContext is GuardianToolWindowViewModel vm)
                    await vm.VerificarDependenciasAsync(solutionDir);
            });
        }

        private void BtnConfigurarDependencias_Click(object sender, RoutedEventArgs e)
        {
            System.Windows.MessageBox.Show(
                "Para o Code Guardian funcionar são necessários:\n\n" +
                "1. Python 3.8 ou superior instalado\n" +
                "   • Baixe em: python.org/downloads\n" +
                "   • Marque 'Add Python to PATH' durante a instalação\n\n" +
                "2. Scripts do Code Guardian no projeto\n" +
                "   • Diretório 'code_guardian/' com runner.py\n\n" +
                "Após instalar, configure em:\n" +
                "   Tools > Options > Code Guardian\n" +
                "   • Python Executable: caminho do python.exe\n" +
                "   • Runner Script Path: caminho do runner.py",
                "Como configurar dependências",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
        }

        private void BtnAnalisarArquivo_Click(object sender, RoutedEventArgs e)
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                var dte    = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                var arquivo = dte?.ActiveDocument?.FullName;

                if (DataContext is GuardianToolWindowViewModel vm)
                    await vm.AnalisarArquivoAsync(arquivo);
            });
        }

        private void BtnAnalisarSolucao_Click(object sender, RoutedEventArgs e)
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                var dte         = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                var solutionPath = dte?.Solution?.FullName;
                var solutionDir  = string.IsNullOrEmpty(solutionPath) ? null : Path.GetDirectoryName(solutionPath);

                if (DataContext is GuardianToolWindowViewModel vm)
                    await vm.AnalisarSolucaoAsync(solutionDir);
            });
        }

        private void BtnLimpar_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is GuardianToolWindowViewModel vm)
                vm.LimparAnalise();
        }

        private void BtnAbrirRelatorio_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is GuardianToolWindowViewModel vm && vm.UltimoResultado != null)
                vm.AbrirRelatorio(vm.UltimoResultado);
        }

        private void BtnExportarSarif_Click(object sender, RoutedEventArgs e)
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                var dte          = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                var solutionPath = dte?.Solution?.FullName;
                var solutionDir  = string.IsNullOrEmpty(solutionPath) ? null : Path.GetDirectoryName(solutionPath);

                if (DataContext is GuardianToolWindowViewModel vm)
                    await vm.ExportarSarifAsync(solutionDir);
            });
        }

        private void ListBoxIssues_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (sender is not ListBox lb || lb.SelectedItem is not IssueViewModel issue)
                return;

            lb.SelectedItem = null;

            if (!File.Exists(issue.CaminhoCompleto))
                return;

            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                var dte = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                if (dte == null)
                    return;

                var window = dte.ItemOperations.OpenFile(issue.CaminhoCompleto);
                if (window?.Document?.Selection is EnvDTE.TextSelection sel)
                    sel.GotoLine(issue.Line, Select: false);
            });
        }

        private void BtnCopiarIssue_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button btn && btn.DataContext is IssueViewModel vm)
            {
                System.Windows.Clipboard.SetText(vm.TextoParaCopiar);
                e.Handled = true;
            }
        }

        private void BtnSuprimirIssue_Click(object sender, RoutedEventArgs e)
        {
            if (sender is not Button btn || btn.DataContext is not IssueViewModel issue)
                return;

            e.Handled = true;

            if (!File.Exists(issue.CaminhoCompleto))
                return;

            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                var dte = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                if (dte == null)
                    return;

                var window = dte.ItemOperations.OpenFile(issue.CaminhoCompleto);
                if (window?.Document?.Selection is not EnvDTE.TextSelection sel)
                    return;

                sel.GotoLine(issue.Line, Select: false);
                sel.StartOfLine(EnvDTE.vsStartOfLineOptions.vsStartOfLineOptionsFirstText);
                sel.NewLine(1);
                sel.LineUp(false, 1);
                sel.StartOfLine(EnvDTE.vsStartOfLineOptions.vsStartOfLineOptionsFirstText);
                sel.Text = $"// guardian: suppress {issue.RuleId}";
            });
        }

        private void BtnToggleIA_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is GuardianToolWindowViewModel vm)
                vm.UsarIA = !vm.UsarIA;
        }

        private void BtnAnalisarIncremental_Click(object sender, RoutedEventArgs e)
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                var dte          = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                var solutionPath = dte?.Solution?.FullName;
                var solutionDir  = string.IsNullOrEmpty(solutionPath) ? null : Path.GetDirectoryName(solutionPath);

                if (DataContext is GuardianToolWindowViewModel vm)
                    await vm.AnalisarIncrementalAsync(solutionDir);
            });
        }

        private void BtnToggleHook_Click(object sender, RoutedEventArgs e)
        {
            _ = ThreadHelper.JoinableTaskFactory.RunAsync(async () =>
            {
                await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();

                var dte         = Microsoft.VisualStudio.Shell.Package.GetGlobalService(typeof(EnvDTE.DTE)) as EnvDTE.DTE;
                var solutionPath = dte?.Solution?.FullName;
                var solutionDir  = string.IsNullOrEmpty(solutionPath) ? null : Path.GetDirectoryName(solutionPath);

                if (DataContext is GuardianToolWindowViewModel vm && solutionDir != null)
                    await vm.ToggleHookAsync(solutionDir);
            });
        }
    }

    /// <summary>
    /// Converte bool para Visibility (true = Visible, false = Collapsed).
    /// </summary>
    public sealed class BoolToVisibilityConverter : IValueConverter
    {
        public static readonly BoolToVisibilityConverter Instance = new BoolToVisibilityConverter();

        public object Convert(object value, System.Type targetType, object parameter, CultureInfo culture)
            => value is true ? Visibility.Visible : Visibility.Collapsed;

        public object ConvertBack(object value, System.Type targetType, object parameter, CultureInfo culture)
            => value is Visibility.Visible;
    }

    /// <summary>
    /// Converte bool para Visibility invertido (true = Collapsed, false = Visible).
    /// </summary>
    public sealed class InverseBoolToVisibilityConverter : IValueConverter
    {
        public static readonly InverseBoolToVisibilityConverter Instance = new InverseBoolToVisibilityConverter();

        public object Convert(object value, System.Type targetType, object parameter, CultureInfo culture)
            => value is true ? Visibility.Collapsed : Visibility.Visible;

        public object ConvertBack(object value, System.Type targetType, object parameter, CultureInfo culture)
            => value is Visibility.Collapsed;
    }

    /// <summary>
    /// Converte string para Visibility: string não-vazia = Visible, vazia/null = Collapsed.
    /// </summary>
    /// <summary>
    /// string não-vazia → Visible; vazia/null → Collapsed.
    /// Com parameter="inverse": inverte o resultado (usado para placeholder).
    /// </summary>
    public sealed class StringNotEmptyToVisibilityConverter : IValueConverter
    {
        public static readonly StringNotEmptyToVisibilityConverter Instance = new StringNotEmptyToVisibilityConverter();

        public object Convert(object value, System.Type targetType, object parameter, CultureInfo culture)
        {
            var isEmpty  = string.IsNullOrEmpty(value as string);
            var invert   = "inverse".Equals(parameter as string, StringComparison.OrdinalIgnoreCase);
            var visible  = invert ? isEmpty : !isEmpty;
            return visible ? Visibility.Visible : Visibility.Collapsed;
        }

        public object ConvertBack(object value, System.Type targetType, object parameter, CultureInfo culture)
            => value;
    }
}
