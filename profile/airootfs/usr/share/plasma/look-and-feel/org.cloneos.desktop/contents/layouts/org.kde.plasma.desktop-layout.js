// Clone OS: área de trabalho no estilo do Windows 11.
// Barra embaixo, sem flutuar; Iniciar, Pesquisa, Visão de tarefas e apps fixados
// no centro (dois espaçadores flexíveis centralizam o que fica entre eles);
// bandeja do sistema, relógio com a data embaixo e "mostrar área de trabalho" à direita.
// O comando "clonectl taskbar left|center" troca o alinhamento depois.

var panel = new Panel;
panel.location = "bottom";
panel.height = 2 * Math.ceil(gridUnit * 2.6 / 2);
panel.floating = false;
panel.hiding = "none";
panel.opacity = "translucent";

function addSpacer() {
    var spacer = panel.addWidget("org.kde.plasma.panelspacer");
    spacer.currentConfigGroup = ["General"];
    spacer.writeConfig("expanding", true);
}

function addLauncher(desktopFile) {
    var launcher = panel.addWidget("org.kde.plasma.icon");
    launcher.currentConfigGroup = ["General"];
    launcher.writeConfig("url", "file:///usr/share/applications/" + desktopFile);
}

addSpacer();

var start = panel.addWidget("org.kde.plasma.kickoff");
start.currentConfigGroup = ["Shortcuts"];
start.writeConfig("global", "Alt+F1");
start.currentConfigGroup = ["General"];
start.writeConfig("favoritesDisplay", 0);
start.writeConfig("applicationsDisplay", 1);
start.writeConfig("appNameFormat", 0);
start.writeConfig("showActionButtonCaptions", false);
start.writeConfig("favorites", [
    "preferred://browser",
    "terminal-claude.desktop",
    "com.anthropic.Claude.desktop",
    "org.kde.dolphin.desktop",
    "cloneos-configuracoes.desktop",
    "libreoffice-writer.desktop",
    "libreoffice-calc.desktop",
    "libreoffice-impress.desktop",
    "org.kde.kwrite.desktop",
    "org.kde.kcalc.desktop",
    "org.kde.gwenview.desktop",
    "org.kde.haruna.desktop",
    "org.kde.spectacle.desktop",
    "org.kde.kamoso.desktop",
    "org.kde.kolourpaint.desktop",
    "org.kde.konsole.desktop",
    "org.kde.plasma-systemmonitor.desktop",
    "clone-update.desktop",
    "clone-welcome.desktop"
]);

addLauncher("cloneos-pesquisar.desktop");
addLauncher("cloneos-visao-de-tarefas.desktop");

var tasks = panel.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("fill", false);
tasks.writeConfig("iconSpacing", 2);
tasks.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "preferred://browser",
    "applications:terminal-claude.desktop",
    "applications:com.anthropic.Claude.desktop"
]);

addSpacer();

panel.addWidget("org.kde.plasma.systemtray");

var clock = panel.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("showDate", true);
clock.writeConfig("dateDisplayFormat", 2);
clock.writeConfig("dateFormat", "shortDate");

panel.addWidget("org.kde.plasma.showdesktop");

// Área de trabalho: papel de parede do Clone OS e ícones em coluna, como no Windows.
var desktopsArray = desktopsForActivity(currentActivity());
for (var i = 0; i < desktopsArray.length; i++) {
    var desktop = desktopsArray[i];
    desktop.wallpaperPlugin = "org.kde.image";
    desktop.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    desktop.writeConfig("Image", "file:///usr/share/wallpapers/CloneOS-Bloom/");
    desktop.currentConfigGroup = ["General"];
    desktop.writeConfig("arrangement", 1);
}
