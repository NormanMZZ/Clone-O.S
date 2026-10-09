#!/usr/bin/env bash
# Gera a ISO do Clone OS (edição notebook). Precisa rodar no Arch Linux (máquina, VM ou WSL).
#
# O perfil é montado em cima do "releng", o perfil oficial da ISO do Arch
# instalado pelo pacote archiso: assim o boot (BIOS e UEFI) é sempre o da
# versão do archiso instalada, e o Clone OS só acrescenta o que é dele.
#
# Brave, o app do Claude, o Claude Code e o yay não estão nos repositórios
# oficiais. As receitas do AUR ficam em aur/ (revisadas; cada uma baixa o
# arquivo oficial da Brave, da Anthropic ou do yay e confere o checksum) e
# são compiladas aqui, num usuário sem privilégios, para um repositório local
# que só existe durante o build.
#
#   ./build.sh                          ISO em ./out
#   CLONEOS_OUT=/outro/lugar ./build.sh
set -euo pipefail

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
work="${CLONEOS_WORK:-/var/tmp/cloneos-build}"
cache="${CLONEOS_CACHE:-/var/cache/cloneos}"
out="${CLONEOS_OUT:-$here/out}"
releng=/usr/share/archiso/configs/releng

if (( EUID != 0 )); then
    exec sudo --preserve-env=CLONEOS_WORK,CLONEOS_CACHE,CLONEOS_OUT "$0" "$@"
fi

[[ -f /etc/arch-release ]] || { echo "Este build precisa rodar no Arch Linux." >&2; exit 1; }

echo "==> Instalando as ferramentas de build"
pacman -Syu --needed --noconfirm archiso base-devel git

echo "==> Preparando o perfil em $work"
profile="$work/profile"
repo="$work/repo"
rm -rf -- "$work"
mkdir -p -- "$profile" "$repo" "$out"
cp -a -- "$releng/." "$profile/"

# Partes do releng pensadas para a ISO de instalação em modo texto:
# login automático do root no tty1, cloud-init, ssh, e rede via iwd/systemd-networkd
# (o Clone OS usa o NetworkManager, que conflita com eles).
rm -rf -- "$profile/airootfs/etc/systemd/system/getty@tty1.service.d" \
          "$profile/airootfs/etc/systemd/system/cloud-init.target.wants" \
          "$profile/airootfs/etc/systemd/network" \
          "$profile/airootfs/etc/systemd/networkd.conf.d"
rm -f -- "$profile/airootfs/etc/motd" \
         "$profile/airootfs/etc/systemd/system/multi-user.target.wants/"{iwd,systemd-networkd,sshd}.service \
         "$profile/airootfs/etc/systemd/system/sockets.target.wants/systemd-networkd.socket" \
         "$profile/airootfs/etc/systemd/system/network-online.target.wants/systemd-networkd-wait-online.service" \
         "$profile/airootfs/etc/systemd/system/dbus-org.freedesktop.network1.service"

echo "==> Compilando os pacotes do AUR (Brave, Claude, Claude Code, yay)"
builder=cloneos-build
id "$builder" >/dev/null 2>&1 || useradd --system --create-home --home-dir "$cache/home" --shell /usr/bin/nologin "$builder"
install -d -o "$builder" -g "$builder" "$cache" "$cache/home" "$cache/src" "$cache/pkg" "$cache/build"
makepkg_as() {
    (cd "$dir" && runuser -u "$builder" -- \
        env HOME="$cache/home" SRCDEST="$cache/src" PKGDEST="$cache/pkg" makepkg "$@")
}
for recipe in "$here"/aur/*/; do
    name="$(basename "$recipe")"
    dir="$cache/build/$name"
    rm -rf -- "$dir"
    cp -r -- "$recipe" "$dir"
    find "$dir" -type f -exec sed -i 's/\r$//' {} +
    chown -R "$builder:$builder" "$dir"
    mapfile -t built < <(makepkg_as --packagelist)
    missing=0
    for pkg in "${built[@]}"; do [[ -f "$pkg" ]] || missing=1; done
    if (( missing )); then
        echo "    $name: compilando"
        makepkg_as --nodeps --noconfirm --force >"$cache/build/$name.log" 2>&1 \
            || { tail -n 30 "$cache/build/$name.log" >&2; echo "Falha ao compilar $name." >&2; exit 1; }
    else
        echo "    $name: já compilado"
    fi
    for pkg in "${built[@]}"; do
        [[ "$pkg" == *-debug-* ]] || cp -- "$pkg" "$repo/"
    done
done
repo-add -q "$repo/cloneos.db.tar.gz" "$repo"/*.pkg.tar.*
cat >>"$profile/pacman.conf" <<EOF

[cloneos]
SigLevel = Optional TrustAll
Server = file://$repo
EOF

echo "==> Aplicando os arquivos do Clone OS"
cp -a -- "$here/profile/airootfs/." "$profile/airootfs/"
cp -- "$here/profile/syslinux/splash.png" "$profile/syslinux/splash.png"
cat -- "$here/profile/profiledef.cloneos.sh" >>"$profile/profiledef.sh"
find "$profile/airootfs" -name __pycache__ -type d -prune -exec rm -rf {} +

# Arquivos editados no Windows podem vir com CRLF, o que quebra scripts e configs.
# (grep sai com 1 quando não acha nada, o que aqui é o normal.)
{ grep -rlI $'\r' "$profile" || true; } | xargs -r sed -i 's/\r$//'

strip() { sed -e 's/#.*//' -e 's/[[:space:]]*$//' -e '/^$/d' "$1"; }
{
    grep -vxF -f <(strip "$here/profile/packages.remove") "$releng/packages.x86_64" || true
    strip "$here/profile/packages.cloneos"
} | sort -u >"$profile/packages.x86_64"
echo "    $(wc -l <"$profile/packages.x86_64") pacotes"

# Menus de boot com o nome do Clone OS
{ grep -rlI 'Arch Linux' "$profile/efiboot" "$profile/grub" "$profile/syslinux" || true; } | xargs -r sed -i \
    -e 's/Arch Linux install medium/Clone OS (live)/g' \
    -e 's/install Arch Linux/install Clone OS/g' \
    -e 's/Arch Linux/Clone OS/g'

echo "==> Gerando a ISO (demora: baixa ~4 GB de pacotes)"
mkarchiso -v -r -w "$work/work" -o "$out" "$profile"
rm -rf -- "$repo"

iso="$(ls -t "$out"/cloneos-*.iso | head -n 1)"
sfs_bytes="$(bsdtar -tvf "$iso" arch/x86_64/airootfs.sfs | awk '{ print $5 }')"
if (( sfs_bytes >= 4294967296 )); then
    echo "Aviso: arch/x86_64/airootfs.sfs tem mais de 4 GiB e não cabe num pendrive FAT32." >&2
fi

if [[ -n "${SUDO_USER:-}" ]]; then
    chown "$SUDO_USER:" "$out"/*.iso 2>/dev/null || true
fi
echo
echo "==> Pronto:"
ls -lh "$iso"
echo "    airootfs.sfs: $(( sfs_bytes / 1024 / 1024 )) MiB"
