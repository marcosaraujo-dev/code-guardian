# Code Guardian for Visual Studio

**Automated code review integrated into Visual Studio.**
Code Guardian analyzes your C# files as you work — detecting security issues, bad practices, code smells, and quality metrics — and surfaces results directly in the Error List, Tool Window, and a full HTML report.

---

## What it does

### 🔍 Static Analysis (Rule Engine)
Runs 20+ regex-based rules on every save or on demand, covering:

| Category | Examples |
|----------|----------|
| **Security** | SQL Injection, hardcoded secrets, path traversal, dangerous deserialization |
| **Reliability** | Swallowed exceptions, empty catch blocks, unbounded loops |
| **Performance** | N+1 query patterns, string concatenation in loops, missing `CancellationToken` |
| **Clean Code** | God Class detection, methods over 30 lines, deep nesting (5+ levels), magic numbers |
| **Async/Await** | `.Result` / `.Wait()` deadlock patterns, fire-and-forget without error handling |

### 📊 Code Metrics
For each analyzed file:
- Total lines
- Largest method (lines)
- Maximum nesting depth
- Constructor dependencies (coupling indicator)

### 🎯 Risk Score
Every analysis produces a **Risk Score from 0 to 100** with a visual gauge — green (low risk) through red (critical). Useful for tracking quality over time.

### 📋 Error List Integration
All issues appear directly in the Visual Studio **Error List** with:
- Severity (Error / Warning / Message)
- Rule ID
- File name and line number
- Click to navigate to the exact line

### 🪟 Tool Window Panel
A dedicated side panel (**Tools → Code Guardian**) shows:
- Risk Score with color-coded progress bar
- Issue counts by severity (Critical / Error / Warning / Info)
- Full list of individual issues with message, rule ID, file, and line
- Code metrics per file (expandable)
- **"Abrir Relatório HTML"** button — opens a self-contained HTML report in your default browser

### 🌐 HTML Report
One-click HTML report with dark theme, including:
- Risk summary card
- Metrics table per file (color-coded cells)
- Full issues table with severity badges

### 🔗 Git Hooks Integration
Optionally install a `pre-commit` hook that blocks commits containing critical issues:
- **Tools → Code Guardian: Install Git Hooks**
- Or via the InfoBar prompt that appears automatically when a solution without hooks is opened

---

## Requirements

| Requirement | Details |
|-------------|---------|
| **Visual Studio** | 2019 (16.x) or 2022 (17.x) — Community, Professional, or Enterprise |
| **Python** | 3.8 or later — must be on `PATH` or configured in settings |
| **Code Guardian scripts** | The `code_guardian/` folder must exist in your repository root |

### Getting the scripts

The analysis engine is the open-source **Code Guardian** Python scripts available at:
👉 **[github.com/marcosaraujo-dev/code-guardian](https://github.com/marcosaraujo-dev/code-guardian)** *(update with your actual repo URL)*

Clone or copy the `code_guardian/` folder into the root of your repository:

```
your-repo/
├── code_guardian/
│   ├── runner.py
│   ├── rule_engine.py
│   ├── metrics.py
│   ├── diff_parser.py
│   └── ...
├── src/
└── ...
```

---

## Quick Start

1. **Install the extension** via the `.vsix` file or the VS Marketplace
2. **Add the `code_guardian/` scripts** to your repository root (see above)
3. **Open a solution** — Code Guardian loads automatically
4. Go to **Tools → Analyze Current File (Code Guardian)** or right-click the solution node → **Analyze with Code Guardian**
5. View results in the **Error List** and in **Tools → Code Guardian** panel

---

## Configuration

Go to **Tools → Options → Code Guardian** to configure:

| Setting | Default | Description |
|---------|---------|-------------|
| Python Executable | `python` | Path to `python.exe` if not on PATH |
| Runner Script Path | *(auto-detect)* | Override path to `runner.py` |
| Analysis Timeout | `60` seconds | Max time per analysis |
| Rules Only | `false` | Skip AI analysis (faster) |

---

## Commands

| Command | Location | Description |
|---------|----------|-------------|
| **Code Guardian** | Tools menu | Open the Tool Window panel |
| **Analyze Current File** | Tools menu | Analyze the active `.cs` file |
| **Analyze with Code Guardian** | Solution Explorer context menu | Full scan of the solution directory |
| **Install Git Hooks** | Tools menu | Install pre-commit hook in the current repository |

---

## Severity Levels

| Level | Color | Meaning |
|-------|-------|---------|
| **Critical** | 🔴 Red | Security vulnerability or reliability blocker — must fix |
| **Error** | 🟠 Orange | Clear violation of best practices |
| **Warning** | 🟡 Yellow | Code smell or potential issue |
| **Info** | 🔵 Blue | Suggestion or metric observation |

---

## Risk Score Reference

| Score | Label | Meaning |
|-------|-------|---------|
| 0–10 | Low Risk | Code in good shape |
| 11–30 | Moderate | Some issues to address |
| 31–60 | High Risk | Significant problems found |
| 61–100 | Critical | Immediate attention required |

---

## Release Notes

### 1.0.0
- Initial release
- Rule Engine with 20+ rules (security, reliability, performance, clean code)
- Code metrics (lines, method size, nesting, coupling)
- Risk Score 0–100 with visual gauge
- Error List integration
- Tool Window with issue list and metrics
- HTML report generation
- Git hooks integration with InfoBar prompt

---

## Feedback & Issues

Found a bug or have a suggestion?
👉 Open an issue at **[github.com/marcosaraujo-dev/code-guardian/issues](https://github.com/marcosaraujo-dev/code-guardian/issues)** *(update with your actual repo URL)*

---

*Code Guardian is developed by [CygnusForge](https://cygnusforge.com.br) and is free to use.*
