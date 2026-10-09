# Clone-O.S
Estou desenvolvendo um O.S baseado em arch linux, com a interface do windows11, atualmente está na versão 0.3


Um Arch Linux com KDE Plasma 6 com a cara e o jeito do **Windows 11**, e o Claude integrado ao sistema,
feito para ser **instalado** em notebook ou pc de baixa configuração


- **Base:** perfil oficial `releng` do Arch (o mesmo da ISO oficial) + pacotes dos repositórios oficiais,
  com toda a segurança padrão do Arch (pacotes assinados, root bloqueado, sudo com senha, faillock).
- **Claude:** **Terminal Claude** (o Claude Code numa janela com o visual do Claude, ícone na área de
  trabalho e tecla Meta+C), o **app oficial do Claude para Linux** e o Claude Code no sistema todo.
- **Navegador:** **Brave** como padrão.
- **HD rápido:** sistema no começo do disco, zram, BFQ, pré-carregamento dos apps, menos escrita no disco.
- **Segurança no estilo do Windows 11:** boot assinado (systemd-boot + imagens unificadas do kernel
  assinadas com `sbctl`, pronto para a Inicialização Segura), LUKS2 com desbloqueio por TPM + PIN
  (como o BitLocker), AppArmor, `lockdown=integrity` e parâmetros de endurecimento do kernel, firewall
  ufw, antivírus ClamAV sob demanda, privacidade de rede (MAC por rede, IPv6 temporário, DNS sobre TLS),
  core dumps desligados, verificação de origem das atualizações do AUR, painel "Segurança" nas
  Configurações, reparo automático do disco no boot e kernel LTS de reserva.
- **Drivers do notebook pré-instalados:** vídeo (Intel, AMD, NVIDIA abertos, VA-API, troca de placa),
  áudio e microfone (PipeWire, SOF, ALSA), webcam (UVC, libcamera, app Câmera), teclado e touchpad
  (libinput, toque para clicar ligado), Bluetooth (BlueZ), Wi-Fi (firmware completo), leitor de digital.
- **Estilo Windows 11:** barra de tarefas embaixo com Iniciar/Pesquisa/Visão de tarefas/apps no centro,
  relógio com data, Lixeira na área de trabalho, app **Configurações** com as categorias do Windows 11,
  nomes dos apps iguais aos do Windows, atalhos (Win+I, Win+E, Win+Tab, Ctrl+Shift+Esc, Win+Shift+S;
  Win+C abre o Terminal Claude, no lugar do Copilot), boot com o logo do fabricante (Plymouth) e GRUB escondido.
- **Visual:** a mesma paleta do Clone OS (azul Arch + argila, tema escuro/claro) e os papéis de parede
  Bloom/Brisa, que acompanham o tema.
- **Leve:** só o essencial; nenhuma outra ferramenta de IA, nada rodando por trás sem necessidade.
  Sistema instalado bem abaixo do limite de 15 GB.

O guia de instalação para quem vai usar o notebook está em
[pendrive/Clone OS - Instalacao/README.md](pendrive/Clone%20OS%20-%20Instalacao/README.md)
(é a pasta que vai no pendrive).

## O que mudou

**0.3 (definitiva):** visual e atalhos do Windows 11 (tema global `org.cloneos.desktop`), app Configurações,
nomes de apps estilo Windows (`cloneos-nomes`), Plymouth + GRUB escondido, papéis de parede Bloom/Brisa,
fonte Inter, som (volume até 150%, sem reamostragem desnecessária), Reprodutor de Mídia (Haruna) e Paint
(KolourPaint), pesquisa `cl:` que abre o claude.ai, instalador que remove as ferramentas de resgate da ISO
e mostra o espaço ocupado, Thunderbird/Node.js/pandas fora da instalação padrão. Correções da 0.2: montagem
da partição EFI, navegador padrão (Brave) e ícone do app do Claude na área de trabalho.

| | 0.1 (alpha, VM) | 0.2 / 0.3 |
|---|---|---|
| Alvo | máquina virtual | notebook i5 8ª geração, 8 GB, HD 1 TB |
| Navegador | Chromium | Brave |
| Claude | Claude Code baixado no primeiro uso, Claude (Web) | Claude Code e app oficial do Claude já instalados, Terminal Claude |
| Disco | uma partição ext4 | EFI + sistema (80 GiB no começo do HD) + /home, LUKS2 opcional |
| Swap | nenhuma | zram 8 GiB (zstd) |
| Kernel | linux | linux + linux-lts (reserva) |
| Segurança | padrão do Arch | + ufw, sysctl, LUKS2, aviso de atualizações, `clone-update` |
| Pendrive | ISO gravada "crua" (Rufus) | FAT32 com o conteúdo da ISO + pasta com o guia |

## Como o Claude se integra

| Peça | O que faz |
|---|---|
| `clone-configuracoes` (Win+I) | Configurações no estilo do Windows 11; páginas próprias de Personalização, Privacidade, Claude e Atualizações, o resto abre o módulo do KDE. |
| `terminal-claude` (ícone, Win+C) | Abre o Claude Code em `~/Clone` numa janela do Alacritty com as cores do Claude. Ao sair do Claude, a janela vira um terminal comum. |
| `claude-desktop` | App oficial do Claude para Linux (o `.deb` da Anthropic, repacotado para o Arch). |
| `~/.claude/settings.json` | Pastas liberadas (`additionalDirectories`), modo de permissão e bloqueios, gravados pelo Clone Welcome. |
| `~/Clone/CLAUDE.md` | Explica ao Claude o sistema (`clonectl`, HD, segurança, ferramentas). |
| `clonectl` | Muda tema, cor, papel de parede e a barra de tarefas (centro/esquerda, ocultar); o Claude usa o mesmo comando. |
| `cloneos-seguranca` | Estado das proteções (JSON), cadastro das chaves da Inicialização Segura e TPM + PIN. |
| `clone-antivirus` | Verificação com o ClamAV sob demanda (também no botão direito do Explorador). |
| `clone-update` | Atualiza pacman + AUR (Brave, Claude, Claude Code) e roda o `arch-audit`. |

## Gerar a ISO

### No Windows (WSL)

1. Uma vez só, no PowerShell **como administrador**: `wsl --install -d archlinux` (reinicie se pedir).
2. Nesta pasta:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

A ISO sai em `out\cloneos-0.3-notebook.AAAAMMDD-x86_64.iso`. O build baixa uns 4 GB de pacotes e usa
uns 25 GB de espaço temporário no WSL.

### No Arch Linux

```bash
sudo ./build.sh
```

### Pacotes do AUR

Brave, app do Claude, Claude Code e yay não estão nos repositórios oficiais. As receitas ficam em `aur/`
(copiadas do AUR e revisadas: cada uma baixa o arquivo oficial da Brave, da Anthropic ou do yay e
confere o checksum). O `build.sh` compila num usuário sem privilégios (`cloneos-build`) e monta um
repositório local só durante o build. Para atualizar uma receita, copie a versão nova do AUR para
`aur/<pacote>/` e revise a diferença antes de gerar a ISO.

## Gravar o pendrive

No PowerShell **como administrador**:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\preparar-pendrive.ps1
```

O script formata o pendrive em FAT32 (16 GB), copia o conteúdo da ISO (boot UEFI), copia a pasta do
guia e deixa o resto do pendrive numa partição exFAT `ARQUIVOS`. Não precisa de Rufus.

## Estrutura

```
build.ps1 / build.sh        geram a ISO (releng oficial + camada do Clone OS + pacotes do AUR)
aur/                        receitas do AUR revisadas: brave-bin, claude-desktop, claude-code, yay-bin
pendrive/                   o que vai no pendrive além do sistema (guia de instalação)
profile/
  packages.cloneos          pacotes somados aos do releng
  packages.remove           pacotes do releng que saem
  profiledef.cloneos.sh     nome, versão, compressão e permissões da ISO
  airootfs/                 arquivos copiados para o sistema
    usr/local/bin/          clone-install, clone-configuracoes, terminal-claude, clone-update, clonectl, cloneos-*
    usr/share/cloneos/      logo, CLAUDE.md, Clone Welcome e Configurações (PySide6), visual do Terminal Claude
    usr/share/plasma/look-and-feel/org.cloneos.desktop/   barra e menu no estilo do Windows 11
    etc/                    HD (udev, sysctl, zram), segurança (sysctl, ufw), som (pipewire), KWin, Brave, SDDM
tools/
  build_assets.py           gera papéis de parede, ícones, esquemas de cor e o splash
  preparar-pendrive.ps1     grava o pendrive no Windows
  new-vm-*.ps1              criam uma VM para testar a ISO
backup/                     fontes da versão 0.1
```

## Desenvolvimento no Windows

```powershell
# regenerar arte e temas depois de mudar cores/logo
uv run --no-project --with pyside6 python tools/build_assets.py

# abrir o Clone Welcome ou as Configurações em modo demonstração (não executa nada no sistema)
uv run --no-project --with pyside6 python profile/airootfs/usr/share/cloneos/welcome/clone_welcome.py --live
uv run --no-project --with pyside6 python profile/airootfs/usr/share/cloneos/configuracoes/clone_configuracoes.py
```

## Limitações

- O instalador usa o disco inteiro (sem dual boot com o Windows).
- Boot pelo pendrive só em UEFI, com Secure Boot desligado.
- Sem hibernação (a swap é zram, na RAM); suspender funciona normalmente.
- O app do Claude para Linux ainda é beta na Anthropic (sem computer use e sem ditado).
- Idioma pt-BR fixo; fuso e teclado são escolhidos na instalação.
