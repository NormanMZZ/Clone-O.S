#Requires -RunAsAdministrator
# Cria e liga uma VM Hyper-V (geração 2, UEFI) com a ISO mais recente de out\.
# Pré-requisito: recurso Hyper-V ativado (Windows 11 Pro).
param(
    [string]$Iso = (Get-ChildItem (Join-Path $PSScriptRoot '..\out\*.iso') -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime | Select-Object -Last 1).FullName,
    [string]$Name = 'Clone OS',
    [int64]$MemoryGB = 8,
    [int]$Cpus = 4,
    [int64]$DiskGB = 40
)
$ErrorActionPreference = 'Stop'
if (-not $Iso) { throw 'Nenhuma ISO encontrada em out\. Rode build.ps1 antes.' }
if (Get-VM -Name $Name -ErrorAction SilentlyContinue) { throw "Já existe uma VM chamada '$Name'." }

$vhd = Join-Path (Get-VMHost).VirtualHardDiskPath "$Name.vhdx"
New-VM -Name $Name -Generation 2 -MemoryStartupBytes ($MemoryGB * 1GB) -NewVHDPath $vhd `
    -NewVHDSizeBytes ($DiskGB * 1GB) -SwitchName 'Default Switch' | Out-Null
Set-VMMemory -VMName $Name -DynamicMemoryEnabled $false
Set-VMProcessor -VMName $Name -Count $Cpus
Set-VM -Name $Name -AutomaticCheckpointsEnabled $false
Add-VMDvdDrive -VMName $Name -Path $Iso
# A ISO do Clone OS não é assinada para Secure Boot.
Set-VMFirmware -VMName $Name -EnableSecureBoot Off -FirstBootDevice (Get-VMDvdDrive -VMName $Name)

Start-VM -Name $Name
vmconnect.exe localhost $Name
Write-Host "VM '$Name' criada com $Cpus CPUs, $MemoryGB GB de RAM e disco de $DiskGB GB."
