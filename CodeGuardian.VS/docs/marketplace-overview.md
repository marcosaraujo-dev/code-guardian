# Code Guardian for Visual Studio

**Automated C# code review integrated into Visual Studio.**
Code Guardian analyzes your C# files on demand — detecting security vulnerabilities, bad practices, code smells, and quality metrics — and surfaces results directly in the Error List, Tool Window, and a full HTML report.

> No cloud. No external services. Runs entirely on your machine.

---

## What it detects

| Category | Examples |
|----------|----------|
| **Security** | SQL Injection, hardcoded secrets, path traversal, dangerous deserialization |
| **Reliability** | Swallowed exceptions, empty catch blocks, unbounded loops |
| **Performance** | N+1 query patterns, string concatenation in loops, missing `CancellationToken` |
| **Clean Code** | God Class, methods over 30 lines, deep nesting (5+ levels), magic numbers |
| **Async/Await** | `.Result` / `.Wait()` deadlock patterns, fire-and-forget without error handling |

---

## Features

### 🎯 Risk Score 0–100
Every analysis produces a visual Risk Score — green (low risk) through red (critical).

| Score | Label |
|-------|-------|
| 0–10 | Low Risk |
| 11–30 | Moderate |
| 31–60 | High Risk |
| 61–100 | Critical |

### 📋 Error List Integration
All issues appear in the Visual Studio **Error List** with severity, rule ID, file name, and line number — click to navigate directly to the problem.

### 🪟 Tool Window Panel
Open via **Tools → Code Guardian** to see:
- Risk Score with color-coded progress bar
- Issue counts by severity (Critical / Error / Warning / Info)
- Full issue list with message, rule ID, file, and line
- Code metrics per file (total lines, method size, nesting depth, coupling)

### 🌐 HTML Report
One-click self-contained HTML report with dark theme — risk summary, metrics table, and full issues list with severity badges.

### 🔗 Git Hooks
Install a `pre-commit` hook via **Tools → Code Guardian: Install Git Hooks** to automatically block commits containing critical issues.

---

## Requirements

| Requirement | Details |
|-------------|---------|
| **Visual Studio** | 2019 (16.x) or 2022 (17.x) — Community, Professional, or Enterprise |
| **Python** | 3.8 or later — must be on `PATH` or configured in settings |
| **Code Guardian scripts** | The `code_guardian/` folder in your repository root |

The analysis engine (Python scripts) is open-source and available at:
**[github.com/marcosaraujo-dev/code-guardian](https://github.com/marcosaraujo-dev/code-guardian)**

---

## Quick Start

1. Install the extension from the Marketplace
2. Clone or copy the `code_guardian/` folder into your repository root
3. Open a solution in Visual Studio
4. **Tools → Analyze Current File** or right-click the solution → **Analyze with Code Guardian**
5. View results in the **Error List** and **Tools → Code Guardian** panel

---

## Commands

| Command | Location |
|---------|----------|
| **Code Guardian** | Tools menu — opens the Tool Window |
| **Analyze Current File** | Tools menu — analyzes the active `.cs` file |
| **Analyze with Code Guardian** | Solution Explorer context menu — full solution scan |
| **Install Git Hooks** | Tools menu — installs pre-commit hook |

---

*Developed by [CygnusForge](https://cygnusforge.com.br) — free and open source.*
