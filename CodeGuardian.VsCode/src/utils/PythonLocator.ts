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

export function findRunnerScript(workspaceDir: string, configured: string): string | null {
  if (configured && fs.existsSync(configured)) {
    return configured;
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
