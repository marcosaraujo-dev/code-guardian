import * as fs from 'fs';
import * as path from 'path';

const CANDIDATES_WINDOWS = ['python', 'py', 'python3'];
const CANDIDATES_UNIX = ['python3', 'python'];

export function getPythonCandidates(configured: string): string[] {
  if (configured && configured !== 'python') {
    return [configured];
  }
  return process.platform === 'win32' ? CANDIDATES_WINDOWS : CANDIDATES_UNIX;
}

/** Variável de ambiente compartilhada com o MCP `cygnus-code-guardian` do harness. */
const CODE_GUARDIAN_PATH_ENV = 'CODE_GUARDIAN_PATH';

/** Orientação exibida quando o runner.py não é localizado por nenhuma das fontes. */
export const RUNNER_NAO_ENCONTRADO_DICA =
  'Configure a setting "codeguardian.runnerScriptPath" ou a variável de ambiente ' +
  `${CODE_GUARDIAN_PATH_ENV} (pasta code_guardian/), ou mantenha code_guardian/ na raiz do projeto.`;

/**
 * Ordem de resolução: setting explícita → `CODE_GUARDIAN_PATH` (pasta `code_guardian/`)
 * → `code_guardian/runner.py` subindo a árvore a partir do workspace.
 */
export function findRunnerScript(workspaceDir: string, configured: string): string | null {
  if (configured && fs.existsSync(configured)) {
    return configured;
  }

  const envDir = process.env[CODE_GUARDIAN_PATH_ENV];
  if (envDir) {
    const candidatoEnv = path.join(envDir, 'runner.py');
    if (fs.existsSync(candidatoEnv)) {
      return candidatoEnv;
    }
  }

  let dir: string | null = workspaceDir;
  while (dir) {
    const candidate = path.join(dir, 'code_guardian', 'runner.py');
    if (fs.existsSync(candidate)) {
      return candidate;
    }
    const parent = path.dirname(dir);
    if (parent === dir) {
      break;
    }
    dir = parent;
  }

  return null;
}

export function findGitRoot(startDir: string): string | null {
  let dir: string | null = startDir;
  while (dir) {
    if (fs.existsSync(path.join(dir, '.git'))) {
      return dir;
    }
    const parent = path.dirname(dir);
    if (parent === dir) {
      break;
    }
    dir = parent;
  }
  return null;
}
