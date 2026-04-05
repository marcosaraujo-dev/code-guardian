using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Executa scripts Python de forma assíncrona, sem janela, com encoding UTF-8.
    /// Tenta automaticamente "python" e depois "py" (Python Launcher for Windows).
    /// </summary>
    public sealed class PythonProcessRunner
    {
        private static readonly string[] CandidatosPython = { "python", "py" };

        /// <summary>
        /// Executa o script Python e retorna o stdout completo como string.
        /// </summary>
        /// <param name="pythonExe">Executável configurado pelo usuário (default "python").</param>
        /// <param name="scriptPath">Caminho absoluto do script Python.</param>
        /// <param name="args">Argumentos CLI para o script.</param>
        /// <param name="workingDir">Diretório de trabalho (raiz do git).</param>
        /// <param name="ct">Token de cancelamento com timeout configurável.</param>
        /// <returns>Saída padrão do processo.</returns>
        /// <exception cref="PythonNotFoundException">Python não encontrado em nenhum candidato.</exception>
        /// <exception cref="OperationCanceledException">Timeout atingido.</exception>
        public async Task<string> RunAsync(
            string pythonExe,
            string scriptPath,
            string[] args,
            string workingDir,
            CancellationToken ct = default)
        {
            var candidatos = ObterCandidatos(pythonExe);
            Exception? ultimoErro = null;

            foreach (var candidato in candidatos)
            {
                try
                {
                    return await ExecutarProcessoAsync(candidato, scriptPath, args, workingDir, ct);
                }
                catch (PythonNotFoundException)
                {
                    throw;
                }
                catch (OperationCanceledException)
                {
                    throw;
                }
                catch (Exception ex) when (EhErroDePythonNaoEncontrado(ex))
                {
                    ultimoErro = ex;
                    // Tentar próximo candidato
                }
            }

            throw new PythonNotFoundException(
                $"Python não encontrado. Tentativas: {string.Join(", ", candidatos)}. " +
                "Configure o caminho em Tools > Options > Code Guardian.",
                ultimoErro);
        }

        private static string[] ObterCandidatos(string pythonExe)
        {
            if (!string.IsNullOrWhiteSpace(pythonExe) &&
                pythonExe != "python" &&
                pythonExe != "py")
            {
                // Caminho customizado configurado pelo usuário
                return new[] { pythonExe };
            }

            return CandidatosPython;
        }

        private static async Task<string> ExecutarProcessoAsync(
            string pythonExe,
            string scriptPath,
            string[] args,
            string workingDir,
            CancellationToken ct)
        {
            var argumentos = MontarArgumentos(scriptPath, args);

            var startInfo = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = argumentos,
                WorkingDirectory = workingDir,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8,
            };

            using var processo = new Process { StartInfo = startInfo, EnableRaisingEvents = true };

            var tcsStdout = new TaskCompletionSource<string>();
            var tcsStderr = new TaskCompletionSource<string>();
            var tcsExited = new TaskCompletionSource<int>();

            var sbOut = new StringBuilder();
            var sbErr = new StringBuilder();

            processo.OutputDataReceived += (_, e) =>
            {
                if (e.Data != null)
                    sbOut.AppendLine(e.Data);
            };

            processo.ErrorDataReceived += (_, e) =>
            {
                if (e.Data != null)
                    sbErr.AppendLine(e.Data);
            };

            processo.Exited += (_, _) => tcsExited.TrySetResult(processo.ExitCode);

            processo.Start();
            processo.BeginOutputReadLine();
            processo.BeginErrorReadLine();

            using var registro = ct.Register(() =>
            {
                try { processo.Kill(); } catch { /* ignorar se já terminou */ }
            });

            await Task.Run(() => processo.WaitForExit(), ct);

            ct.ThrowIfCancellationRequested();

            var stderr = sbErr.ToString();
            var stdout = sbOut.ToString();

            if (processo.ExitCode != 0 && string.IsNullOrWhiteSpace(stdout))
            {
                throw new GuardianScriptException(
                    $"runner.py retornou exit code {processo.ExitCode}. stderr: {stderr}");
            }

            return stdout;
        }

        private static string MontarArgumentos(string scriptPath, string[] args)
        {
            var sb = new StringBuilder();
            sb.Append('"');
            sb.Append(scriptPath.Replace("\"", "\\\""));
            sb.Append('"');

            foreach (var arg in args)
            {
                sb.Append(' ');
                if (arg.IndexOf(' ') >= 0)
                {
                    sb.Append('"');
                    sb.Append(arg.Replace("\"", "\\\""));
                    sb.Append('"');
                }
                else
                {
                    sb.Append(arg);
                }
            }

            return sb.ToString();
        }

        private static bool EhErroDePythonNaoEncontrado(Exception ex)
        {
            // Win32Exception com código 2 = arquivo não encontrado
            if (ex is System.ComponentModel.Win32Exception w32 && w32.NativeErrorCode == 2)
                return true;

            if (ex is FileNotFoundException)
                return true;

            if (ex.Message.IndexOf("O sistema não pode encontrar o arquivo especificado", StringComparison.OrdinalIgnoreCase) >= 0 ||
                ex.Message.IndexOf("The system cannot find the file", StringComparison.OrdinalIgnoreCase) >= 0)
                return true;

            return false;
        }
    }

    /// <summary>
    /// Exceção lançada quando nenhum executável Python é encontrado.
    /// </summary>
    public class PythonNotFoundException : Exception
    {
        public PythonNotFoundException(string message, Exception? innerException = null)
            : base(message, innerException) { }
    }

    /// <summary>
    /// Exceção lançada quando o runner.py termina com erro.
    /// </summary>
    public class GuardianScriptException : Exception
    {
        public GuardianScriptException(string message) : base(message) { }
    }
}
