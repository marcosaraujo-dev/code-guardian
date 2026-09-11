import * as vscode from 'vscode';

export interface GuardianSettings {
  pythonExecutable: string;
  analyzeOnSave: boolean;
  rulesOnly: boolean;
  minimumSeverity: string;
  timeoutSeconds: number;
  runnerScriptPath: string;
  ia: {
    providerPrimary: string;
    providerFallback: string;
    ollamaUrl: string;
    ollamaModel: string;
  };
}

export function loadSettings(): GuardianSettings {
  const cfg = vscode.workspace.getConfiguration('codeguardian');
  return {
    pythonExecutable: cfg.get<string>('pythonExecutable', 'python'),
    analyzeOnSave: cfg.get<boolean>('analyzeOnSave', true),
    rulesOnly: cfg.get<boolean>('rulesOnly', true),
    minimumSeverity: cfg.get<string>('minimumSeverity', 'warning'),
    timeoutSeconds: cfg.get<number>('timeoutSeconds', 30),
    runnerScriptPath: cfg.get<string>('runnerScriptPath', ''),
    ia: {
      providerPrimary: cfg.get<string>('ia.providerPrimary', 'ollama'),
      providerFallback: cfg.get<string>('ia.providerFallback', 'none'),
      ollamaUrl: cfg.get<string>('ia.ollamaUrl', 'http://localhost:11434'),
      ollamaModel: cfg.get<string>('ia.ollamaModel', 'qwen2.5-coder:32b'),
    },
  };
}
