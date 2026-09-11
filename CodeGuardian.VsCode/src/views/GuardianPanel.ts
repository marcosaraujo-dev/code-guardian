import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import { GuardianResult } from '../models/GuardianResult';

export class GuardianPanel implements vscode.WebviewViewProvider {
  static readonly viewId = 'codeguardian.panel';

  private view?: vscode.WebviewView;
  private readonly extensionUri: vscode.Uri;
  private readonly htmlTemplatePath: string;

  constructor(extensionUri: vscode.Uri) {
    this.extensionUri = extensionUri;
    this.htmlTemplatePath = path.join(extensionUri.fsPath, 'src', 'views', 'webview', 'panel.html');
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this.buildHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage(msg => this.handleMessage(msg));
  }

  showLoading(): void {
    this.view?.webview.postMessage({ type: 'loading' });
  }

  showResult(result: GuardianResult): void {
    this.view?.webview.postMessage({ type: 'result', data: result });
  }

  showError(message: string): void {
    this.view?.webview.postMessage({ type: 'error', message });
  }

  showClear(): void {
    this.view?.webview.postMessage({ type: 'clear' });
  }

  private handleMessage(msg: { command: string; [k: string]: unknown }): void {
    switch (msg.command) {
      case 'analyzeFile':
        vscode.commands.executeCommand('codeguardian.analyzeFile');
        break;
      case 'analyzeSolution':
        vscode.commands.executeCommand('codeguardian.analyzeSolution');
        break;
      case 'analyzeIncremental':
        vscode.commands.executeCommand('codeguardian.analyzeIncremental');
        break;
      case 'exportSarif':
        vscode.commands.executeCommand('codeguardian.exportSarif');
        break;
      case 'clearResults':
        vscode.commands.executeCommand('codeguardian.clearResults');
        break;
      case 'openFile':
        this.openFileAtLine(String(msg.file), Number(msg.line));
        break;
      case 'copyIssue':
        vscode.env.clipboard.writeText(String(msg.text));
        break;
      case 'suppressIssue':
        this.suppressIssue(String(msg.file), Number(msg.line), String(msg.ruleId));
        break;
    }
  }

  private async openFileAtLine(filePath: string, line: number): Promise<void> {
    if (!fs.existsSync(filePath)) return;
    const uri = vscode.Uri.file(filePath);
    const pos = new vscode.Position(Math.max(0, line - 1), 0);
    await vscode.window.showTextDocument(uri, {
      selection: new vscode.Range(pos, pos),
      preserveFocus: false,
    });
  }

  private async suppressIssue(filePath: string, line: number, ruleId: string): Promise<void> {
    if (!fs.existsSync(filePath)) return;

    const uri = vscode.Uri.file(filePath);
    const doc = await vscode.workspace.openTextDocument(uri);
    const targetLine = Math.max(0, line - 1);
    const targetText = doc.lineAt(targetLine).text;
    const indent = targetText.match(/^(\s*)/)?.[1] ?? '';

    const edit = new vscode.WorkspaceEdit();
    edit.insert(uri, new vscode.Position(targetLine, 0), `${indent}// guardian: suppress ${ruleId}\n`);
    await vscode.workspace.applyEdit(edit);
  }

  private buildHtml(_webview: vscode.Webview): string {
    const nonce = crypto.randomBytes(16).toString('base64');
    let html = fs.readFileSync(this.htmlTemplatePath, 'utf8');
    html = html.replace(/\{\{NONCE\}\}/g, nonce);
    return html;
  }
}
