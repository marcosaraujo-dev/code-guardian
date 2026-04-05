using System.Globalization;
using System.Windows;
using System.Windows.Data;

namespace CodeGuardian.VS.ToolWindow
{
    /// <summary>
    /// Code-behind minimo do GuardianToolWindowControl.
    /// Toda a logica reside no GuardianToolWindowViewModel.
    /// </summary>
    public partial class GuardianToolWindowControl : System.Windows.Controls.UserControl
    {
        public GuardianToolWindowControl()
        {
            InitializeComponent();
        }

        /// <summary>
        /// Abre o relatório HTML no navegador padrão quando o botão é clicado.
        /// </summary>
        private void BtnAbrirRelatorio_Click(object sender, System.Windows.RoutedEventArgs e)
        {
            if (DataContext is GuardianToolWindowViewModel vm && vm.UltimoResultado != null)
                vm.AbrirRelatorio(vm.UltimoResultado);
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
}
