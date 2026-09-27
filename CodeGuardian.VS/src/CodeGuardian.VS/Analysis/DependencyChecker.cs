using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using CodeGuardian.VS.Settings;
using Microsoft.VisualStudio.Shell;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Verifica se Python e o runner.py estão acessíveis antes de executar análises.
    /// </summary>
    public static class DependencyChecker
    {
        public static async Task<DependencyStatus> CheckAsync(string? solutionDir = null)
        {
            var settings = ObterConfiguracoes();

            var (pythonOk, pythonVersion) = await VerificarPythonAsync(settings.PythonExecutable);
            var runnerPath = PythonLocator.LocalizarRunnerPy(settings.RunnerScriptPath, solutionDir);

            return new DependencyStatus
            {
                PythonOk      = pythonOk,
                PythonVersion = pythonVersion,
                RunnerOk      = runnerPath != null,
                RunnerPath    = runnerPath,
            };
        }

        private static async Task<(bool ok, string? version)> VerificarPythonAsync(string pythonExe)
        {
            foreach (var candidate in PythonLocator.ObterCandidatos(pythonExe))
            {
                try
                {
                    var psi = new ProcessStartInfo
                    {
                        FileName               = candidate,
                        Arguments              = "--version",
                        RedirectStandardOutput = true,
                        RedirectStandardError  = true,
                        UseShellExecute        = false,
                        CreateNoWindow         = true,
                    };

                    using var proc = Process.Start(psi);
                    if (proc == null) continue;

                    var stdout = await proc.StandardOutput.ReadToEndAsync().ConfigureAwait(false);
                    var stderr = await proc.StandardError.ReadToEndAsync().ConfigureAwait(false);
                    await Task.Run(() => proc.WaitForExit()).ConfigureAwait(false);

                    if (proc.ExitCode == 0)
                        return (true, (stdout + stderr).Trim());
                }
                catch
                {
                    // Tentar próximo candidato
                }
            }

            return (false, null);
        }

        private static CodeGuardianSettings ObterConfiguracoes()
        {
#pragma warning disable VSTHRD010
            var provider = ServiceProvider.GlobalProvider?.GetService(typeof(ICodeGuardianSettingsProvider))
                           as ICodeGuardianSettingsProvider;
#pragma warning restore VSTHRD010
            return provider?.GetSettings() ?? CodeGuardianSettings.Padrao;
        }
    }
}
