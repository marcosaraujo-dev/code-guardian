using System;
using System.Collections.Generic;
using System.IO;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Centraliza a busca pelo executável Python e pelo runner.py bundlado.
    /// Usado por DependencyChecker e PythonProcessRunner.
    /// </summary>
    internal static class PythonLocator
    {
        public static readonly string BundledRunnerPath =
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "CodeGuardian", "scripts", "runner.py");

        /// <summary>
        /// Retorna candidatos Python na ordem de preferência.
        /// Se o usuário configurou um caminho explícito, retorna apenas esse.
        /// </summary>
        public static IEnumerable<string> ObterCandidatos(string pythonExe)
        {
            if (!string.IsNullOrWhiteSpace(pythonExe) &&
                pythonExe != "python" &&
                pythonExe != "py")
            {
                yield return pythonExe;
                yield break;
            }

            // PATH primeiro (mais rápido)
            yield return "python";
            yield return "py";
            yield return "python3";

            // Locais de instalação comuns no Windows
            foreach (var path in BuscarInstalacoes())
                yield return path;
        }

        private static IEnumerable<string> BuscarInstalacoes()
        {
            var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);

            // %LOCALAPPDATA%\Python\*\python.exe  (Windows Store / pythoncore)
            foreach (var p in GlobarExe(Path.Combine(localAppData, "Python"), "*"))
                yield return p;

            // %LOCALAPPDATA%\Programs\Python\Python*\python.exe  (instalador per-user)
            foreach (var p in GlobarExe(Path.Combine(localAppData, "Programs", "Python"), "Python*"))
                yield return p;

            // C:\Python*\python.exe  (instalações legadas para todos os usuários)
            foreach (var p in GlobarExe(@"C:\", "Python*"))
                yield return p;
        }

        private static IEnumerable<string> GlobarExe(string baseDir, string pattern)
        {
            if (!Directory.Exists(baseDir))
                yield break;

            string[] dirs;
            try { dirs = Directory.GetDirectories(baseDir, pattern); }
            catch { yield break; }

            foreach (var dir in dirs)
            {
                var exe = Path.Combine(dir, "python.exe");
                if (File.Exists(exe))
                    yield return exe;
            }
        }
    }
}
