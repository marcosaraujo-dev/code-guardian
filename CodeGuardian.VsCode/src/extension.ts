import * as vscode from 'vscode';
import { GuardianAnalysisService } from './services/GuardianAnalysisService';
import { HookInstallService } from './services/HookInstallService';
import { GuardianPanel } from './views/GuardianPanel';
import { loadSettings } from './models/GuardianSettings';
import { GuardianResult } from './models/GuardianResult';

const DEBOUNCE_DELAY_MS = 1500;

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel('Code Guardian');
  const panel  = new GuardianPanel(context.extensionUri);
  const service = new GuardianAnalysisService(output);
  const hooks  = new HookInstallService();

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(GuardianPanel.viewId, panel)
  );

  service.onCompleted.event(result => {
    panel.showResult(result);
    atualizarDiagnosticos(result, diagnostics);
  }, null, context.subscriptions);

  service.onFailed.event(msg => {
    panel.showError(msg);
  }, null, context.subscriptions);

  service.onProgress.event(() => {
    panel.showLoading();
  }, null, context.subscriptions);

  const diagnostics = vscode.languages.createDiagnosticCollection('codeguardian');
  context.subscriptions.push(diagnostics);

  context.subscriptions.push(
    vscode.commands.registerCommand('codeguardian.analyzeFile', async () => {
      const filePath = vscode.window.activeTextEditor?.document.uri.fsPath;
      if (!filePath) {
        vscode.window.showWarningMessage('Code Guardian: nenhum arquivo aberto.');
        return;
      }
      await service.analisarArquivo(filePath);
    }),

    vscode.commands.registerCommand('codeguardian.analyzeSolution', async () => {
      const workspaceDir = vscode.workspace.workspaceFolders?.[0].uri.fsPath;
      if (!workspaceDir) {
        vscode.window.showWarningMessage('Code Guardian: nenhum workspace aberto.');
        return;
      }
      await service.analisarSolution(workspaceDir);
    }),

    vscode.commands.registerCommand('codeguardian.analyzeIncremental', async () => {
      const workspaceDir = vscode.workspace.workspaceFolders?.[0].uri.fsPath;
      if (!workspaceDir) {
        vscode.window.showWarningMessage('Code Guardian: nenhum workspace aberto.');
        return;
      }
      await service.analisarIncremental(workspaceDir);
    }),

    vscode.commands.registerCommand('codeguardian.clearResults', () => {
      service.limpar();
      diagnostics.clear();
      panel.showClear();
    }),

    vscode.commands.registerCommand('codeguardian.installHooks', () => {
      const workspaceDir = vscode.workspace.workspaceFolders?.[0].uri.fsPath;
      if (!workspaceDir) return;
      hooks.verificarEInstalar(workspaceDir);
    }),

    vscode.commands.registerCommand('codeguardian.exportSarif', () => {
      vscode.window.showInformationMessage('Code Guardian: exportação SARIF será implementada na Fase 2.');
    }),

    vscode.commands.registerCommand('codeguardian.openPanel', () => {
      vscode.commands.executeCommand('workbench.view.extension.codeguardian');
    }),

    vscode.workspace.onDidSaveTextDocument(doc => {
      if (doc.languageId !== 'csharp') return;
      const settings = loadSettings();
      if (!settings.analyzeOnSave) return;

      // Debounce: aguardar 1.5s antes de disparar — evita processos Python em rafaga de saves
      const filePath = doc.uri.fsPath;
      clearTimeout(saveDebounceTimer);
      saveDebounceTimer = setTimeout(() => service.analisarArquivo(filePath), DEBOUNCE_DELAY_MS);
    })
  );

  // Verificar hooks de forma diferida — não bloquear o activate com I/O síncrono
  setTimeout(() => {
    const workspaceDir = vscode.workspace.workspaceFolders?.[0].uri.fsPath;
    if (workspaceDir) {
      hooks.verificarEInstalar(workspaceDir);
    }
  }, 2000);
}

let saveDebounceTimer: ReturnType<typeof setTimeout> | undefined;

export function deactivate(): void { /* cleanup via subscriptions */ }

function atualizarDiagnosticos(result: GuardianResult | null, collection: vscode.DiagnosticCollection): void {
  if (!result) return;

  collection.clear();

  const porArquivo = new Map<string, vscode.Diagnostic[]>();

  for (const issue of result.issues) {
    const uri = vscode.Uri.file(issue.file);
    const key = uri.toString();

    const range = new vscode.Range(
      Math.max(0, issue.line - 1), 0,
      Math.max(0, issue.line - 1), Number.MAX_SAFE_INTEGER
    );

    const sev = issue.severity === 'critical' || issue.severity === 'error'
      ? vscode.DiagnosticSeverity.Error
      : issue.severity === 'warning'
        ? vscode.DiagnosticSeverity.Warning
        : vscode.DiagnosticSeverity.Information;

    const diag = new vscode.Diagnostic(range, `[${issue.rule_id}] ${issue.message}`, sev);
    diag.source = 'Code Guardian';
    diag.code = issue.rule_id;

    const list = porArquivo.get(key) ?? [];
    list.push(diag);
    porArquivo.set(key, list);
  }

  for (const [key, diags] of porArquivo) {
    collection.set(vscode.Uri.parse(key), diags);
  }
}
