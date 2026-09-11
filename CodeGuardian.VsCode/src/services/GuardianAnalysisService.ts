import * as vscode from 'vscode';
import * as path from 'path';
import { GuardianResult } from '../models/GuardianResult';
import { loadSettings } from '../models/GuardianSettings';
import { PythonProcessRunner, PythonNotFoundException, GuardianScriptException } from './PythonProcessRunner';
import { findRunnerScript, findGitRoot } from '../utils/PythonLocator';

export class GuardianAnalysisService {
  readonly onCompleted = new vscode.EventEmitter<GuardianResult>();
  readonly onFailed    = new vscode.EventEmitter<string>();
  readonly onProgress  = new vscode.EventEmitter<string>();

  private running = false;
  private readonly cache = new Map<string, GuardianResult>();
  private readonly runner: PythonProcessRunner;
  private readonly output: vscode.OutputChannel;
  private lastResult: GuardianResult | null = null;

  constructor(output: vscode.OutputChannel) {
    this.output = output;
    this.runner = new PythonProcessRunner(output);
  }

  get ultimoResultado(): GuardianResult | null { return this.lastResult; }
  get emAndamento(): boolean { return this.running; }

  async analisarArquivo(filePath: string): Promise<void> {
    await this.executar(['--file', filePath, '--format', 'json'], path.dirname(filePath));
  }

  async analisarSolution(workspaceDir: string): Promise<void> {
    await this.executar(['--scan', '--dir', workspaceDir, '--format', 'json'], workspaceDir);
  }

  async analisarIncremental(workspaceDir: string): Promise<void> {
    await this.executar(['--staged', '--format', 'json'], workspaceDir);
  }

  limpar(): void {
    this.lastResult = null;
    this.cache.clear();
  }

  private async executar(args: string[], workingDir: string): Promise<void> {
    if (this.running) {
      vscode.window.showWarningMessage('Code Guardian: análise já em andamento.');
      return;
    }

    const settings = loadSettings();
    const runnerPath = findRunnerScript(workingDir, settings.runnerScriptPath);

    if (!runnerPath) {
      const msg = 'runner.py não encontrado. Certifique-se de que code_guardian/ está na raiz do projeto.';
      this.onFailed.fire(msg);
      vscode.window.showErrorMessage(`Code Guardian: ${msg}`);
      return;
    }

    if (settings.rulesOnly) {
      args.push('--rules-only');
    }

    const gitRoot = findGitRoot(workingDir) ?? workingDir;
    const envVars = this.buildEnvVars(settings);

    this.running = true;
    this.onProgress.fire('Analisando...');

    try {
      const raw = await this.runner.run(settings.pythonExecutable, {
        scriptPath: runnerPath,
        args,
        workingDir: gitRoot,
        envVars,
        timeoutMs: settings.timeoutSeconds * 1_000,
      });

      const result = this.parseOutput(raw);
      this.lastResult = result;
      this.onCompleted.fire(result);
    } catch (err) {
      const msg = err instanceof PythonNotFoundException || err instanceof GuardianScriptException
        ? (err as Error).message
        : `Erro inesperado: ${String(err)}`;

      this.output.appendLine(`[guardian error] ${msg}`);
      this.onFailed.fire(msg);
      vscode.window.showErrorMessage(`Code Guardian: ${msg}`);
    } finally {
      this.running = false;
    }
  }

  private parseOutput(raw: string): GuardianResult {
    const jsonStart = raw.indexOf('{');
    if (jsonStart === -1) {
      throw new GuardianScriptException('Saída inesperada do runner.py: JSON não encontrado.');
    }
    return JSON.parse(raw.slice(jsonStart)) as GuardianResult;
  }

  private buildEnvVars(settings: ReturnType<typeof loadSettings>): Record<string, string> {
    const vars: Record<string, string> = {};
    const { ia } = settings;

    if (ia.providerPrimary !== 'none') {
      vars['GUARDIAN_AI_PRIMARY'] = ia.providerPrimary;
    }
    if (ia.providerFallback !== 'none') {
      vars['GUARDIAN_AI_FALLBACK'] = ia.providerFallback;
    }
    if (ia.ollamaUrl) {
      vars['OLLAMA_BASE_URL'] = ia.ollamaUrl;
    }
    if (ia.ollamaModel) {
      vars['OLLAMA_MODEL'] = ia.ollamaModel;
    }
    return vars;
  }
}
