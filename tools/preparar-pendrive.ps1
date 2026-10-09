# Prepara o pendrive de instalação do Clone OS no Windows, sem programas extras.
#
# O pendrive é formatado em FAT32 e recebe o conteúdo da ISO (o boot UEFI do
# Arch funciona assim, sem gravar a imagem "crua"). Por isso ele continua sendo
# um pendrive normal: a pasta "Clone OS - Instalacao" com o README fica nele.
# Uma segunda partição (exFAT) com o espaço que sobra fica livre para seus arquivos.
#
# Precisa rodar como administrador (formatar disco exige):
#   powershell -ExecutionPolicy Bypass -File .\tools\preparar-pendrive.ps1
#   powershell -ExecutionPolicy Bypass -File .\tools\preparar-pendrive.ps1 -Disco 2   (sem perguntar qual)
#   ... -Disco 2 -SemPerguntar   (sem pedir APAGAR nem pausar; para rodar sem ninguém olhando)
param(
    [int]$Disco = -1,
    [string]$Iso = '',
    [switch]$SemPerguntar
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Start-Transcript -Path (Join-Path $env:TEMP 'clone-os-pendrive.log') -Force | Out-Null

function Pausar { if ($SemPerguntar) { return }; Read-Host 'Pressione Enter para fechar' | Out-Null }
trap {
    Write-Host "`nErro: $_" -ForegroundColor Red
    Write-Host "Registro completo: $(Join-Path $env:TEMP 'clone-os-pendrive.log')"
    Pausar; exit 1
}

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Este script precisa rodar como administrador.' -ForegroundColor Yellow
    Pausar; exit 1
}

if (-not $Iso) {
    $Iso = Get-ChildItem (Join-Path $repo 'out\cloneos-0.3*-notebook*.iso') -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime | Select-Object -Last 1 -ExpandProperty FullName
}
if (-not $Iso -or -not (Test-Path $Iso)) { Write-Host 'ISO do Clone OS 0.3.x não encontrada em out\.' -ForegroundColor Red; Pausar; exit 1 }
$guia = Join-Path $repo 'pendrive\Clone OS - Instalacao'
if (-not (Test-Path $guia)) { Write-Host "Pasta do guia não encontrada: $guia" -ForegroundColor Red; Pausar; exit 1 }

$usbs = @(Get-Disk | Where-Object { $_.BusType -eq 'USB' -and -not $_.IsBoot -and -not $_.IsSystem })
if (-not $usbs) { Write-Host 'Nenhum pendrive encontrado.' -ForegroundColor Red; Pausar; exit 1 }
if ($Disco -lt 0) {
    Write-Host "`nPendrives conectados:" -ForegroundColor Cyan
    $usbs | ForEach-Object { '  {0})  {1}  ({2:N1} GB)' -f $_.Number, $_.FriendlyName, ($_.Size / 1GB) }
    $Disco = [int](Read-Host "`nNúmero do pendrive")
}
$alvo = $usbs | Where-Object Number -eq $Disco
if (-not $alvo) { Write-Host "O disco $Disco não é um pendrive USB." -ForegroundColor Red; Pausar; exit 1 }

Write-Host ("`nTUDO no pendrive '{0}' ({1:N1} GB) será apagado." -f $alvo.FriendlyName, ($alvo.Size / 1GB)) -ForegroundColor Yellow
if (-not $SemPerguntar -and (Read-Host 'Digite APAGAR para continuar').Trim() -ne 'APAGAR') { Write-Host 'Cancelado. Nada foi alterado.'; Pausar; exit 0 }

Write-Host '==> Formatando o pendrive' -ForegroundColor Cyan
# O diskpart é mais confiável que os cmdlets de disco com pendrives (o volume novo às vezes
# demora a aparecer para o Format-Volume). O Windows só formata FAT32 até 32 GB: a partição
# do sistema fica com 16 GB e o resto do pendrive vira uma partição exFAT.
if ($alvo.PartitionStyle -ne 'RAW') { $alvo | Clear-Disk -RemoveData -RemoveOEM -Confirm:$false }
Start-Sleep -Seconds 2
$tamanhoBootMB = [int][Math]::Min(16384, [Math]::Floor($alvo.Size / 1MB) - 64)
$comandos = @(
    "select disk $Disco", 'convert mbr noerr',
    "create partition primary size=$tamanhoBootMB", 'active',
    'format fs=fat32 quick label=CLONEOS', 'assign'
)
if (($alvo.Size / 1MB) - $tamanhoBootMB -gt 1024) {
    $comandos += 'create partition primary', 'format fs=exfat quick label=ARQUIVOS', 'assign'
}
$roteiro = Join-Path $env:TEMP 'clone-os-diskpart.txt'
Set-Content -Path $roteiro -Value $comandos -Encoding ASCII
diskpart /s $roteiro
if ($LASTEXITCODE -ne 0) { throw "O diskpart falhou (código $LASTEXITCODE)." }
Start-Sleep -Seconds 3
$letra = (Get-Partition -DiskNumber $Disco -PartitionNumber 1).DriveLetter
if (-not $letra) { throw 'O Windows não deu uma letra de unidade ao pendrive.' }
$destino = "${letra}:\"

Write-Host "==> Copiando o Clone OS para $destino (alguns minutos)" -ForegroundColor Cyan
$montada = Mount-DiskImage -ImagePath $Iso -PassThru
try {
    $origem = ($montada | Get-Volume).DriveLetter + ':\'
    robocopy $origem $destino /E /NFL /NDL /NJH /NP /R:2 /W:2 | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Falha ao copiar os arquivos da ISO (robocopy $LASTEXITCODE)." }
} finally {
    Dismount-DiskImage -ImagePath $Iso | Out-Null
}
Get-ChildItem $destino -Recurse -Force | ForEach-Object { $_.Attributes = 'Normal' }

Write-Host '==> Copiando o guia de instalação' -ForegroundColor Cyan
Copy-Item $guia -Destination $destino -Recurse -Force

$sfs = Get-Item (Join-Path $destino 'arch\x86_64\airootfs.sfs')
if (-not (Test-Path (Join-Path $destino 'EFI\BOOT\BOOTx64.EFI'))) { throw 'O arquivo de boot UEFI não foi copiado.' }
Write-Host ("`nPendrive pronto ({0}). Sistema: {1:N2} GB. Guia: {2}" -f $destino, ($sfs.Length / 1GB), (Join-Path $destino 'Clone OS - Instalacao')) -ForegroundColor Green
Write-Host 'Ejete o pendrive pelo Windows antes de tirar.'
Pausar
