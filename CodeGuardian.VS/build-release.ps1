# build-release.ps1 - Uso: powershell -ExecutionPolicy Bypass -File build-release.ps1
# PRE-REQUISITO: projeto ja compilado pelo VS ao menos uma vez (para gerar o .pkgdef)
param([switch]$SkipBuild)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root    = $PSScriptRoot
$src     = "$root\src\CodeGuardian.VS"
$binDir  = "$src\bin\Release\net472"
$objDir  = "$src\obj\Release\net472\net472"
$resDir  = "$src\Resources"
$out     = "$root\release\CodeGuardian.VS.vsix"
$msbuild = "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"

# 1. Build sem clean (preserva pkgdef gerado pelo VS) — pulado se -SkipBuild
if (-not $SkipBuild) {
    Write-Host "Compilando..." -ForegroundColor Cyan
    & $msbuild "$root\CodeGuardian.VS.sln" /t:Build /p:Configuration=Release /p:DeployExtension=false /v:minimal
    if ($LASTEXITCODE -ne 0) { throw "Build falhou (exit $LASTEXITCODE)" }
}

# 2. Verificar pkgdef (gerado pelo VS - necessario para a extensao funcionar)
$pkgdef = "$objDir\CodeGuardian.VS.pkgdef"
if (-not (Test-Path $pkgdef)) {
    throw "CodeGuardian.VS.pkgdef nao encontrado em $objDir`nExecute o projeto pelo VS (F5 na instancia experimental) ao menos uma vez e tente novamente."
}

# 3. Gerar extension.vsixmanifest a partir do source (sem depender do VSSDK)
$ver = ([xml](Get-Content "$src\source.extension.vsixmanifest")).PackageManifest.Metadata.Identity.Version
$mf  = Get-Content "$src\source.extension.vsixmanifest" -Raw
$mf  = $mf -replace ' xmlns:d="[^"]*"', ''
$mf  = [regex]::Replace($mf, '\s+d:[A-Za-z]+="[^"]*"', '')
$mf  = $mf -replace 'Path="\|[^|;]+;PkgdefProjectOutputGroup\|"', 'Path="CodeGuardian.VS.pkgdef"'
$mf  = $mf -replace 'Path="\|[^|]+\|"', 'Path="CodeGuardian.VS.dll"'
$mf  = [regex]::Replace($mf, '(<Identity[^>]+Version=")[^"]*"', "`${1}$ver`"")
$mfTemp = "$env:TEMP\cg_manifest.xml"
[System.IO.File]::WriteAllText($mfTemp, $mf, [System.Text.Encoding]::UTF8)
Write-Host "Versao: $ver" -ForegroundColor Cyan

# 4. Empacotar VSIX
Write-Host "Empacotando VSIX..." -ForegroundColor Cyan
[System.Reflection.Assembly]::LoadWithPartialName('System.IO.Compression') | Out-Null
[System.Reflection.Assembly]::LoadWithPartialName('System.IO.Compression.FileSystem') | Out-Null
New-Item -ItemType Directory -Force -Path "$root\release" | Out-Null
Remove-Item $out -Force -ErrorAction SilentlyContinue

$tmpCt = "$env:TEMP\cg_ct.xml"
$tmpRl = "$env:TEMP\cg_rl.xml"
[System.IO.File]::WriteAllText($tmpCt, '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="vsixmanifest" ContentType="text/xml" /><Default Extension="pkgdef" ContentType="text/plain" /><Default Extension="dll" ContentType="application/octet-stream" /><Default Extension="png" ContentType="image/png" /><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" /></Types>')
[System.IO.File]::WriteAllText($tmpRl, '<?xml version="1.0" encoding="utf-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.microsoft.com/developer/vsx-schema/2011/relationships/manifest" Target="/extension.vsixmanifest" Id="R1" /></Relationships>')

$zip = [System.IO.Compression.ZipFile]::Open($out, 1)
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $tmpCt,                      '[Content_Types].xml') | Out-Null
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $tmpRl,                      '_rels/.rels') | Out-Null
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $mfTemp,                     'extension.vsixmanifest') | Out-Null
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, "$binDir\CodeGuardian.VS.dll", 'CodeGuardian.VS.dll') | Out-Null
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $pkgdef,                     'CodeGuardian.VS.pkgdef') | Out-Null
if (Test-Path "$binDir\Newtonsoft.Json.dll") {
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, "$binDir\Newtonsoft.Json.dll", 'Newtonsoft.Json.dll') | Out-Null
}
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, "$resDir\logo-codeguardian.png", 'Resources\logo-codeguardian.png') | Out-Null
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, "$binDir\LICENSE",           'LICENSE') | Out-Null
$zip.Dispose()
Remove-Item $tmpCt, $tmpRl, $mfTemp -Force -ErrorAction SilentlyContinue

# 5. Relatorio
$info = Get-Item $out
Write-Host "VSIX gerado: $out" -ForegroundColor Green
Write-Host "Versao: $ver  |  Tamanho: $([math]::Round($info.Length / 1MB, 2)) MB"
