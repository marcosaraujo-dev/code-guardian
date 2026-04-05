@echo off
:: Executa o Code Guardian runner a partir de qualquer diretorio.
:: Uso:
::   review --file MeuService.cs
::   review --file MeuService.cs --rules-only
::   review --staged
::   review --staged --severity error

setlocal
set "SCRIPT_DIR=%~dp0code_guardian"
python "%SCRIPT_DIR%\runner.py" %*
