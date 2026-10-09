# Clone OS 0.3.5 (notebook): instalação passo a passo

O Clone OS é um Arch Linux com a cara e o jeito do **Windows 11**: barra de tarefas embaixo com os
ícones no centro, menu Iniciar, Configurações, Explorador de Arquivos e os mesmos atalhos de teclado.
O **Claude** vem integrado ao sistema todo, e a segurança segue a do Windows 11: Inicialização Segura,
disco criptografado com TPM + PIN (como o BitLocker), firewall e antivírus.
Ele foi ajustado para este notebook: **Lenovo IdeaPad 330S-15IKB (modelo 81JN)**, Intel Core i5-8250U
(8ª geração), 8 GB de RAM DDR4 e HD de 1 TB. Todos os drivers dele já vêm instalados.

A instalação **apaga o HD inteiro, inclusive o Windows 10**, e coloca o Clone OS no lugar.
Leva uns 40 minutos. Deixe este guia aberto no celular ou em outro computador enquanto instala.

**Você vai precisar de:**

- este pendrive;
- o carregador do notebook ligado na tomada (deixe ligado até o fim);
- a senha do Wi-Fi (só depois de instalar, para entrar na conta Claude);
- uma assinatura Claude (Pro, Max, Team ou Enterprise) para usar o Claude Code e o app.

---

## Passo 1: ajustar a BIOS da Lenovo

Entre na BIOS de **um** destes jeitos:

- **Pelo Windows 10 (o mais fácil):** Configurações → Atualização e segurança → Recuperação →
  Inicialização avançada → **Reiniciar agora** → Solucionar problemas → Opções avançadas →
  **Configurações de Firmware UEFI** → Reiniciar.
- **Pela tecla:** com o notebook desligado, ligue apertando várias vezes **F2** (em alguns modelos,
  **Fn + F2**).
- **Pelo botão Novo** (IdeaPad, Yoga, série V): um furinho na lateral, perto da entrada do
  carregador, às vezes com o desenho de uma setinha. Com o notebook desligado, aperte com a ponta
  de um clipe e escolha **BIOS Setup**.
- **ThinkPad:** ligue apertando **Enter** e depois **F1**.

Na BIOS, use as setas para trocar de aba e Enter para mudar uma opção:

| Aba | Opção | Deixe em | Por quê |
|---|---|---|---|
| **Security** | **Secure Boot** | **Disabled** (por enquanto) | Ela volta a ser ligada depois de instalar, já com as chaves do Clone OS (Passo 6). |
| **Security** | **Security Chip** / **Intel PTT** (se existir) | **Enabled** | É o chip TPM, usado no desbloqueio do disco com PIN. |
| **Configuration** | **SATA Controller Mode** / **Storage** | **AHCI** (se estiver "Intel RST" ou "RAID") | Com RST/RAID o Linux não enxerga o HD. A Lenovo pode avisar que o Windows deixa de iniciar: pode confirmar, ele vai ser apagado. |
| **Boot** | **Boot Mode** | **UEFI** (não "Legacy Support") | O pendrive foi preparado para UEFI. |
| **Boot** | **Fast Boot** (se existir) | **Disabled** | Ajuda o notebook a enxergar o pendrive. |
| **Configuration** | **Hotkey Mode** (opcional) | **Disabled** | Para usar F2, F12 etc. sem segurar o Fn. |

Salve e saia: **F10 → Yes**.

---

## Passo 2: iniciar pelo pendrive

1. Com o notebook desligado, coloque o pendrive (de preferência numa porta USB azul, 3.0).
2. Ligue apertando várias vezes **F12** (ou **Fn + F12**). Pelo botão Novo: **Boot Menu**.
3. Escolha **`EFI USB Device`** ou **`UEFI: SanDisk Cruzer Blade`**.
4. Aparece o menu **Clone OS (live)**. Tecle **Enter** (ou espere 15 segundos).
5. Em 1 a 3 minutos aparece a área de trabalho, igual à do sistema instalado, e o
   **Clone Welcome** abre sozinho.

Este é o **modo live**: o sistema roda do pendrive e nada é gravado no HD. Aproveite para conferir
se o touchpad, o teclado, o som e o Wi-Fi (ícone de rede perto do relógio) funcionam.
No modo live tudo é mais lento que no sistema instalado, porque roda do pendrive.

---

## Passo 3: instalar (é aqui que o Windows 10 é apagado)

1. Dê dois cliques no ícone **Instalar Clone OS** da área de trabalho
   (ou clique em **Instalar Clone OS** no Clone Welcome). Abre uma janela de terminal.
2. Responda às perguntas. O número entre colchetes, como `[1]`, é a resposta padrão:
   é só teclar **Enter** para aceitar.

| Pergunta | O que responder |
|---|---|
| **Em qual disco instalar?** | O HD de 1 TB: aparece com uns `931,5G` e o tipo `HD`. O pendrive não aparece na lista. Normalmente o padrão já é o HD: tecle **Enter**. |
| **Seu nome** | Seu nome, como quiser que apareça (ex.: `Gabriel`). |
| **Nome de usuário** | Minúsculas, sem espaço nem acento (ex.: `gabriel`). |
| **Senha** (duas vezes) | A senha de login. **Nada aparece enquanto você digita, é normal.** |
| **Nome do computador** | **Enter** (fica `clone-notebook`). |
| **Fuso horário** | **Enter** (fica `America/Sao_Paulo`). |
| **Teclado** | `1` se o teclado do notebook tem a tecla **Ç** (ABNT2, o padrão no Brasil). |
| **Criptografar o disco?** | **Enter** (sim). Se o notebook for roubado, ninguém lê seus arquivos. |
| **Usar a mesma senha da sua conta?** | **Enter** (sim). A senha do disco precisa ter **8 caracteres ou mais, sem acento nem ç**; se a da conta não servir, o instalador pede outra só para o disco. |
| **Digite APAGAR para continuar** | Confira o resumo e digite `APAGAR` (em maiúsculas). |

3. Espere de 15 a 30 minutos. O instalador mostra cada etapa: particionar, criptografar e formatar;
   **copiar o sistema** (a barra mostra a porcentagem); criar as chaves de segurança e preparar o boot.
4. Quando aparecer **Clone OS instalado!** (com o espaço que o sistema ocupou), digite `s` e
   **Enter**. Tire o pendrive assim que a tela apagar.

> **Importante:** guarde bem a senha do disco. Se esquecê-la, **não existe forma de recuperar
> os arquivos**: essa é justamente a proteção. Ela também é a chave de recuperação do TPM (Passo 6).

---

## Passo 4: primeiro uso

1. Ao ligar aparece o **logo da Lenovo** com uma animação e o **Clone OS** embaixo, como no Windows.
2. Na mesma tela aparece um campo de senha com a frase *Please enter passphrase for disk CloneOS
   (root)*: digite a **senha do disco** e tecle **Enter** (nada aparece enquanto digita).
3. Na tela de login, digite a sua senha.
4. A área de trabalho abre com o **Clone Welcome**:
   1. **Bem-vindo**: clique em **Começar**.
   2. **Conectar o Claude**: primeiro conecte o Wi-Fi (ícone perto do relógio). Depois:
      - **Entrar com Claude** abre o **Terminal Claude**. Clique em **Entrar com o Claude**: abre
        uma janelinha de terminal e o Brave na página de login da **conta Claude (assinatura)**.
        Entre e clique em **Autorizar**. Em alguns segundos o Terminal Claude mostra **Conectado**.
      - **Abrir o app** abre o **app do Claude**. Clique em entrar e use a mesma conta.
   3. **Permissões**: deixe o padrão (Documentos e Downloads, "Perguntar antes de agir").
   4. **Aparência**: tema, cor de destaque e papel de parede.
   5. **Concluir**.

Se aparecer uma janela da **Carteira do KDE** pedindo para criar uma carteira, escolha
**Blowfish** e use **a mesma senha do login**: assim ela abre sozinha nos próximos logins e
guarda com segurança as senhas do Brave e do app do Claude.

---

## Passo 5: conferir o hardware (5 minutos)

Os drivers do notebook já vêm instalados. Confira cada item:

| O que testar | Como |
|---|---|
| **Vídeo** | A tela abre na resolução certa e o brilho muda nas teclas de brilho (F11/F12 ou Fn + F11/F12). |
| **Som** | Ícone de som perto do relógio → aumente o volume e toque um vídeo no Brave. Fone de ouvido: ao conectar, o som muda sozinho. |
| **Microfone** | Configurações → Sistema → **Som** → aba de entrada: fale e veja a barra se mexer. |
| **Webcam** | Abra o app **Câmera** no menu Iniciar. A luz da câmera acende e a imagem aparece. |
| **Teclado** | Digite `ç`, `á`, `ã` e teste as teclas de volume, brilho e mudo. |
| **Touchpad** | Mover, **tocar para clicar** (já vem ligado), dois dedos para rolar, dois dedos tocando para o botão direito. Ajustes: Configurações → Bluetooth e dispositivos → **Touchpad**. |
| **Bluetooth** | Ícone de Bluetooth perto do relógio → **Adicionar dispositivo** e pareie um fone ou caixa de som. |
| **Wi-Fi** | Ícone de rede perto do relógio. |

Se algum item não funcionar, abra o **Terminal Claude** e peça: *"o microfone não funciona, me ajuda
a descobrir por quê"*. O Claude conhece o sistema e mostra antes o que vai fazer.

---

## Passo 6: ligar a segurança do Windows 11 (recomendado, 10 minutos)

Abra **Configurações → Privacidade e segurança**. O painel mostra cada proteção e o que falta ligar.

**Inicialização Segura (Secure Boot).** Garante que o notebook só inicie o Clone OS original:
ninguém consegue trocar o sistema por uma versão adulterada para roubar a sua senha.

1. Reinicie, aperte **F2** e vá em **Security → Secure Boot → Reset to Setup Mode** (ou
   **Clear All Secure Boot Keys**) → **Yes**. Deixe o Secure Boot ainda em **Disabled**. **F10 → Yes**.
2. No Clone OS: **Configurações → Privacidade e segurança → Inicialização Segura → Ativar**.
   Digite a sua senha. As chaves do Clone OS são cadastradas no notebook.
3. Reinicie, aperte **F2**, vá em **Security → Secure Boot → Enabled**. **F10 → Yes**.
4. O painel passa a mostrar **Inicialização Segura: Ativado**.

**Desbloqueio com TPM + PIN (como o BitLocker).** Em vez da senha longa do disco, você digita um
PIN curto ao ligar. O disco só abre neste notebook, com o sistema original, e com o PIN.

1. Ative depois da Inicialização Segura.
2. **Configurações → Privacidade e segurança → Desbloqueio com TPM + PIN → Ativar**.
3. Digite a sua senha de login (sudo), depois a **senha do disco** e escolha um **PIN** (4 dígitos
   ou mais), duas vezes.
4. No próximo boot, a tela pede o **PIN** (*Please enter LUKS2 token PIN*). A senha do disco continua
   valendo como chave de recuperação.

---

## Igual ao Windows 11

| No Windows 11 | No Clone OS |
|---|---|
| Barra de tarefas embaixo, ícones no centro | Igual. Para deixar à esquerda: **Configurações → Personalização → Barra de tarefas** |
| Botão Iniciar / tecla Windows | Menu Iniciar com os apps fixados, a lista de todos os apps e a busca |
| Pesquisa | Ícone da lupa na barra (ou comece a digitar com o Iniciar aberto) |
| Visão de tarefas (Windows + Tab) | Mostra todas as janelas e áreas de trabalho |
| Configurações (Windows + I) | **Configurações**, com as mesmas categorias do Windows 11, mais a página do Claude |
| Segurança do Windows | **Configurações → Privacidade e segurança** |
| Windows Defender | **Antivírus** (botão direito num arquivo → **Verificar vírus**) |
| BitLocker | Disco criptografado (LUKS2) com **TPM + PIN** |
| Windows Update | **Configurações → Atualizações** |
| Explorador de Arquivos (Windows + E) | Explorador de Arquivos |
| Copilot (Windows + C) | **Terminal Claude** |
| Gerenciador de Tarefas (Ctrl + Shift + Esc) | Gerenciador de Tarefas |
| Ferramenta de Captura (Windows + Shift + S) | Ferramenta de Captura |
| Câmera, Fotos, Paint, Bloco de Notas, Calculadora, Reprodutor de Mídia | Iguais, com os mesmos nomes |
| Área de transferência (Windows + V), emojis (Windows + .) | Iguais |
| Bloquear (Windows + L), mostrar a área de trabalho (Windows + D) | Iguais |
| Encaixar janelas (Windows + setas) | Igual; arrastar a janela para a borda também encaixa |
| Lixeira na área de trabalho | Igual |

### Programas que vêm instalados

| Programa | Para quê |
|---|---|
| **Terminal Claude** | O Claude Code numa janela no estilo do app do Claude, toda em português. Peça: organizar arquivos, montar planilhas, ajustar o sistema. |
| **Claude** (app) | O app oficial do Claude para Linux: conversas, projetos e Claude Code. |
| **Brave** | Navegador padrão, com bloqueio de anúncios e rastreadores. |
| **Explorador de Arquivos, Bloco de Notas, Calculadora, Câmera, Fotos, Paint, Reprodutor de Mídia, Ferramenta de Captura, Leitor de PDF** | Os básicos do Windows, com os mesmos nomes. |
| **LibreOffice** (Writer, Calc, Impress) | Documentos, planilhas e apresentações, que abrem arquivos do Word, Excel e PowerPoint. |

Quer mais programas? **Configurações → Aplicativos → Instalar mais programas** tem os mais
procurados (Thunderbird, GIMP, VLC, OBS Studio, Telegram, Discord, Kdenlive, Krita), todos dos
repositórios oficiais do Arch. Ou peça ao Claude ("instala o GIMP pra mim").

### O Claude em todo lugar

- **Windows + C** abre o Terminal Claude de qualquer lugar.
- Na pesquisa do Iniciar, digite **`cl:` e a pergunta** (ex.: `cl: como juntar dois PDFs`):
  o Brave abre o claude.ai já com a pergunta.
- **Configurações → Claude** mostra se você está conectado e as permissões.
- O Claude só enxerga a pasta `~/Clone` e as pastas liberadas no Clone Welcome, e pede
  confirmação antes de mudar qualquer coisa.

### Usando o Terminal Claude

- Escreva na caixa de baixo e tecle **Enter** (Shift+Enter quebra a linha). O botão redondo
  vira **■ Parar** enquanto o Claude responde (ou tecle **Esc**).
- **Modelo** (botão embaixo, à esquerda): **Opus** (recomendado), **Sonnet** (mais rápido),
  **Haiku** (o mais leve) ou **Fable** (o mais capaz, gasta mais da sua cota). Vale a partir da
  próxima mensagem, sem perder a conversa.
- **Grau de esforço** (botão com as barrinhas): de **Baixo** (respostas rápidas) a **Máximo**
  (pensa o máximo possível). **Alto** é o padrão.
- **Roda de contexto** (ao lado do botão de enviar): mostra quanto da memória da conversa já foi
  usado. Verde até 60%, amarela até 85% e vermelha depois disso. Quando enche, o Claude resume a
  conversa sozinho; para um assunto novo, clique em **+ Nova conversa**.
- **Raciocínio**: clique em "Raciocínio" para ver como o Claude pensou. Ele responde e pensa em português.
- Quando o Claude quer rodar um comando ou mudar um arquivo, aparece um cartão com **Permitir**,
  **Permitir sempre nesta conversa** e **Negar**.
- As conversas ficam na barra da esquerda (botão direito para renomear ou apagar).
- Prefere o terminal? Menu **•••** → **Abrir no modo texto**.

---

## Drivers que vêm instalados

### No IdeaPad 330S-15IKB (81JN)

| Peça | Driver | Observação |
|---|---|---|
| Intel UHD 620 | i915, Mesa, Vulkan, VA-API | Tela e vídeos com aceleração |
| AMD Radeon 540 (se o seu tiver) | amdgpu, Vulkan, switcheroo | Fica desligada até um programa pedir (economiza bateria). Botão direito no programa → **Executar com a placa dedicada** |
| Áudio Realtek e microfone | snd_hda_intel, PipeWire, SOF | O "Dolby Audio" é um programa do Windows; o som funciona normalmente |
| Wi-Fi + Bluetooth 4.1 (Realtek RTL8821CE, Intel ou Qualcomm, conforme a unidade) | rtw88 / iwlwifi / ath10k, btusb | Veja "Wi-Fi cai de vez em quando" em Problemas comuns |
| Touchpad ELAN | i2c-hid, libinput | Toque para clicar já ligado |
| Teclado e teclas Fn | ideapad_laptop | Brilho, volume, modo avião e **modo de conservação da bateria** (Configurações → Sistema → Energia e bateria) |
| Webcam HD | uvcvideo | App **Câmera** |
| Leitor de cartão SD | rtsx_pci | |

### Em geral

| Parte | O que vem |
|---|---|
| Vídeo | Intel UHD 620 (i915, Mesa, Vulkan, aceleração de vídeo VA-API); AMD Radeon e NVIDIA (drivers abertos), se o modelo tiver placa dedicada, com troca automática de placa |
| Áudio e microfone | PipeWire, ALSA, firmware Intel SOF e perfis de áudio de notebook; fones Bluetooth com codecs de alta qualidade (AAC, LDAC) |
| Webcam | UVC (todas as webcams USB/integradas comuns) e câmeras MIPI (libcamera) |
| Teclado e touchpad | libinput (touchpads Synaptics, Elan, I2C-HID e PS/2), teclas especiais da Lenovo (ideapad/thinkpad) |
| Bluetooth | BlueZ, com firmware Intel, Realtek, Qualcomm e MediaTek |
| Wi-Fi | Intel, Realtek, Qualcomm Atheros, MediaTek e Broadcom (firmware completo do Arch) |
| Outros | Leitor de digital (se tiver), leitor de cartão SD, sensores, Thunderbolt, microcódigo Intel |

---

## Leve de propósito

Com 8 GB de RAM, o Clone OS só deixa rodando o necessário: nenhuma ferramenta de IA além do
Claude (o assistente de IA do Brave vem desligado), antivírus sem processo residente, sem indexador
de arquivos, sem loja rodando por trás e sem serviço de modem quando o notebook não tem 4G. O Brave
fecha de verdade quando você fecha a janela. O sistema instalado ocupa **bem menos de 15 GB** do HD.

## Como o sistema foi ajustado para o HD

- **Sistema no começo do disco** (partição de 80 GB na região mais rápida do HD); seus arquivos no resto.
- **Swap na memória (zram)**: quando a RAM aperta, o sistema comprime dados na própria RAM.
- **Escalonador BFQ**: prioridade para o programa que você está usando.
- **Pré-carregamento** do Brave e do Claude logo depois do login, só quando o HD está livre.
- **Menos escrita no disco** (cache do Brave na memória, diário do sistema limitado).
- **Reparo automático:** se o notebook desligar no meio (bateria acabou), o disco é conferido e
  consertado sozinho no próximo boot, como no Windows.

## Segurança: o que já vem ligado

- **Pacotes assinados** pelo Arch; Brave, app do Claude e Claude Code vêm dos sites oficiais e, nas
  atualizações, o sistema confere se a origem continua sendo o site oficial antes de instalar.
- **Disco criptografado (LUKS2)** e **boot assinado** (pronto para a Inicialização Segura, Passo 6).
- **Firewall ligado** (bloqueia conexões de fora); nenhum servidor aberto (SSH desligado, LLMNR e mDNS
  desligados).
- **AppArmor** (controle do que cada programa pode fazer) e **lockdown do kernel** (nem programas
  com senha de administrador alteram o kernel em execução), mais as proteções da wiki do Arch.
- **Privacidade na rede:** endereço Wi-Fi (MAC) diferente para cada rede, IPv6 temporário e DNS
  criptografado quando a rede suporta.
- **Administrador protegido:** a conta root fica bloqueada e o `sudo` pede a sua senha; depois de
  3 senhas erradas, o login trava por 10 minutos.
- **Antivírus** (ClamAV) com as vacinas atualizadas uma vez por dia; verifique arquivos pelo botão
  direito → **Verificar vírus**, ou em Configurações → Privacidade e segurança.
- **Aviso de atualizações** todos os dias. Atualize pelo menos uma vez por semana.

---

## Problemas comuns

**O pendrive não aparece no menu do F12.**
Confira se o Secure Boot está **Disabled** e o Boot Mode em **UEFI**. Tente outra porta USB.

**O menu "Clone OS (live)" aparece, mas a tela fica preta.**
Espere 3 minutos. Se continuar preta, reinicie; no menu do Clone OS aperte `e`, vá até o fim da linha,
acrescente ` nomodeset` e tecle **Enter**.

**O instalador diz "nenhum disco encontrado".**
O SATA da BIOS está em Intel RST/RAID. Mude para **AHCI** (Passo 1).

**Depois de instalar, o notebook volta para o "Windows Boot Manager" ou diz "No bootable device".**
F2 → aba **Boot** → coloque **Linux Boot Manager** (ou **CloneOS**) em primeiro lugar. **F10**.

**Depois de ligar o Secure Boot, o notebook não inicia.**
F2 → Security → Secure Boot → **Disabled**, F10. O Clone OS volta a iniciar; refaça o Passo 6.

**O sistema não inicia depois de uma atualização.**
Ligue segurando a **barra de espaço** logo depois do logo da Lenovo: aparece o menu de boot.
Escolha a opção com **linux-lts** (o kernel de reserva) e rode a atualização de novo.

**Wi-Fi cai de vez em quando (chip Realtek RTL8821CE).**
Esse chip às vezes se perde com a economia de energia ligada. Abra o **Terminal Claude** e peça:
*"meu Wi-Fi Realtek 8821CE cai, desliga a economia de energia dele"*. O Claude mostra o ajuste
(uma linha em `/etc/modprobe.d`) e pede sua confirmação antes.

**Esqueci o PIN do TPM.**
Digite a **senha do disco** no campo do PIN: ela também abre o disco. Depois de vários PINs errados,
o chip TPM se bloqueia por um tempo (proteção contra quem tenta adivinhar) e a tela passa a pedir
direto a senha do disco. Para trocar o PIN: Configurações → Privacidade e segurança → Desbloqueio
com TPM + PIN → **Desativar**, e depois **Ativar** de novo com o PIN novo.

**Esqueci a senha do disco (e não tenho o PIN).**
Não há como recuperar: é preciso reinstalar.

---

## Detalhes técnicos

| Partição | Tamanho | Sistema de arquivos | Montada em |
|---|---|---|---|
| EFI | 1 GiB | FAT32 | `/efi` (carregador systemd-boot e imagens de boot assinadas) |
| CloneOS | 80 GiB, no começo do HD | ext4 dentro de LUKS2 | `/` (inclui `/boot`) |
| Home | o resto (~850 GiB) | ext4 dentro de LUKS2 | `/home` (abre com uma chave guardada no sistema criptografado) |
| swap | 8 GiB na RAM | zram (zstd) | – |

- Base: perfil oficial `releng` do Arch Linux, KDE Plasma 6 (Wayland, com sessão X11 de reserva),
  tema global `org.cloneos.desktop` (barra e menu no estilo do Windows 11).
- Boot: systemd-boot + imagens unificadas do kernel assinadas com `sbctl` (menu escondido, sem edição
  da linha de comando); Plymouth com o logo do fabricante; kernels `linux` e `linux-lts`.
- Segurança: `cloneos-seguranca` (Inicialização Segura e TPM + PIN), `clone-antivirus`, AppArmor,
  `lockdown=integrity`, `/etc/sysctl.d/80-cloneos-seguranca.conf`, ufw.
- Registro da instalação: `/var/log/clone-install.log`.
- O pendrive continua sendo um pendrive comum: esta pasta e a partição **ARQUIVOS** podem
  guardar o que você quiser. Não apague as pastas `arch`, `boot`, `EFI` e `loader`, que são
  o Clone OS.
