@echo off
:: Executa a suite de testes do Code Guardian a partir de qualquer diretorio.
:: Uso:
::   test-guardian          -> todos os testes
::   test-guardian re       -> apenas rule_engine
::   test-guardian me       -> apenas metrics
::   test-guardian dp       -> apenas diff_parser
::   test-guardian ai       -> apenas ai_client
::   test-guardian ru       -> apenas runner

setlocal
set "SCRIPT_DIR=%~dp0code_guardian"

if "%~1"=="" (
    python "%SCRIPT_DIR%\tests\run_tests.py"
) else (
    python "%SCRIPT_DIR%\tests\run_tests.py" --script %1
)
