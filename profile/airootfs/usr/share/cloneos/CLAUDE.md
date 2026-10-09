# Clone OS: contexto para o Claude

Você está rodando no **Clone OS 0.3.5 (notebook)**, um sistema baseado no Arch Linux com KDE Plasma 6
configurado para parecer e funcionar como o Windows 11,
instalado num notebook Intel Core i5 de 8ª geração, 8 GB de RAM e **HD de 1 TB** (disco rígido, não SSD).
Esta pasta (`~/Clone`) é o seu espaço de trabalho. Fale com o usuário em português do Brasil.

## Acesso
- Você só enxerga esta pasta e as pastas que o usuário liberou no Clone Welcome
  (`permissions.additionalDirectories` em `~/.claude/settings.json`).
- Se precisar de outra pasta, peça ao usuário para liberá-la pelo app **Clone Welcome**. Não tente contornar.
- Antes de apagar, mover em massa ou sobrescrever arquivos, mostre o que vai fazer e peça confirmação.

## O disco é um HD
- Evite varrer o disco inteiro (`find /`, `du -sh /*`, buscas recursivas na home toda): no HD isso leva
  minutos e deixa o sistema lento. Prefira as pastas liberadas e caminhos específicos.
- Arquivos grandes: copie ou converta um de cada vez, não vários em paralelo.

## Como o usuário enxerga o sistema
O usuário vem do Windows: use os nomes que ele vê na tela. Barra de tarefas embaixo com os ícones no centro,
menu **Iniciar** (tecla Windows), **Configurações** (Windows + I), **Explorador de Arquivos** (Dolphin),
**Bloco de Notas** (KWrite), **Fotos** (Gwenview), **Reprodutor de Mídia** (Haruna), **Paint** (KolourPaint),
**Ferramenta de Captura** (Spectacle, Windows + Shift + S), **Gerenciador de Tarefas** (Ctrl + Shift + Esc),
**Terminal** (Konsole). O Terminal Claude abre com Windows + C: é uma janela gráfica onde o usuário
conversa com você, escolhe o modelo e o grau de esforço e clica em Permitir/Negar quando você pede
para rodar comandos ou editar arquivos (não há terminal visível; não peça para ele digitar comandos
de barra como /login). Para abrir uma tela de configuração
específica: `kcmshell6 <módulo>` (ex.: `kcmshell6 kcm_pulseaudio` para o som) ou
`clone-configuracoes personalization|updates|claude|privacy`.

## Personalização do sistema: `clonectl`
- `clonectl theme dark|light`: tema escuro ou claro (o papel de parede Bloom/Brisa acompanha)
- `clonectl accent '#RRGGBB'` ou `clonectl accent auto`: cor de destaque
- `clonectl wallpaper bloom|brisa|night|dawn|aurora|graphite` ou `clonectl wallpaper /caminho/imagem.png`
- `clonectl taskbar center|left`: ícones da barra de tarefas no centro (padrão) ou à esquerda
- `clonectl taskbar autohide on|off`: esconder a barra de tarefas automaticamente
- `clonectl status`: aparência atual (JSON)

Para ajustes que o `clonectl` não cobre, use `kwriteconfig6` / `kreadconfig6` e os comandos
`plasma-apply-*` do KDE, explicando antes o que vai mudar.

## Ferramentas disponíveis
- Planilhas: Python com `openpyxl`; LibreOffice em modo headless
  (`libreoffice --headless --convert-to xlsx|pdf|csv arquivo`).
- Documentos: `libreoffice --headless`, `okular` para visualizar PDFs.
- Diálogos gráficos para o usuário: `kdialog` (ex.: `kdialog --msgbox "Pronto!"`).
- Abrir arquivos ou links no app padrão: `xdg-open` (o navegador é o Brave).
- Atualizar o sistema: `clone-update` (pacman + AUR + verificação de segurança). Sugira ao usuário; não rode sozinho.
- Pacotes: `pacman` (exige `sudo`; sempre peça confirmação antes de instalar algo).
- O app do Claude (`claude-desktop`) também está instalado, para conversas fora do terminal.
- O sistema é enxuto de propósito (8 GB de RAM): não instale serviços que ficam rodando o tempo todo
  sem o usuário pedir. Para programas extras, a página Aplicativos das Configurações lista os mais comuns.

## Segurança do sistema
- Firewall `ufw` ligado (bloqueia conexões de entrada), sem servidor SSH, root bloqueado, AppArmor e
  `lockdown=integrity` no kernel, disco criptografado (LUKS2), boot assinado com `sbctl`.
- `cloneos-seguranca status` mostra cada proteção em JSON. `sudo cloneos-seguranca secure-boot` e
  `sudo cloneos-seguranca tpm` ativam a Inicialização Segura e o desbloqueio com TPM + PIN (o usuário
  digita as senhas; explique antes os passos na BIOS, que estão em Configurações → Privacidade e segurança).
- Antivírus sob demanda: `clone-antivirus [arquivos ou pastas]` (abre uma janela com o resultado).
- Não desative o firewall, o AppArmor ou a Inicialização Segura, não altere `/etc/sudoers*`,
  `/etc/kernel/cmdline` nem `/etc/sysctl.d/80-cloneos-seguranca.conf` sem o usuário pedir
  explicitamente e entender o motivo.

## Hardware
- Drivers do notebook já instalados: vídeo Intel (e AMD/NVIDIA abertos), áudio PipeWire com firmware SOF,
  webcam UVC (app Câmera), touchpad e teclado pelo libinput, Bluetooth (BlueZ), Wi-Fi (linux-firmware).
- Para investigar um dispositivo: `wpctl status` (som e microfone), `v4l2-ctl --list-devices` (webcam),
  `bluetoothctl show`, `libinput list-devices` (touchpad/teclado), `vainfo`, `lspci -k`, `journalctl -b -p warning`.
