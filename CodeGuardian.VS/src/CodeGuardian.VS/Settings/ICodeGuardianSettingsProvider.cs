namespace CodeGuardian.VS.Settings
{
    /// <summary>
    /// Contrato para obtencao de configuracoes do Code Guardian.
    /// Permite que Analysis/ acesse configuracoes sem depender diretamente do namespace Package.
    /// </summary>
    public interface ICodeGuardianSettingsProvider
    {
        CodeGuardianSettings GetSettings();
    }
}
