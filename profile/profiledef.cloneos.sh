
# --- Clone OS (anexado ao profiledef.sh do releng pelo build.sh) ---
iso_name="cloneos"
iso_label="CLONEOS_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="Clone OS"
iso_application="Clone OS Live (notebook)"
iso_version="0.3-notebook.$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m%d)"
# zstd descompacta rápido, o que acelera o modo live e a cópia do instalador.
# O airootfs.sfs precisa ficar abaixo de 4 GiB para caber num pendrive FAT32.
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '19' '-b' '1M')
file_permissions+=(
  ["/etc/sudoers.d"]="0:0:750"
  ["/etc/sudoers.d/10-wheel"]="0:0:440"
  ["/etc/sudoers.d/20-cloneos-live"]="0:0:440"
  ["/usr/local/bin/clone-install"]="0:0:755"
  ["/usr/local/bin/clone-update"]="0:0:755"
  ["/usr/local/bin/clone-welcome"]="0:0:755"
  ["/usr/local/bin/clonectl"]="0:0:755"
  ["/usr/local/bin/cloneos-aquecer"]="0:0:755"
  ["/usr/local/bin/cloneos-avisar-atualizacoes"]="0:0:755"
  ["/usr/local/bin/clone-antivirus"]="0:0:755"
  ["/usr/local/bin/clone-configuracoes"]="0:0:755"
  ["/usr/local/bin/cloneos-brand"]="0:0:755"
  ["/usr/local/bin/cloneos-build-customize"]="0:0:755"
  ["/usr/local/bin/cloneos-firstrun"]="0:0:755"
  ["/usr/local/bin/cloneos-nomes"]="0:0:755"
  ["/usr/local/bin/cloneos-seguranca"]="0:0:755"
  ["/usr/local/bin/terminal-claude"]="0:0:755"
)
