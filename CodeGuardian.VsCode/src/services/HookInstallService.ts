import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { findGitRoot, findRunnerScript } from '../utils/PythonLocator';
import { loadSettings } from '../models/GuardianSettings';

const GUARDIAN_MARKER = '# guardian-managed';

export class HookInstallService {
  verificarEInstalar(workspaceDir: string): void {
    const gitRoot = findGitRoot(workspaceDir);
    if (!gitRoot) return;

    const hooksDir = path.join(gitRoot, '.git', 'hooks');
    const instalado = this.estaInstalado(hooksDir);

    if (!instalado) {
      vscode.window.showInformationMessage(
        'Code Guardian: deseja instalar os git hooks (pre-commit + prepare-commit-msg)?',
        'Instalar', 'Agora não'
      ).then(choice => {
        if (choice === 'Instalar') {
          this.instalar(hooksDir, gitRoot, workspaceDir);
        }
      });
    }
  }

  instalar(hooksDir: string, _gitRoot: string, workspaceDir: string): void {
    try {
      const settings = loadSettings();
      const runnerPath = findRunnerScript(workspaceDir, settings.runnerScriptPath);

      if (!runnerPath) {
        vscode.window.showErrorMessage('Code Guardian: runner.py não encontrado. Hooks não instalados.');
        return;
      }

      const runnerBash = this.toUnixPath(runnerPath);

      this.escreverHookPreCommit(hooksDir, runnerBash);
      this.escreverHookCommitMsg(hooksDir, runnerBash);

      vscode.window.showInformationMessage('Code Guardian: git hooks instalados com sucesso.');
    } catch (err) {
      vscode.window.showErrorMessage(`Code Guardian: falha ao instalar hooks — ${String(err)}`);
    }
  }

  remover(hooksDir: string): void {
    for (const name of ['pre-commit', 'prepare-commit-msg']) {
      const hookPath = path.join(hooksDir, name);
      if (!fs.existsSync(hookPath)) continue;

      const content = fs.readFileSync(hookPath, 'utf8');
      if (!content.includes(GUARDIAN_MARKER)) continue;

      const linhasLimpas = content
        .split('\n')
        .filter(l => !l.includes(GUARDIAN_MARKER) && !l.includes('guardian') && !l.includes('runner.py'))
        .join('\n');

      if (linhasLimpas.trim() === '#!/bin/sh') {
        fs.unlinkSync(hookPath);
      } else {
        fs.writeFileSync(hookPath, linhasLimpas, 'utf8');
      }
    }
    vscode.window.showInformationMessage('Code Guardian: git hooks removidos.');
  }

  private estaInstalado(hooksDir: string): boolean {
    const hookPath = path.join(hooksDir, 'pre-commit');
    if (!fs.existsSync(hookPath)) return false;
    return fs.readFileSync(hookPath, 'utf8').includes(GUARDIAN_MARKER);
  }

  private escreverHookPreCommit(hooksDir: string, runnerBash: string): void {
    const hookPath = path.join(hooksDir, 'pre-commit');
    const content = [
      '#!/bin/sh',
      `${GUARDIAN_MARKER}`,
      `python "${runnerBash}" --staged --rules-only --format json --fail-on error`,
      'EXIT_CODE=$?',
      'if [ $EXIT_CODE -ne 0 ]; then',
      '  echo "Code Guardian: commit bloqueado por issues críticas. Corrija antes de commitar."',
      '  exit 1',
      'fi',
      'exit 0',
    ].join('\n');

    this.escreverHook(hookPath, content);
  }

  private escreverHookCommitMsg(hooksDir: string, runnerBash: string): void {
    const hookPath = path.join(hooksDir, 'prepare-commit-msg');
    const content = [
      '#!/bin/sh',
      `${GUARDIAN_MARKER}`,
      'COMMIT_MSG_FILE=$1',
      `SCORE=$(python "${runnerBash}" --staged --rules-only --format json 2>/dev/null | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('risk_score','-'))" 2>/dev/null || echo "-")`,
      `echo "" >> "$COMMIT_MSG_FILE"`,
      `echo "Guardian-Review: Score $SCORE" >> "$COMMIT_MSG_FILE"`,
    ].join('\n');

    this.escreverHook(hookPath, content);
  }

  private escreverHook(hookPath: string, content: string): void {
    if (fs.existsSync(hookPath)) {
      const existing = fs.readFileSync(hookPath, 'utf8');
      if (!existing.includes(GUARDIAN_MARKER)) {
        vscode.window.showWarningMessage(
          `Code Guardian: ${path.basename(hookPath)} já existe e não é gerenciado pelo Guardian. Hook não sobrescrito.`
        );
        return;
      }
    }
    fs.writeFileSync(hookPath, content, { mode: 0o755, encoding: 'utf8' });
  }

  private toUnixPath(winPath: string): string {
    if (process.platform !== 'win32') return winPath;
    return winPath
      .replace(/\\/g, '/')
      .replace(/^([A-Za-z]):/, (_, d: string) => `/${d.toLowerCase()}`);
  }
}
