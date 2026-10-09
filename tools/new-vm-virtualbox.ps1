# Cria e liga uma VM VirtualBox (UEFI) com a ISO mais recente de out\.
# Pré-requisito: VirtualBox 7 instalado (https://www.virtualbox.org/).
param(
    [string]$Iso = (Get-ChildItem (Join-Path $PSScriptRoot '..\out\*.iso') -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime | Select-Object -Last 1).FullName,
    [string]$Name = 'Clone OS',
    [int]$MemoryMB = 8192,
    [int]$Cpus = 4,
    [int]$DiskGB = 40
)
$ErrorActionPreference = 'Stop'
$vbox = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path $vbox)) { throw 'VirtualBox não encontrado. Instale em https://www.virtualbox.org/' }
if (-not $Iso) { throw 'Nenhuma ISO encontrada em out\. Rode build.ps1 antes.' }

function VBox { & $vbox @args; if ($LASTEXITCODE -ne 0) { throw "VBoxManage $($args -join ' ') falhou." } }

VBox createvm --name $Name --ostype ArchLinux_64 --register
$vmDir = Split-Path ((& $vbox showvminfo $Name --machinereadable | Select-String '^CfgFile=').Line.Split('=', 2)[1].Trim('"'))
$disk = Join-Path $vmDir "$Name.vdi"

VBox modifyvm $Name --memory $MemoryMB --cpus $Cpus --firmware efi --graphicscontroller vmsvga --vram 128 `
    --nic1 nat --clipboard-mode bidirectional --mouse usbtablet --usb-xhci on
VBox storagectl $Name --name SATA --add sata --controller IntelAhci --portcount 2
VBox createmedium disk --filename $disk --size ($DiskGB * 1024) --format VDI
VBox storageattach $Name --storagectl SATA --port 0 --device 0 --type hdd --medium $disk
VBox storageattach $Name --storagectl SATA --port 1 --device 0 --type dvddrive --medium $Iso
VBox startvm $Name
Write-Host "VM '$Name' criada com $Cpus CPUs, $($MemoryMB / 1024) GB de RAM e disco de $DiskGB GB."
