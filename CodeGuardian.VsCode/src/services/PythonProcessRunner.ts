import { spawn } from 'child_process';
import * as vscode from 'vscode';
import { getPythonCandidates } from '../utils/PythonLocator';

export class PythonNotFoundException extends Error {}
export class GuardianScriptException extends Error {}

export interface RunOptions {
  scriptPath: string;
  args: string[];
  workingDir: string;
  envVars?: Record<string, string>;
  timeoutMs?: number;
}

export class PythonProcessRunner {
  private readonly output: vscode.OutputChannel;
  private resolvedPython: string | null = null;
  private configuredPython: string | null = null;

  constructor(output: vscode.OutputChannel) {
    this.output = output;
  }

  async run(configuredPython: string, options: RunOptions): Promise<string> {
    const python = await this.resolvePython(configuredPython);
    return this.execute(python, options);
  }

  private async resolvePython(configured: string): Promise<string> {
    // Invalidar cache se o usuário mudou o executável nas Settings
    if (this.configuredPython !== configured) {
      this.resolvedPython = null;
      this.configuredPython = configured;
    }

    if (this.resolvedPython) {
      return this.resolvedPython;
    }

    for (const candidate of getPythonCandidates(configured)) {
      const ok = await this.testPython(candidate);
      if (ok) {
        this.resolvedPython = candidate;
        return candidate;
      }
    }
    throw new PythonNotFoundException(
      'Python não encontrado. Configure "codeguardian.pythonExecutable" nas Settings.'
    );
  }

  private testPython(exe: string): Promise<boolean> {
    return new Promise(resolve => {
      const proc = spawn(exe, ['--version'], { stdio: 'pipe', shell: process.platform === 'win32' });
      proc.on('close', code => resolve(code === 0));
      proc.on('error', () => resolve(false));
    });
  }

  private execute(python: string, options: RunOptions): Promise<string> {
    const { scriptPath, args, workingDir, envVars = {}, timeoutMs = 30_000 } = options;

    return new Promise((resolve, reject) => {
      const env = { ...process.env, ...envVars };
      const proc = spawn(python, [scriptPath, ...args], {
        cwd: workingDir,
        env,
        stdio: 'pipe',
        shell: false,
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (chunk: Buffer) => { stdout += chunk.toString('utf8'); });
      proc.stderr.on('data', (chunk: Buffer) => {
        const text = chunk.toString('utf8');
        stderr += text;
        this.output.appendLine(`[guardian stderr] ${text.trimEnd()}`);
      });

      const timer = setTimeout(() => {
        proc.kill();
        reject(new GuardianScriptException(`Análise cancelada: timeout de ${timeoutMs / 1000}s atingido.`));
      }, timeoutMs);

      proc.on('close', code => {
        clearTimeout(timer);
        if (code !== 0 && !stdout.includes('{')) {
          reject(new GuardianScriptException(stderr || `runner.py encerrou com código ${code}.`));
          return;
        }
        resolve(stdout);
      });

      proc.on('error', err => {
        clearTimeout(timer);
        reject(new PythonNotFoundException(`Falha ao iniciar Python: ${err.message}`));
      });
    });
  }
}
