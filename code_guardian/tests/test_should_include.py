"""TC-DP-001 a TC-DP-005 — Testa a funcao _should_include do diff_parser."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from diff_parser import _should_include

falhas = []

def check(descricao, resultado, esperado):
    if resultado != esperado:
        falhas.append(f"  FALHOU [{descricao}]: obteve {resultado}, esperava {esperado}")

# TC-DP-001 — Migrations excluidas
check("TC-DP-001 Migrations", _should_include("src/Data/Migrations/20240101_Init.cs"), False)

# TC-DP-002 — Designer.cs excluido
check("TC-DP-002 Designer.cs", _should_include("src/Forms/MainForm.Designer.cs"), False)

# TC-DP-003 — /obj/ e /bin/ excluidos
check("TC-DP-003 obj", _should_include("src/obj/Debug/Service.cs"), False)
check("TC-DP-003 bin", _should_include("src/bin/Release/App.cs"), False)

# TC-DP-004 — AssemblyInfo.cs excluido
check("TC-DP-004 AssemblyInfo", _should_include("Properties/AssemblyInfo.cs"), False)

# TC-DP-005 — Outras extensoes excluidas
check("TC-DP-005 .py", _should_include("scripts/build.py"), False)
check("TC-DP-005 .json", _should_include("config.json"), False)
check("TC-DP-005 .md", _should_include("README.md"), False)

# Deve incluir arquivos .cs validos
check("Incluir Services", _should_include("src/Services/UserService.cs"), True)
check("Incluir Controllers", _should_include("src/Controllers/UserController.cs"), True)

if falhas:
    print("FALHOU:")
    for f in falhas:
        print(f)
    sys.exit(1)
else:
    print("TC-DP-001 a TC-DP-005: PASSOU")
    sys.exit(0)
