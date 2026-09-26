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

        /// <summary>Variável de ambiente compartilhada com o MCP <c>cygnus-code-guardian</c> do harness.</summary>
        private const string CodeGuardianPathEnv = "CODE_GUARDIAN_PATH";

        /// <summary>
        /// Resolve o runner.py na ordem: caminho configurado → <c>CODE_GUARDIAN_PATH</c>
        /// (pasta <c>code_guardian/</c>) → <c>code_guardian/runner.py</c> subindo a árvore
        /// a partir de <paramref name="pontoDePartida"/> → scripts bundlados.
        /// </summary>
        /// <param name="runnerConfigurado">Valor de RunnerScriptPath nas Options (pode ser vazio).</param>
        /// <param name="pontoDePartida">Arquivo ou diretório de onde iniciar a busca (pode ser nulo).</param>
        public static string? LocalizarRunnerPy(string? runnerConfigurado, string? pontoDePartida)
        {
            if (!string.IsNullOrWhiteSpace(runnerConfigurado) && File.Exists(runnerConfigurado))
                return runnerConfigurado;

            var diretorioEnv = Environment.GetEnvironmentVariable(CodeGuardianPathEnv);
            if (!string.IsNullOrWhiteSpace(diretorioEnv))
            {
                var candidatoEnv = Path.Combine(diretorioEnv, "runner.py");
                if (File.Exists(candidatoEnv))
                    return candidatoEnv;
            }

            // Preferir scripts do projeto (sempre mais atualizados que os bundlados)
            var candidatoProjeto = BuscarRunnerNaArvore(pontoDePartida);
            if (candidatoProjeto != null)
                return candidatoProjeto;

            // Fallback: scripts bundlados (quando o projeto não contém code_guardian/)
            return File.Exists(BundledRunnerPath) ? BundledRunnerPath : null;
        }

        private static string? BuscarRunnerNaArvore(string? pontoDePartida)
        {
            if (string.IsNullOrEmpty(pontoDePartida))
                return null;

            var diretorio = Directory.Exists(pontoDePartida)
                ? pontoDePartida
                : Path.GetDirectoryName(pontoDePartida);

            while (!string.IsNullOrEmpty(diretorio))
            {
                var candidato = Path.Combine(diretorio, "code_guardian", "runner.py");
                if (File.Exists(candidato))
                    return candidato;

                var pai = Path.GetDirectoryName(diretorio);
                if (pai == diretorio)
                    break;

                diretorio = pai;
            }

            return null;
        }

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
