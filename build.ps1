# Gera a ISO do Clone OS no Windows, usando o Arch Linux do WSL.
# Pré-requisito (uma vez, como administrador):  wsl --install -d archlinux
$ErrorActionPreference = 'Stop'
$env:WSL_UTF8 = '1'
$distro = 'archlinux'

$installed = (wsl.exe -l -q 2>$null) -replace "`0", '' | ForEach-Object { $_.Trim() } | Where-Object { $_ -eq $distro }
if (-not $installed) {
    Write-Host 'O Arch Linux do WSL nao esta instalado. Abra o PowerShell como administrador e rode:' -ForegroundColor Yellow
    Write-Host '    wsl --install -d archlinux'
    Write-Host 'Reinicie o computador se for pedido e rode este script de novo.'
    exit 1
}

$repo = (wsl.exe -d $distro -u root -- wslpath -a ($PSScriptRoot -replace '\\', '/')).Trim()
Write-Host "==> Projeto no WSL: $repo" -ForegroundColor Cyan

Write-Host '==> Atualizando o Arch do WSL e instalando o archiso' -ForegroundColor Cyan
wsl.exe -d $distro -u root -- bash -c 'pacman-key --init >/dev/null 2>&1; pacman-key --populate archlinux >/dev/null 2>&1; pacman -Sy --needed --noconfirm archlinux-keyring && pacman -Su --needed --noconfirm archiso'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar o Arch do WSL.' }

wsl.exe -d $distro -u root -- bash "$repo/build.sh"
if ($LASTEXITCODE -ne 0) { throw 'O build da ISO falhou (veja as mensagens acima).' }

Get-ChildItem (Join-Path $PSScriptRoot 'out\*.iso') | Sort-Object LastWriteTime | Select-Object -Last 1 |
    ForEach-Object { Write-Host "`nISO pronta: $($_.FullName) ($([math]::Round($_.Length / 1GB, 2)) GB)" -ForegroundColor Green }
