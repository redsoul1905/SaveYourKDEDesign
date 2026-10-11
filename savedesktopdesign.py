#!/usr/bin/env python3
"""
SaveYourKDEDesign — Sichert & restauriert das komplette KDE-Plasma-Design
(Themes, Icons, Schriften, KWin-Skripte, Plasma-Einstellungen, Kvantum,
Wallpaper, Panel-Layouts) sowie Paketlisten (pacman, AUR, Flatpak).

Für KDE Plasma auf Arch-basierten Systemen (CachyOS, EndeavourOS …),
Ubuntu/Debian (apt) und Fedora (dnf).
Benötigt PyQt6:  Arch: python-pyqt6 | Ubuntu/Fedora: python3-pyqt6

Sprachen: Deutsch, English, Français, Italiano, Español, Português, Türkçe
"""

import io
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QProcess, QSettings, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
    QInputDialog, QLineEdit, QStyleFactory,
)

HOME = Path.home()
APP_NAME = "SaveYourKDEDesign"
# Keep the old identity in source for v1.6's update validation and keep its
# settings namespace, rollback paths and SDD1 codes compatible.
LEGACY_APP_NAME = "SaveDesktopDesign"
VERSION = "1.7.2"

# Update über die GitHub-Releases — nur Standardbibliothek, kein Token.
GITHUB_REPO = "redsoul1905/SaveYourKDEDesign"
LEGACY_GITHUB_REPO = "redsoul1905/Savedesktopdesign"
RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RAW_URL = ("https://raw.githubusercontent.com/" + GITHUB_REPO
           + "/{tag}/savedesktopdesign.py")
MAX_DOWNLOAD = 2_000_000   # Obergrenze, damit ein kaputter Server uns nicht flutet

# ----------------------------------------------------------------------------
# Übersetzungen / Translations
# ----------------------------------------------------------------------------
LANG_NAMES = {
    "de": "Deutsch", "en": "English", "fr": "Français", "it": "Italiano",
    "es": "Español", "pt": "Português", "tr": "Türkçe",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "de": {
        "app_subtitle": "KDE-Design sichern & laden",
        "lang_label": "Sprache:",
        "tab_backup": "Sichern",
        "tab_restore": "Wiederherstellen",
        "backup_title": "Komplettes Plasma-Design + Paketlisten in eine Datei sichern",
        "choose_box": "Was soll gesichert werden?",
        "cat_plasma": "Plasma- & KWin-Einstellungen",
        "cat_gtk": "GTK- & Kvantum-Design (Glass etc.)",
        "cat_themes": "Themes, Icons & Cursor",
        "cat_fonts": "Schriften",
        "cat_kwin": "KWin-Skripte & Effekte",
        "cat_wallpaper": "Wallpaper & Konsole-Profile",
        "cat_packages": "Paketlisten (pacman / AUR / Flatpak)",
        "btn_backup": "  Backup erstellen …",
        "msg_select_one": "Bitte mindestens eine Kategorie auswählen.",
        "dlg_save": "Backup speichern unter …",
        "dlg_open": "Backup-Archiv wählen",
        "dlg_archive_filter": "Archiv (*.tar.gz)",
        "log_creating": "Backup wird erstellt …",
        "log_pkg_creating": "  + Paketlisten erzeugen …",
        "log_skipped": "  ! übersprungen",
        "done_prefix": "\n✔ Fertig: ",
        "msg_backup_done": "Backup erstellt:",
        "err_prefix": "\n✘ Fehler:\n",
        "msg_backup_failed": "Backup fehlgeschlagen — Details im Protokoll.",
        "restore_title": "Backup-Archiv laden und Design wiederherstellen",
        "restore_hint": "1-Klick-Restore: Archiv wählen → Dateien werden zurückkopiert.\n"
                        "Danach optional Pakete installieren und Plasma neu starten.",
        "btn_restore": "  Archiv wählen & wiederherstellen …",
        "btn_packages": "  Pakete installieren (öffnet Terminal)",
        "btn_plasma": "  Plasma neu starten (Design anwenden)",
        "mf_created": "Erstellt", "mf_host": "Rechner",
        "mf_categories": "Kategorien", "mf_packages": "Paketlisten",
        "yes": "ja", "no": "nein",
        "msg_confirm_restore": "Dieses Backup wiederherstellen?\nBestehende Einstellungen werden überschrieben.",
        "log_extracting": "Archiv wird entpackt …",
        "err_invalid_archive": "Ungültiges Archiv: kein 'home/'-Ordner enthalten.",
        "log_pkglists_saved": "Paketlisten gespeichert unter: ",
        "log_fontcache": "Schrift-Cache wird aktualisiert …",
        "log_kwin_reload": "KWin-Einstellungen werden neu geladen …",
        "log_restored": "\n✔ Design wiederhergestellt!",
        "msg_restored_pkg": "Design wiederhergestellt!\n\nJetzt optional Pakete installieren und Plasma neu starten (oder ab- und anmelden), damit alles greift.",
        "msg_restored": "Design wiederhergestellt!\n\nPlasma neu starten (oder ab- und anmelden), damit alles greift.",
        "msg_restore_failed": "Restore fehlgeschlagen — Details im Protokoll.",
        "msg_no_terminal": "Kein Terminal gefunden. Bitte manuell ausführen:\n",
        "msg_no_pkglists": "Keine Paketlisten gefunden. Bitte zuerst ein Backup wiederherstellen, das Paketlisten enthält.",
        "msg_term_failed": "Das Terminal konnte nicht gestartet werden. Führe den Befehl manuell im Terminal aus:",
        "log_pkg_terminal": "Terminal zur Paketinstallation geöffnet …",
        "msg_confirm_pkg": "Jetzt Pakete installieren? Es öffnet sich ein Terminal, das nach deinem sudo-Passwort fragt. Gefundene Listen:",
        "msg_pkg_opened": "Ein Terminal wurde geöffnet — folge dort den Anweisungen (sudo-Passwort eingeben). Falls kein Fenster erscheint, führe diesen Befehl manuell im Terminal aus:",
        "msg_busy": "Es läuft bereits ein Vorgang. Bitte warte, bis er abgeschlossen ist.",
        "btn_update": "  Nach Updates suchen",
        "upd_checking": "Suche nach Updates …",
        "upd_current": "Du hast bereits die neueste Version ({cur}).",
        "upd_available": "Neue Version {new} verfügbar — installiert ist {cur}.\n\nJetzt aktualisieren?",
        "upd_installing": "Update wird geladen …",
        "upd_done": "Update auf {new} installiert.\n\nDie Änderungen greifen nach einem Neustart der App. Jetzt neu starten?",
        "upd_failed": "Update fehlgeschlagen:",
        "upd_not_writable": "Die installierte Programmdatei ist nicht beschreibbar:\n{path}",
        "upd_git_clone": "Dieser Ordner ist ein Git-Repository. Aktualisiere hier lieber mit:\n\n./install.sh --update",
        "upd_no_release": "Auf GitHub ist noch kein Release veröffentlicht.",
        "ver_current": "aktuell",
        "ver_update": "Update auf {new} verfügbar",
        "cb_autocheck": "Beim Start prüfen",
        "dlg_restore_title": "Was soll zurückgespielt werden?",
        "cb_rollback": "Vorher den aktuellen Zustand sichern (Rückholen möglich)",
        "btn_rollback": "  Zustand vor der letzten Wiederherstellung zurückholen",
        "log_rollback": "Sicherungskopie des aktuellen Zustands wird angelegt …",
        "msg_no_rollback": "Keine Sicherungskopie vorhanden. Sie entsteht automatisch bei der nächsten Wiederherstellung.",
        "msg_confirm_rollback": "Den Zustand von vor der letzten Wiederherstellung zurückholen?\n\nAngelegt: {when}",
        "log_app_added": "  + SaveYourKDEDesign fürs neue Gerät beigelegt",
        "msg_busy_close": "Ein Vorgang läuft noch. Das Fenster kann erst danach geschlossen werden.",
        "msg_confirm_plasma": "Plasma jetzt neu starten? Der Desktop ist kurz weg.",
    },
    "en": {
        "app_subtitle": "Back up & restore your KDE design",
        "lang_label": "Language:",
        "tab_backup": "Back up",
        "tab_restore": "Restore",
        "backup_title": "Back up your complete Plasma design + package lists into one file",
        "choose_box": "What should be backed up?",
        "cat_plasma": "Plasma & KWin settings",
        "cat_gtk": "GTK & Kvantum design (Glass etc.)",
        "cat_themes": "Themes, icons & cursors",
        "cat_fonts": "Fonts",
        "cat_kwin": "KWin scripts & effects",
        "cat_wallpaper": "Wallpapers & Konsole profiles",
        "cat_packages": "Package lists (pacman / AUR / Flatpak)",
        "btn_backup": "  Create backup …",
        "msg_select_one": "Please select at least one category.",
        "dlg_save": "Save backup as …",
        "dlg_open": "Choose backup archive",
        "dlg_archive_filter": "Archive (*.tar.gz)",
        "log_creating": "Creating backup …",
        "log_pkg_creating": "  + Generating package lists …",
        "log_skipped": "  ! skipped",
        "done_prefix": "\n✔ Done: ",
        "msg_backup_done": "Backup created:",
        "err_prefix": "\n✘ Error:\n",
        "msg_backup_failed": "Backup failed — see log for details.",
        "restore_title": "Load a backup archive and restore your design",
        "restore_hint": "One-click restore: pick the archive → files are copied back.\n"
                        "Then optionally install packages and restart Plasma.",
        "btn_restore": "  Choose archive & restore …",
        "btn_packages": "  Install packages (opens a terminal)",
        "btn_plasma": "  Restart Plasma (apply design)",
        "mf_created": "Created", "mf_host": "Computer",
        "mf_categories": "Categories", "mf_packages": "Package lists",
        "yes": "yes", "no": "no",
        "msg_confirm_restore": "Restore this backup?\nExisting settings will be overwritten.",
        "log_extracting": "Extracting archive …",
        "err_invalid_archive": "Invalid archive: no 'home/' folder found.",
        "log_pkglists_saved": "Package lists saved to: ",
        "log_fontcache": "Updating font cache …",
        "log_kwin_reload": "Reloading KWin settings …",
        "log_restored": "\n✔ Design restored!",
        "msg_restored_pkg": "Design restored!\n\nOptionally install the packages now, then restart Plasma (or log out and back in) so everything takes effect.",
        "msg_restored": "Design restored!\n\nRestart Plasma (or log out and back in) so everything takes effect.",
        "msg_restore_failed": "Restore failed — see log for details.",
        "msg_no_terminal": "No terminal found. Please run manually:\n",
        "msg_no_pkglists": "No package lists found. Please restore a backup that contains package lists first.",
        "msg_term_failed": "Could not start the terminal. Run this command manually in a terminal:",
        "log_pkg_terminal": "Opened a terminal to install packages …",
        "msg_confirm_pkg": "Install packages now? A terminal will open and ask for your sudo password. Lists found:",
        "msg_pkg_opened": "A terminal was opened — follow the instructions there (enter your sudo password). If no window appears, run this command manually in a terminal:",
        "msg_busy": "Another operation is already running. Please wait until it has finished.",
        "btn_update": "  Check for updates",
        "upd_checking": "Checking for updates …",
        "upd_current": "You already have the latest version ({cur}).",
        "upd_available": "Version {new} is available — you have {cur}.\n\nUpdate now?",
        "upd_installing": "Downloading update …",
        "upd_done": "Updated to {new}.\n\nThe changes take effect after a restart. Restart now?",
        "upd_failed": "Update failed:",
        "upd_not_writable": "The installed program file is not writable:\n{path}",
        "upd_git_clone": "This folder is a Git repository. Update it with:\n\n./install.sh --update",
        "upd_no_release": "No release has been published on GitHub yet.",
        "ver_current": "up to date",
        "ver_update": "update to {new} available",
        "cb_autocheck": "Check at startup",
        "dlg_restore_title": "What should be restored?",
        "cb_rollback": "Back up the current state first (so you can roll back)",
        "btn_rollback": "  Roll back to the state before the last restore",
        "log_rollback": "Backing up the current state …",
        "msg_no_rollback": "No rollback copy available. One is created automatically the next time you restore.",
        "msg_confirm_rollback": "Roll back to the state from before the last restore?\n\nCreated: {when}",
        "log_app_added": "  + SaveYourKDEDesign bundled for the new machine",
        "msg_busy_close": "An operation is still running. The window can only be closed once it has finished.",
        "msg_confirm_plasma": "Restart Plasma now? The desktop will disappear briefly.",
    },
    "fr": {
        "app_subtitle": "Sauvegarder et restaurer votre design KDE",
        "lang_label": "Langue :",
        "tab_backup": "Sauvegarder",
        "tab_restore": "Restaurer",
        "backup_title": "Sauvegarder l'ensemble du design Plasma + listes de paquets dans un seul fichier",
        "choose_box": "Que faut-il sauvegarder ?",
        "cat_plasma": "Paramètres Plasma & KWin",
        "cat_gtk": "Design GTK & Kvantum (Glass, etc.)",
        "cat_themes": "Thèmes, icônes et curseurs",
        "cat_fonts": "Polices",
        "cat_kwin": "Scripts et effets KWin",
        "cat_wallpaper": "Fonds d'écran et profils Konsole",
        "cat_packages": "Listes de paquets (pacman / AUR / Flatpak)",
        "btn_backup": "  Créer une sauvegarde …",
        "msg_select_one": "Veuillez sélectionner au moins une catégorie.",
        "dlg_save": "Enregistrer la sauvegarde sous …",
        "dlg_open": "Choisir l'archive de sauvegarde",
        "dlg_archive_filter": "Archive (*.tar.gz)",
        "log_creating": "Création de la sauvegarde …",
        "log_pkg_creating": "  + Génération des listes de paquets …",
        "log_skipped": "  ! ignoré",
        "done_prefix": "\n✔ Terminé : ",
        "msg_backup_done": "Sauvegarde créée :",
        "err_prefix": "\n✘ Erreur :\n",
        "msg_backup_failed": "Échec de la sauvegarde — détails dans le journal.",
        "restore_title": "Charger une archive et restaurer le design",
        "restore_hint": "Restauration en un clic : choisissez l'archive → les fichiers sont recopiés.\n"
                        "Ensuite, installez éventuellement les paquets et redémarrez Plasma.",
        "btn_restore": "  Choisir l'archive et restaurer …",
        "btn_packages": "  Installer les paquets (ouvre un terminal)",
        "btn_plasma": "  Redémarrer Plasma (appliquer le design)",
        "mf_created": "Créée", "mf_host": "Ordinateur",
        "mf_categories": "Catégories", "mf_packages": "Listes de paquets",
        "yes": "oui", "no": "non",
        "msg_confirm_restore": "Restaurer cette sauvegarde ?\nLes paramètres existants seront écrasés.",
        "log_extracting": "Extraction de l'archive …",
        "err_invalid_archive": "Archive non valide : aucun dossier « home/ ».",
        "log_pkglists_saved": "Listes de paquets enregistrées dans : ",
        "log_fontcache": "Mise à jour du cache des polices …",
        "log_kwin_reload": "Rechargement des paramètres KWin …",
        "log_restored": "\n✔ Design restauré !",
        "msg_restored_pkg": "Design restauré !\n\nInstallez éventuellement les paquets, puis redémarrez Plasma (ou déconnectez-vous et reconnectez-vous) pour tout appliquer.",
        "msg_restored": "Design restauré !\n\nRedémarrez Plasma (ou déconnectez-vous et reconnectez-vous) pour tout appliquer.",
        "msg_restore_failed": "Échec de la restauration — détails dans le journal.",
        "msg_no_terminal": "Aucun terminal trouvé. Veuillez exécuter manuellement :\n",
        "msg_no_pkglists": "Aucune liste de paquets trouvée. Restaurez d'abord une sauvegarde contenant des listes de paquets.",
        "msg_term_failed": "Impossible de démarrer le terminal. Exécutez cette commande manuellement dans un terminal :",
        "log_pkg_terminal": "Terminal ouvert pour l'installation des paquets …",
        "msg_confirm_pkg": "Installer les paquets maintenant ? Un terminal s'ouvrira et demandera votre mot de passe sudo. Listes trouvées :",
        "msg_pkg_opened": "Un terminal a été ouvert — suivez-y les instructions (saisissez votre mot de passe sudo). Si aucune fenêtre n'apparaît, exécutez cette commande manuellement dans un terminal :",
        "msg_busy": "Une opération est déjà en cours. Veuillez attendre qu'elle se termine.",
        "btn_update": "  Rechercher des mises à jour",
        "upd_checking": "Recherche de mises à jour …",
        "upd_current": "Vous avez déjà la dernière version ({cur}).",
        "upd_available": "La version {new} est disponible — vous avez {cur}.\n\nMettre à jour maintenant ?",
        "upd_installing": "Téléchargement de la mise à jour …",
        "upd_done": "Mise à jour vers {new} effectuée.\n\nLes changements prennent effet après un redémarrage. Redémarrer maintenant ?",
        "upd_failed": "Échec de la mise à jour :",
        "upd_not_writable": "Le fichier du programme installé n'est pas modifiable :\n{path}",
        "upd_git_clone": "Ce dossier est un dépôt Git. Mettez-le à jour avec :\n\n./install.sh --update",
        "upd_no_release": "Aucune version n'a encore été publiée sur GitHub.",
        "ver_current": "à jour",
        "ver_update": "mise à jour {new} disponible",
        "cb_autocheck": "Vérifier au démarrage",
        "dlg_restore_title": "Que faut-il restaurer ?",
        "cb_rollback": "Sauvegarder d'abord l'état actuel (retour possible)",
        "btn_rollback": "  Revenir à l'état d'avant la dernière restauration",
        "log_rollback": "Sauvegarde de l'état actuel …",
        "msg_no_rollback": "Aucune copie de secours disponible. Elle sera créée automatiquement lors de la prochaine restauration.",
        "msg_confirm_rollback": "Revenir à l'état d'avant la dernière restauration ?\n\nCréée : {when}",
        "log_app_added": "  + SaveYourKDEDesign joint pour la nouvelle machine",
        "msg_busy_close": "Une opération est encore en cours. La fenêtre ne pourra être fermée qu'après.",
        "msg_confirm_plasma": "Redémarrer Plasma maintenant ? Le bureau disparaîtra brièvement.",
    },
    "it": {
        "app_subtitle": "Salva e ripristina il tuo design KDE",
        "lang_label": "Lingua:",
        "tab_backup": "Salva",
        "tab_restore": "Ripristina",
        "backup_title": "Salva l'intero design Plasma + elenchi dei pacchetti in un unico file",
        "choose_box": "Cosa salvare?",
        "cat_plasma": "Impostazioni Plasma e KWin",
        "cat_gtk": "Design GTK e Kvantum (Glass ecc.)",
        "cat_themes": "Temi, icone e cursori",
        "cat_fonts": "Caratteri",
        "cat_kwin": "Script ed effetti KWin",
        "cat_wallpaper": "Sfondi e profili Konsole",
        "cat_packages": "Elenchi dei pacchetti (pacman / AUR / Flatpak)",
        "btn_backup": "  Crea backup …",
        "msg_select_one": "Seleziona almeno una categoria.",
        "dlg_save": "Salva il backup come …",
        "dlg_open": "Scegli l'archivio di backup",
        "dlg_archive_filter": "Archivio (*.tar.gz)",
        "log_creating": "Creazione del backup …",
        "log_pkg_creating": "  + Generazione elenchi pacchetti …",
        "log_skipped": "  ! saltato",
        "done_prefix": "\n✔ Fatto: ",
        "msg_backup_done": "Backup creato:",
        "err_prefix": "\n✘ Errore:\n",
        "msg_backup_failed": "Backup non riuscito — dettagli nel registro.",
        "restore_title": "Carica un archivio di backup e ripristina il design",
        "restore_hint": "Ripristino con un clic: scegli l'archivio → i file vengono ricopiati.\n"
                        "Poi, se vuoi, installa i pacchetti e riavvia Plasma.",
        "btn_restore": "  Scegli archivio e ripristina …",
        "btn_packages": "  Installa i pacchetti (apre un terminale)",
        "btn_plasma": "  Riavvia Plasma (applica il design)",
        "mf_created": "Creato", "mf_host": "Computer",
        "mf_categories": "Categorie", "mf_packages": "Elenchi pacchetti",
        "yes": "sì", "no": "no",
        "msg_confirm_restore": "Ripristinare questo backup?\nLe impostazioni esistenti verranno sovrascritte.",
        "log_extracting": "Estrazione dell'archivio …",
        "err_invalid_archive": "Archivio non valido: cartella 'home/' mancante.",
        "log_pkglists_saved": "Elenchi pacchetti salvati in: ",
        "log_fontcache": "Aggiornamento della cache dei caratteri …",
        "log_kwin_reload": "Ricaricamento delle impostazioni KWin …",
        "log_restored": "\n✔ Design ripristinato!",
        "msg_restored_pkg": "Design ripristinato!\n\nSe vuoi, installa ora i pacchetti, poi riavvia Plasma (o esci e rientra) per applicare tutto.",
        "msg_restored": "Design ripristinato!\n\nRiavvia Plasma (o esci e rientra) per applicare tutto.",
        "msg_restore_failed": "Ripristino non riuscito — dettagli nel registro.",
        "msg_no_terminal": "Nessun terminale trovato. Esegui manualmente:\n",
        "msg_no_pkglists": "Nessun elenco di pacchetti trovato. Ripristina prima un backup che contenga gli elenchi dei pacchetti.",
        "msg_term_failed": "Impossibile avviare il terminale. Esegui questo comando manualmente in un terminale:",
        "log_pkg_terminal": "Terminale aperto per l'installazione dei pacchetti …",
        "msg_confirm_pkg": "Installare ora i pacchetti? Si aprirà un terminale che chiederà la password sudo. Elenchi trovati:",
        "msg_pkg_opened": "È stato aperto un terminale — segui lì le istruzioni (inserisci la password sudo). Se non compare alcuna finestra, esegui questo comando manualmente in un terminale:",
        "msg_busy": "È già in corso un'operazione. Attendi che sia terminata.",
        "btn_update": "  Cerca aggiornamenti",
        "upd_checking": "Ricerca di aggiornamenti …",
        "upd_current": "Hai già la versione più recente ({cur}).",
        "upd_available": "È disponibile la versione {new} — hai la {cur}.\n\nAggiornare ora?",
        "upd_installing": "Download dell'aggiornamento …",
        "upd_done": "Aggiornato alla versione {new}.\n\nLe modifiche hanno effetto dopo un riavvio. Riavviare ora?",
        "upd_failed": "Aggiornamento non riuscito:",
        "upd_not_writable": "Il file del programma installato non è scrivibile:\n{path}",
        "upd_git_clone": "Questa cartella è un repository Git. Aggiorna con:\n\n./install.sh --update",
        "upd_no_release": "Su GitHub non è ancora stata pubblicata alcuna release.",
        "ver_current": "aggiornato",
        "ver_update": "aggiornamento {new} disponibile",
        "cb_autocheck": "Controlla all'avvio",
        "dlg_restore_title": "Che cosa va ripristinato?",
        "cb_rollback": "Salva prima lo stato attuale (ritorno possibile)",
        "btn_rollback": "  Torna allo stato precedente all'ultimo ripristino",
        "log_rollback": "Salvataggio dello stato attuale …",
        "msg_no_rollback": "Nessuna copia di sicurezza disponibile. Verrà creata automaticamente al prossimo ripristino.",
        "msg_confirm_rollback": "Tornare allo stato precedente all'ultimo ripristino?\n\nCreata: {when}",
        "log_app_added": "  + SaveYourKDEDesign incluso per la nuova macchina",
        "msg_busy_close": "Un'operazione è ancora in corso. La finestra potrà essere chiusa solo al termine.",
        "msg_confirm_plasma": "Riavviare Plasma adesso? Il desktop sparirà per un momento.",
    },
    "es": {
        "app_subtitle": "Guardar y restaurar tu diseño KDE",
        "lang_label": "Idioma:",
        "tab_backup": "Guardar",
        "tab_restore": "Restaurar",
        "backup_title": "Guarda todo el diseño de Plasma + listas de paquetes en un solo archivo",
        "choose_box": "¿Qué se debe guardar?",
        "cat_plasma": "Ajustes de Plasma y KWin",
        "cat_gtk": "Diseño GTK y Kvantum (Glass, etc.)",
        "cat_themes": "Temas, iconos y cursores",
        "cat_fonts": "Fuentes",
        "cat_kwin": "Scripts y efectos de KWin",
        "cat_wallpaper": "Fondos de pantalla y perfiles de Konsole",
        "cat_packages": "Listas de paquetes (pacman / AUR / Flatpak)",
        "btn_backup": "  Crear copia de seguridad …",
        "msg_select_one": "Selecciona al menos una categoría.",
        "dlg_save": "Guardar copia de seguridad como …",
        "dlg_open": "Elegir archivo de copia de seguridad",
        "dlg_archive_filter": "Archivo (*.tar.gz)",
        "log_creating": "Creando la copia de seguridad …",
        "log_pkg_creating": "  + Generando listas de paquetes …",
        "log_skipped": "  ! omitido",
        "done_prefix": "\n✔ Listo: ",
        "msg_backup_done": "Copia de seguridad creada:",
        "err_prefix": "\n✘ Error:\n",
        "msg_backup_failed": "La copia de seguridad falló — detalles en el registro.",
        "restore_title": "Cargar un archivo de copia y restaurar el diseño",
        "restore_hint": "Restauración con un clic: elige el archivo → los archivos se copian de vuelta.\n"
                        "Después, opcionalmente instala los paquetes y reinicia Plasma.",
        "btn_restore": "  Elegir archivo y restaurar …",
        "btn_packages": "  Instalar paquetes (abre una terminal)",
        "btn_plasma": "  Reiniciar Plasma (aplicar el diseño)",
        "mf_created": "Creado", "mf_host": "Equipo",
        "mf_categories": "Categorías", "mf_packages": "Listas de paquetes",
        "yes": "sí", "no": "no",
        "msg_confirm_restore": "¿Restaurar esta copia de seguridad?\nSe sobrescribirán los ajustes actuales.",
        "log_extracting": "Extrayendo el archivo …",
        "err_invalid_archive": "Archivo no válido: no contiene la carpeta 'home/'.",
        "log_pkglists_saved": "Listas de paquetes guardadas en: ",
        "log_fontcache": "Actualizando la caché de fuentes …",
        "log_kwin_reload": "Recargando los ajustes de KWin …",
        "log_restored": "\n✔ ¡Diseño restaurado!",
        "msg_restored_pkg": "¡Diseño restaurado!\n\nOpcionalmente instala ahora los paquetes y reinicia Plasma (o cierra y vuelve a iniciar sesión) para que todo surta efecto.",
        "msg_restored": "¡Diseño restaurado!\n\nReinicia Plasma (o cierra y vuelve a iniciar sesión) para que todo surta efecto.",
        "msg_restore_failed": "La restauración falló — detalles en el registro.",
        "msg_no_terminal": "No se encontró ninguna terminal. Ejecuta manualmente:\n",
        "msg_no_pkglists": "No se encontraron listas de paquetes. Restaura primero una copia de seguridad que contenga listas de paquetes.",
        "msg_term_failed": "No se pudo iniciar la terminal. Ejecuta este comando manualmente en una terminal:",
        "log_pkg_terminal": "Se abrió una terminal para instalar los paquetes …",
        "msg_confirm_pkg": "¿Instalar los paquetes ahora? Se abrirá una terminal que pedirá tu contraseña de sudo. Listas encontradas:",
        "msg_pkg_opened": "Se abrió una terminal — sigue allí las instrucciones (introduce tu contraseña de sudo). Si no aparece ninguna ventana, ejecuta este comando manualmente en una terminal:",
        "msg_busy": "Ya hay una operación en curso. Espera a que termine.",
        "btn_update": "  Buscar actualizaciones",
        "upd_checking": "Buscando actualizaciones …",
        "upd_current": "Ya tienes la versión más reciente ({cur}).",
        "upd_available": "La versión {new} está disponible — tienes la {cur}.\n\n¿Actualizar ahora?",
        "upd_installing": "Descargando la actualización …",
        "upd_done": "Actualizado a {new}.\n\nLos cambios se aplican tras reiniciar. ¿Reiniciar ahora?",
        "upd_failed": "La actualización falló:",
        "upd_not_writable": "El archivo del programa instalado no se puede escribir:\n{path}",
        "upd_git_clone": "Esta carpeta es un repositorio Git. Actualiza con:\n\n./install.sh --update",
        "upd_no_release": "Todavía no se ha publicado ninguna versión en GitHub.",
        "ver_current": "actualizado",
        "ver_update": "actualización {new} disponible",
        "cb_autocheck": "Comprobar al inicio",
        "dlg_restore_title": "¿Qué se debe restaurar?",
        "cb_rollback": "Guardar antes el estado actual (permite volver atrás)",
        "btn_rollback": "  Volver al estado anterior a la última restauración",
        "log_rollback": "Guardando el estado actual …",
        "msg_no_rollback": "No hay ninguna copia de seguridad. Se crea automáticamente en la próxima restauración.",
        "msg_confirm_rollback": "¿Volver al estado anterior a la última restauración?\n\nCreada: {when}",
        "log_app_added": "  + SaveYourKDEDesign incluido para el equipo nuevo",
        "msg_busy_close": "Todavía hay una operación en curso. La ventana solo se puede cerrar cuando haya terminado.",
        "msg_confirm_plasma": "¿Reiniciar Plasma ahora? El escritorio desaparecerá un momento.",
    },
    "pt": {
        "app_subtitle": "Salvar e restaurar seu design KDE",
        "lang_label": "Idioma:",
        "tab_backup": "Salvar",
        "tab_restore": "Restaurar",
        "backup_title": "Salve todo o design do Plasma + listas de pacotes em um único arquivo",
        "choose_box": "O que deve ser salvo?",
        "cat_plasma": "Configurações do Plasma e KWin",
        "cat_gtk": "Design GTK e Kvantum (Glass etc.)",
        "cat_themes": "Temas, ícones e cursores",
        "cat_fonts": "Fontes",
        "cat_kwin": "Scripts e efeitos do KWin",
        "cat_wallpaper": "Papéis de parede e perfis do Konsole",
        "cat_packages": "Listas de pacotes (pacman / AUR / Flatpak)",
        "btn_backup": "  Criar backup …",
        "msg_select_one": "Selecione pelo menos uma categoria.",
        "dlg_save": "Salvar backup como …",
        "dlg_open": "Escolher arquivo de backup",
        "dlg_archive_filter": "Arquivo (*.tar.gz)",
        "log_creating": "Criando o backup …",
        "log_pkg_creating": "  + Gerando listas de pacotes …",
        "log_skipped": "  ! ignorado",
        "done_prefix": "\n✔ Concluído: ",
        "msg_backup_done": "Backup criado:",
        "err_prefix": "\n✘ Erro:\n",
        "msg_backup_failed": "Falha no backup — detalhes no registro.",
        "restore_title": "Carregar um arquivo de backup e restaurar o design",
        "restore_hint": "Restauração com um clique: escolha o arquivo → os arquivos são copiados de volta.\n"
                        "Depois, opcionalmente instale os pacotes e reinicie o Plasma.",
        "btn_restore": "  Escolher arquivo e restaurar …",
        "btn_packages": "  Instalar pacotes (abre um terminal)",
        "btn_plasma": "  Reiniciar o Plasma (aplicar o design)",
        "mf_created": "Criado", "mf_host": "Computador",
        "mf_categories": "Categorias", "mf_packages": "Listas de pacotes",
        "yes": "sim", "no": "não",
        "msg_confirm_restore": "Restaurar este backup?\nAs configurações existentes serão substituídas.",
        "log_extracting": "Extraindo o arquivo …",
        "err_invalid_archive": "Arquivo inválido: pasta 'home/' não encontrada.",
        "log_pkglists_saved": "Listas de pacotes salvas em: ",
        "log_fontcache": "Atualizando o cache de fontes …",
        "log_kwin_reload": "Recarregando as configurações do KWin …",
        "log_restored": "\n✔ Design restaurado!",
        "msg_restored_pkg": "Design restaurado!\n\nOpcionalmente instale os pacotes agora e reinicie o Plasma (ou saia e entre novamente) para aplicar tudo.",
        "msg_restored": "Design restaurado!\n\nReinicie o Plasma (ou saia e entre novamente) para aplicar tudo.",
        "msg_restore_failed": "Falha na restauração — detalhes no registro.",
        "msg_no_terminal": "Nenhum terminal encontrado. Execute manualmente:\n",
        "msg_no_pkglists": "Nenhuma lista de pacotes encontrada. Restaure primeiro um backup que contenha listas de pacotes.",
        "msg_term_failed": "Não foi possível iniciar o terminal. Execute este comando manualmente em um terminal:",
        "log_pkg_terminal": "Terminal aberto para instalar os pacotes …",
        "msg_confirm_pkg": "Instalar os pacotes agora? Um terminal será aberto e pedirá sua senha do sudo. Listas encontradas:",
        "msg_pkg_opened": "Um terminal foi aberto — siga as instruções lá (digite sua senha do sudo). Se nenhuma janela aparecer, execute este comando manualmente em um terminal:",
        "msg_busy": "Já há uma operação em andamento. Aguarde até que ela termine.",
        "btn_update": "  Procurar atualizações",
        "upd_checking": "Procurando atualizações …",
        "upd_current": "Você já tem a versão mais recente ({cur}).",
        "upd_available": "A versão {new} está disponível — você tem a {cur}.\n\nAtualizar agora?",
        "upd_installing": "Baixando a atualização …",
        "upd_done": "Atualizado para {new}.\n\nAs alterações têm efeito após reiniciar. Reiniciar agora?",
        "upd_failed": "Falha na atualização:",
        "upd_not_writable": "O arquivo do programa instalado não pode ser gravado:\n{path}",
        "upd_git_clone": "Esta pasta é um repositório Git. Atualize com:\n\n./install.sh --update",
        "upd_no_release": "Ainda não há nenhuma release publicada no GitHub.",
        "ver_current": "atualizado",
        "ver_update": "atualização {new} disponível",
        "cb_autocheck": "Verificar ao iniciar",
        "dlg_restore_title": "O que deve ser restaurado?",
        "cb_rollback": "Salvar antes o estado atual (permite voltar atrás)",
        "btn_rollback": "  Voltar ao estado anterior à última restauração",
        "log_rollback": "Salvando o estado atual …",
        "msg_no_rollback": "Nenhuma cópia de segurança disponível. Ela é criada automaticamente na próxima restauração.",
        "msg_confirm_rollback": "Voltar ao estado anterior à última restauração?\n\nCriada: {when}",
        "log_app_added": "  + SaveYourKDEDesign incluído para o computador novo",
        "msg_busy_close": "Uma operação ainda está em andamento. A janela só pode ser fechada depois disso.",
        "msg_confirm_plasma": "Reiniciar o Plasma agora? A área de trabalho sumirá por um instante.",
    },
    "tr": {
        "app_subtitle": "KDE tasarımınızı yedekleyin ve geri yükleyin",
        "lang_label": "Dil:",
        "tab_backup": "Yedekle",
        "tab_restore": "Geri Yükle",
        "backup_title": "Tüm Plasma tasarımını + paket listelerini tek dosyada yedekleyin",
        "choose_box": "Neler yedeklensin?",
        "cat_plasma": "Plasma ve KWin ayarları",
        "cat_gtk": "GTK ve Kvantum tasarımı (Glass vb.)",
        "cat_themes": "Temalar, simgeler ve imleçler",
        "cat_fonts": "Yazı tipleri",
        "cat_kwin": "KWin betikleri ve efektleri",
        "cat_wallpaper": "Duvar kâğıtları ve Konsole profilleri",
        "cat_packages": "Paket listeleri (pacman / AUR / Flatpak)",
        "btn_backup": "  Yedek oluştur …",
        "msg_select_one": "Lütfen en az bir kategori seçin.",
        "dlg_save": "Yedeği farklı kaydet …",
        "dlg_open": "Yedek arşivini seç",
        "dlg_archive_filter": "Arşiv (*.tar.gz)",
        "log_creating": "Yedek oluşturuluyor …",
        "log_pkg_creating": "  + Paket listeleri oluşturuluyor …",
        "log_skipped": "  ! atlandı",
        "done_prefix": "\n✔ Tamamlandı: ",
        "msg_backup_done": "Yedek oluşturuldu:",
        "err_prefix": "\n✘ Hata:\n",
        "msg_backup_failed": "Yedekleme başarısız — ayrıntılar günlükte.",
        "restore_title": "Yedek arşivini yükleyin ve tasarımı geri getirin",
        "restore_hint": "Tek tıkla geri yükleme: arşivi seçin → dosyalar geri kopyalanır.\n"
                        "Ardından isteğe bağlı paketleri kurun ve Plasma'yı yeniden başlatın.",
        "btn_restore": "  Arşiv seç ve geri yükle …",
        "btn_packages": "  Paketleri kur (terminal açılır)",
        "btn_plasma": "  Plasma'yı yeniden başlat (tasarımı uygula)",
        "mf_created": "Oluşturulma", "mf_host": "Bilgisayar",
        "mf_categories": "Kategoriler", "mf_packages": "Paket listeleri",
        "yes": "evet", "no": "hayır",
        "msg_confirm_restore": "Bu yedek geri yüklensin mi?\nMevcut ayarların üzerine yazılacak.",
        "log_extracting": "Arşiv çıkarılıyor …",
        "err_invalid_archive": "Geçersiz arşiv: 'home/' klasörü yok.",
        "log_pkglists_saved": "Paket listeleri şuraya kaydedildi: ",
        "log_fontcache": "Yazı tipi önbelleği güncelleniyor …",
        "log_kwin_reload": "KWin ayarları yeniden yükleniyor …",
        "log_restored": "\n✔ Tasarım geri yüklendi!",
        "msg_restored_pkg": "Tasarım geri yüklendi!\n\nİsterseniz şimdi paketleri kurun, ardından her şeyin etkinleşmesi için Plasma'yı yeniden başlatın (veya oturumu kapatıp açın).",
        "msg_restored": "Tasarım geri yüklendi!\n\nHer şeyin etkinleşmesi için Plasma'yı yeniden başlatın (veya oturumu kapatıp açın).",
        "msg_restore_failed": "Geri yükleme başarısız — ayrıntılar günlükte.",
        "msg_no_terminal": "Terminal bulunamadı. Lütfen elle çalıştırın:\n",
        "msg_no_pkglists": "Paket listesi bulunamadı. Lütfen önce paket listeleri içeren bir yedeği geri yükleyin.",
        "msg_term_failed": "Terminal başlatılamadı. Bu komutu terminalde elle çalıştırın:",
        "log_pkg_terminal": "Paket kurulumu için terminal açıldı …",
        "msg_confirm_pkg": "Paketler şimdi kurulsun mu? Sudo parolanızı soran bir terminal açılacak. Bulunan listeler:",
        "msg_pkg_opened": "Bir terminal açıldı — oradaki yönergeleri izleyin (sudo parolanızı girin). Hiçbir pencere görünmezse bu komutu terminalde elle çalıştırın:",
        "msg_busy": "Zaten bir işlem sürüyor. Lütfen bitmesini bekleyin.",
        "btn_update": "  Güncellemeleri denetle",
        "upd_checking": "Güncellemeler denetleniyor …",
        "upd_current": "Zaten en son sürüme sahipsiniz ({cur}).",
        "upd_available": "{new} sürümü mevcut — sizde {cur} var.\n\nŞimdi güncellensin mi?",
        "upd_installing": "Güncelleme indiriliyor …",
        "upd_done": "{new} sürümüne güncellendi.\n\nDeğişiklikler yeniden başlattıktan sonra etkin olur. Şimdi yeniden başlatılsın mı?",
        "upd_failed": "Güncelleme başarısız:",
        "upd_not_writable": "Kurulu program dosyası yazılabilir değil:\n{path}",
        "upd_git_clone": "Bu klasör bir Git deposu. Şununla güncelleyin:\n\n./install.sh --update",
        "upd_no_release": "GitHub'da henüz yayımlanmış bir sürüm yok.",
        "ver_current": "güncel",
        "ver_update": "{new} güncellemesi mevcut",
        "cb_autocheck": "Başlangıçta denetle",
        "dlg_restore_title": "Neler geri yüklensin?",
        "cb_rollback": "Önce mevcut durumu yedekle (geri dönülebilir)",
        "btn_rollback": "  Son geri yüklemeden önceki duruma dön",
        "log_rollback": "Mevcut durum yedekleniyor …",
        "msg_no_rollback": "Yedek kopya yok. Bir sonraki geri yüklemede otomatik olarak oluşturulur.",
        "msg_confirm_rollback": "Son geri yüklemeden önceki duruma dönülsün mü?\n\nOluşturulma: {when}",
        "log_app_added": "  + Yeni cihaz için SaveYourKDEDesign eklendi",
        "msg_busy_close": "Bir işlem hâlâ sürüyor. Pencere ancak bittikten sonra kapatılabilir.",
        "msg_confirm_plasma": "Plasma şimdi yeniden başlatılsın mı? Masaüstü kısa süreliğine kaybolur.",
    },
}

_current_lang = "de"

# New sharing strings fall back to English in the other supported languages.
TRANSLATIONS["en"].update({
    "tab_share": "Share design", "share_export": "Create export code …",
    "share_import": "Import code …", "share_copy": "Copy code",
    "share_title": "Share your KDE design via Catbox",
    "share_last_code": "Last successful export code",
    "share_hint": "No account needed. Public uploads up to 200 MB. Anonymous files may be deleted after two years without access. Keep a local backup.",
    "share_consent": "Publish a design package to Catbox? Anyone with the code can download it. This exports selected visual settings, themes, fonts and wallpapers, not your full backup or installed-app list. Theme assets can still contain personal content: review your selected theme and wallpaper before sharing. Only share content you may redistribute. Catbox's terms apply: https://catbox.moe/legal.php",
    "share_upload": "Creating and uploading the public design package …",
    "share_download": "Downloading and checking the design package …",
    "share_code": "Paste the complete SDD1 export code:",
    "share_ready": "Uploaded. Copy this code to share the design. Keep the complete code, including its checksum.",
    "share_review": "The downloaded package has passed the file and checksum checks. Themes and widgets may contain executable code. Only apply designs from authors you trust. Your current settings will be backed up first. Full visual identity cannot be verified automatically.",
    "share_blocked": "Import checks found remaining differences. Available automatic installations are offered next. No design settings have been changed:\n\n",
    "share_apply": "Apply this design?", "share_error": "Sharing failed",
    "share_complete": "Design files applied. Log out and back in to load the panel layout and themes. Check the result before sharing it further; identical rendering has not been verified.",
    "share_details": "Package contents", "share_omitted": "Not exported",
    "share_install": "Install the missing Kvantum theme engine using this system's package manager? Administrator authentication is required. Only the locally defined package is installed; no commands from the design package are run. Remaining compatibility differences will be checked again afterwards.",
    "share_installing": "Installing the missing theme engine …",
    "share_desktop_install": "Install the KDE desktop system-wide now? This can download many packages and take a long time. Administrator authentication is required. Your existing desktop is retained. No distribution upgrade is performed.",
    "share_desktop_working": "Installing KDE. Do not shut down or interrupt the package manager …",
    "share_desktop_done": "KDE packages installed. Log out, select Plasma at the login screen and reopen this app. The import resumes automatically without entering the code again. No design settings have been applied yet.",
    "share_extensions": "Bundled extensions will replace local copies with the exported version (including older versions). Declared minimum Plasma versions are checked; undeclared dependencies and runtime compatibility cannot be verified automatically.",
})
TRANSLATIONS["de"].update({
    "tab_share": "Design teilen", "share_export": "Export-Code erstellen …",
    "share_import": "Code importieren …", "share_copy": "Code kopieren",
    "share_title": "KDE-Design über Catbox teilen",
    "share_last_code": "Letzter erfolgreicher Export-Code",
    "share_hint": "Ohne Konto. Öffentliche Uploads bis 200 MB. Anonyme Dateien können nach zwei Jahren ohne Zugriff gelöscht werden. Lokales Backup behalten.",
    "share_consent": "Design-Paket auf Catbox veröffentlichen? Jeder mit dem Code kann es herunterladen. Exportiert werden ausgewählte optische Einstellungen, Themes, Schriften und Wallpaper, nicht dein vollständiges Backup oder die Liste installierter Programme. Theme-Dateien können trotzdem persönliche Inhalte enthalten: prüfe dein ausgewähltes Theme und Wallpaper vor dem Teilen. Teile nur Inhalte, die du weitergeben darfst. Es gelten die Catbox-Bedingungen: https://catbox.moe/legal.php",
    "share_upload": "Öffentliches Design-Paket wird erstellt und hochgeladen …",
    "share_download": "Design-Paket wird heruntergeladen und geprüft …",
    "share_code": "Vollständigen SDD1-Export-Code einfügen:",
    "share_ready": "Hochgeladen. Diesen Code zum Teilen kopieren. Den vollständigen Code einschließlich Prüfsumme behalten.",
    "share_review": "Dateien und Prüfsumme des Downloads wurden geprüft. Themes und Widgets können ausführbaren Code enthalten. Wende nur Designs vertrauenswürdiger Autoren an. Deine bisherigen Einstellungen werden zuerst gesichert. Eine identische Darstellung lässt sich nicht automatisch bestätigen.",
    "share_blocked": "Die Import-Prüfung hat noch Unterschiede gefunden. Verfügbare automatische Installationen werden anschließend angeboten. Noch keine Design-Einstellungen geändert:\n\n",
    "share_apply": "Dieses Design anwenden?", "share_error": "Teilen fehlgeschlagen",
    "share_complete": "Design-Dateien übernommen. Bitte ab- und wieder anmelden, damit Panel-Layout und Themes geladen werden. Prüfe das Ergebnis; eine identische Darstellung wurde nicht bestätigt.",
    "share_details": "Paketinhalt", "share_omitted": "Nicht exportiert",
    "share_install": "Fehlende Kvantum-Theme-Engine mit der Paketverwaltung dieses Systems installieren? Dafür ist eine Administrator-Anmeldung nötig. Installiert wird nur das im Programm festgelegte Paket; keine Befehle aus dem Design-Paket. Anschließend werden verbleibende Kompatibilitätsunterschiede erneut geprüft.",
    "share_installing": "Fehlende Theme-Engine wird installiert …",
    "share_desktop_install": "KDE jetzt systemweit zusätzlich installieren? Dies kann viele Pakete herunterladen und lange dauern. Administrator-Anmeldung erforderlich. Die vorhandene Oberfläche bleibt erhalten. Kein Distributions-Upgrade.",
    "share_desktop_working": "KDE wird installiert. Nicht herunterfahren oder die Paketverwaltung unterbrechen …",
    "share_desktop_done": "KDE-Pakete installiert. Bitte abmelden, am Anmeldebildschirm Plasma auswählen und dieses Programm wieder öffnen. Der Import wird automatisch fortgesetzt; der Code muss nicht erneut eingegeben werden. Noch keine Design-Einstellungen übernommen.",
    "share_extensions": "Mitgelieferte Erweiterungen ersetzen lokale Kopien durch die exportierte Version (auch ältere Versionen). Angegebene Plasma-Mindestversionen werden geprüft; nicht angegebene Abhängigkeiten und die Laufzeit-Kompatibilität lassen sich nicht automatisch bestätigen.",
})


def T(key: str) -> str:
    """Übersetzten Text für die aktuelle Sprache liefern."""
    return TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"]).get(
        key, TRANSLATIONS["en"].get(key, key))


def detect_language(settings: QSettings) -> str:
    saved = settings.value("language", "")
    if saved in TRANSLATIONS:
        return saved
    env = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
           or os.environ.get("LANG") or "en")[:2].lower()
    return env if env in TRANSLATIONS else "en"


# ----------------------------------------------------------------------------
# Was gesichert wird — Pfade relativ zum Home-Verzeichnis
# (Schlüssel = stabile IDs, Anzeigename kommt aus den Übersetzungen)
# ----------------------------------------------------------------------------
CATEGORIES: dict[str, list[str]] = {
    "cat_plasma": [
        ".config/kdeglobals",
        ".config/kdedefaults",              # Global-Theme-Vorgaben (Plasma 5.24+/6)
        ".config/plasma-localerc",
        ".config/kactivitymanagerdrc",
        ".config/systemsettingsrc",
        ".config/plasma-workspace",         # Autostart-/Env-Skripte der Sitzung
        ".config/kwinrc",
        ".config/kwinrulesrc",
        ".config/kglobalshortcutsrc",
        ".config/khotkeysrc",
        ".config/kscreenlockerrc",
        ".config/ksplashrc",
        ".config/ksmserverrc",
        ".config/krunnerrc",
        ".config/plasmarc",
        ".config/plasmashellrc",
        ".config/plasmanotifyrc",
        ".config/plasma-org.kde.plasma.desktop-appletsrc",
        ".config/kcminputrc",
        ".config/kded5rc",
        ".config/kded6rc",
        ".config/breezerc",
        ".config/oxygenrc",
        ".config/klassyrc",                # Klassy-Fensterdekoration
        ".config/klassy",                  # Klassy-Presets
        ".config/lightlyrc",               # Lightly-Dekoration
        ".config/sierrabreezeenhancedrc",  # SierraBreezeEnhanced
        ".config/kwalletrc",
        ".config/dolphinrc",
        ".config/konsolerc",
        ".config/yakuakerc",
        ".config/spectaclerc",
        ".config/katerc",
        ".config/lattedockrc",
        ".config/latte",
        ".config/autostart",
        ".config/kde.org",
        ".config/xsettingsd",
        ".config/Trolltech.conf",
        ".config/mimeapps.list",
        ".config/touchpadrc",
        ".config/powermanagementprofilesrc",
    ],
    "cat_gtk": [
        ".config/gtkrc",
        ".config/gtkrc-2.0",
        ".config/gtk-3.0",
        ".config/gtk-4.0",
        ".config/Kvantum",
        ".gtkrc-2.0",
    ],
    "cat_themes": [
        ".local/share/plasma",            # Desktop-Themes, Look&Feel, Plasmoids
        ".local/share/aurorae",           # Fensterdekorationen
        ".local/share/color-schemes",
        ".local/share/icons",
        ".local/share/themes",
        ".themes",
        ".icons",
    ],
    "cat_fonts": [
        ".local/share/fonts",
        ".fonts",
        ".config/fontconfig",
        ".local/share/kfontinst",
    ],
    "cat_kwin": [
        ".local/share/kwin",              # Skripte, Effekte, Tabbox
        ".local/share/kservices5",
        ".local/share/kservices6",
        ".local/share/knewstuff3",
    ],
    "cat_wallpaper": [
        ".local/share/wallpapers",
        ".local/share/konsole",
        ".local/share/kxmlgui5",
        ".local/share/kxmlgui6",
    ],
}


def _run_cmd(cmd: list[str], timeout: int = 120) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             env={**os.environ, "LC_ALL": "C"})
        return out.stdout if out.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def gather_package_lists() -> dict[str, str]:
    """Erzeugt Paketlisten als {dateiname: inhalt} — pacman, apt, dnf, flatpak."""
    lists: dict[str, str] = {}

    if shutil.which("pacman"):
        for fname, cmd in {
            "pacman-explicit.txt": ["pacman", "-Qqen"],   # explizit, offizielle Repos
            "pacman-foreign.txt": ["pacman", "-Qqem"],    # AUR / fremd
        }.items():
            out = _run_cmd(cmd)
            if out:
                lists[fname] = out

    if shutil.which("pacman-conf"):                       # aktivierte Repos
        out = _run_cmd(["pacman-conf", "--repo-list"])
        if out:
            lists["pacman-repos.txt"] = out

    if shutil.which("apt-mark"):                          # Ubuntu / Debian
        out = _run_cmd(["apt-mark", "showmanual"])
        if out:
            lists["apt-manual.txt"] = out

    if shutil.which("dnf"):                               # Fedora
        out = (_run_cmd(["dnf", "repoquery", "--userinstalled",
                         "--queryformat", "%{name}\n"], 300)
               or _run_cmd(["dnf", "repoquery", "--userinstalled"], 300))
        if out:
            # Duplikate entfernen, leere Zeilen filtern
            names = sorted({l.strip() for l in out.splitlines() if l.strip()})
            lists["dnf-packages.txt"] = "\n".join(names) + "\n"

    if shutil.which("flatpak"):
        out = _run_cmd(["flatpak", "list", "--app", "--columns=application"])
        if out:
            lists["flatpak.txt"] = out

    return lists


def rollback_path() -> Path:
    """HOME wird in Tests umgebogen — daher bewusst zur Laufzeit bilden."""
    return HOME / ".savedesktopdesign-rollback.tar.gz"


def make_rollback(rel_paths: list[str], categories: list[str]) -> str:
    """Sichert den aktuellen Zustand genau der Pfade, die gleich
    überschrieben werden. Das Netz unter dem Restore."""
    present = [r for r in rel_paths if os.path.lexists(HOME / r)]
    if not present:
        return ""
    manifest = {
        "app": APP_NAME,
        "version": VERSION,
        "rollback": True,
        "created": datetime.now().isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "user": os.environ.get("USER", ""),
        "categories": categories,
        "with_packages": False,
        "paths": present,
    }
    dest = rollback_path()
    tmp = dest.with_name(dest.name + ".new")
    with tarfile.open(tmp, "w:gz") as tar:
        for rel in present:
            tar.add(HOME / rel, arcname=f"home/{rel}")
        data = json.dumps(manifest, indent=2).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(data)
        info.mtime = int(datetime.now().timestamp())
        tar.addfile(info, io.BytesIO(data))
    os.replace(tmp, dest)     # erst umbenennen, wenn das Archiv vollständig ist
    return str(dest)


def _version_tuple(v: str) -> tuple:
    """'v1.4.0' -> (1, 4, 0). Alles Unparsbare wird zu 0, damit ein
    ungewöhnlicher Tag-Name keinen Absturz auslöst."""
    parts = []
    for chunk in v.strip().lstrip("vV").split("."):
        digits = ""
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    # A released version must update a development build with the same number.
    return tuple((parts + [0, 0, 0])[:3]) + (0 if "-" in v else 1,)


# Public sharing is deliberately a different format from a private backup.
CATBOX_API = "https://catbox.moe/user/api.php"
CATBOX_FILES = "https://files.catbox.moe/"
SHARE_LIMIT = 200_000_000
EXPANDED_LIMIT = 1_000_000_000
SHARE_FILE_LIMIT = 200_000  # Tela-dark plus inherited Breeze has over 108k paths.
MANIFEST_LIMIT = 16_000_000
CODE_RE = re.compile(r"SDD1:([a-zA-Z0-9]{6,16}\.sdd):([0-9a-f]{64})\Z")
HOME_TOKEN = "@SDD_HOME@"
VISUAL_CONFIGS = {
    "kdeglobals", "kwinrc", "plasmarc", "plasmashellrc",
    "plasma-org.kde.plasma.desktop-appletsrc", "kcminputrc",
    "ksplashrc", "kscreenlockerrc", "breezerc", "oxygenrc",
    "klassyrc", "lightlyrc", "sierrabreezeenhancedrc",
    "gtk-3.0/settings.ini", "gtk-4.0/settings.ini",
}
# Explicit keys only: arbitrary widget settings can contain notes, URLs,
# credentials, local file paths, or commands. Unknown keys never go public.
VISUAL_KEYS = set("""
ColorScheme LookAndFeelPackage widgetStyle font fixed menuFont smallestReadableFont
toolBarFont activeFont shadeSortColumn contrast SingleClick AnimationDurationFactor
XftAntialias XftHintStyle XftSubPixel XftDPI AccentColor AccentColorFromWallpaper
cursorTheme cursorSize Theme name theme library BorderSize BorderSizeAuto
ButtonsOnLeft ButtonsOnRight NoPlugin CustomButtonPositions
plugin wallpaperplugin formfactor location activityId lastScreen screen
immutability containmentId SystrayContainmentId AppletOrder
panelVisibility alignment floating lengthMode minLength maxLength thickness
height width offset maximumLength minimumLength
iconSize iconSizeRatio taskbarPosition showToolTips
showDate dateFormat use24hClock showSeconds boldText fontFamily fontSize
showWeekNumbers firstDayOfWeek showLocalTimezone
Image FillMode Blur ShowMediaControls showDesktopLayout
BackgroundNormal BackgroundAlternate ForegroundNormal ForegroundInactive
ForegroundActive ForegroundLink ForegroundVisited ForegroundNegative
ForegroundNeutral ForegroundPositive DecorationFocus DecorationHover
activeBackground activeBlend activeForeground inactiveBackground inactiveBlend
inactiveForeground Color ColorEffect ColorAmount ContrastEffect ContrastAmount
IntensityEffect IntensityAmount Enable ApplyToInactive ChangeSelectionColor
DisableLut FilterContrast
gtk-theme-name gtk-icon-theme-name gtk-font-name gtk-cursor-theme-name
gtk-cursor-theme-size gtk-application-prefer-dark-theme
BlurStrength NoiseStrength Radius cornerRadius
""".split()) - {"activityId"}  # activity IDs refer to private, machine-local state
ASSET_BASES = (
    "plasma/desktoptheme", "plasma/look-and-feel", "plasma/plasmoids",
    "plasma/wallpapers", "aurorae/themes", "icons", "color-schemes",
    "wallpapers", "fonts", "kwin/scripts", "kwin/effects", "Kvantum", "themes",
)


def read_kconfig(path: Path) -> list[tuple[str, str, str]]:
    """Preserve nested KConfig group syntax without interpreting interpolation."""
    if not path.is_file():
        return []
    if path.stat().st_size > 4_000_000:
        raise ValueError(f"Configuration too large: {path.name}")
    group = ""
    values = []
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if line.startswith("[") and line.endswith("]"):
            group = line
        elif "=" in line and not line.startswith(("#", ";")):
            key, value = line.split("=", 1)
            values.append((group, key.strip(), value))
    return values


def screen_profile() -> list[dict]:
    # Called in the GUI thread before starting a worker.
    app = QGuiApplication.instance()
    if app is None:
        return []
    return sorted([{"width": s.geometry().width(), "height": s.geometry().height(),
                    "x": s.geometry().x(), "y": s.geometry().y(),
                    "scale": round(s.devicePixelRatio(), 3)}
                   for s in app.screens()], key=lambda s: (s["x"], s["y"]))


def desktop_profile(screens: list[dict]) -> dict:
    out = _run_cmd(["plasmashell", "--version"], 10) or ""
    version = re.search(r"\b(\d+\.\d+(?:\.\d+)?)\b", out)
    return {"plasma": version.group(1) if version else "",
            "desktop": "KDE" if "kde" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower().split(":") else "",
            "session": os.environ.get("XDG_SESSION_TYPE", ""),
            "screens": screens}


def share_path_allowed(rel: str) -> bool:
    if not isinstance(rel, str) or "\\" in rel or "\x00" in rel:
        return False
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return False
    if rel in {".config/" + n for n in VISUAL_CONFIGS}:
        return True
    if rel.startswith(".config/Kvantum/"):
        return True
    return any(rel.startswith(".local/share/" + base + "/") for base in ASSET_BASES)


def _safe_asset_name(name: str) -> bool:
    return bool(name and re.fullmatch(r"[\w .+@#-]+", name) and name not in (".", ".."))


def selected_font_files(family: str) -> list[Path]:
    """Include every installed style of an exact family, never a silent fallback."""
    output = _run_cmd(["fc-list", "--format", "%{family}\t%{file}\n"], 15) or ""
    found = set()
    for line in output.splitlines():
        names, sep, filename = line.partition("\t")
        if sep and family.casefold() in {n.strip().casefold() for n in names.split(",")}:
            path = Path(filename)
            if path.is_file():
                found.add(path)
    return sorted(found)


def public_design(stage: Path, screens: list[dict], log=lambda message: None) -> dict:
    """Build a visual-only tree, never a copy of the user's private backup."""
    home = stage / "home"
    home.mkdir()
    sources = [HOME / ".local/share", Path("/usr/local/share"), Path("/usr/share")]
    requirements, omitted, paths = [], [], set()
    copied_bytes = 0
    copied_count = 0
    seen = set()
    exported_fonts = set()

    def copy_asset(src: Path, rel: str, allowed_root: Path):
        nonlocal copied_bytes, copied_count
        if not share_path_allowed(rel):
            raise ValueError("Invalid public asset destination")
        # Resolve icon symlinks into regular files, but never follow links into
        # private directories or copy sockets/devices/compiled binaries.
        real = src.resolve(strict=True)
        if not real.is_relative_to(allowed_root.resolve()):
            raise ValueError(f"Asset link leaves its theme directory: {src.name}")
        if real.is_dir():
            if real in seen:
                raise ValueError("Cyclic theme directory link")
            seen.add(real)
            for child in sorted(real.iterdir()):
                copy_asset(child, rel + "/" + child.name, allowed_root)
            seen.remove(real)
        elif real.is_file():
            size = real.stat().st_size
            dst = home / rel
            previous_size = dst.stat().st_size if rel in paths else 0
            next_bytes = copied_bytes - previous_size + size
            next_count = copied_count + (rel not in paths)
            if next_bytes > EXPANDED_LIMIT:
                raise ValueError(f"Design zu groß / too large unpacked: {next_bytes:,} bytes; limit {EXPANDED_LIMIT:,}. Asset: {rel}")
            if next_count > SHARE_FILE_LIMIT:
                raise ValueError(f"Zu viele Design-Dateien / too many design files: {next_count:,}; limit {SHARE_FILE_LIMIT:,}. Asset: {rel}")
            with real.open("rb") as stream:
                if stream.read(4) == b"\x7fELF":
                    raise ValueError(f"Compiled plugin needs installation on the target: {src.name}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(real, dst)
            copied_bytes = next_bytes
            copied_count = next_count
            paths.add(rel)
        else:
            raise ValueError(f"Unsupported asset type: {src.name}")

    added = set()

    def asset(base: str, name: str):
        if not _safe_asset_name(name) or (base, name) in added:
            return
        added.add((base, name))
        rel = base + "/" + name
        if base == "icons" and name == "hicolor":
            # This fallback also contains icons owned by installed applications,
            # often linked outside the theme tree. Keep it supplied by the target
            # distribution instead of exporting the source's application icons.
            requirements.append({"kind": "asset", "name": rel})
            return
        candidates = [root / rel for root in sources]
        if base == "icons":
            candidates.insert(1, HOME / ".icons" / name)
        if base == "themes":
            candidates.insert(1, HOME / ".themes" / name)
        if base == "Kvantum":
            candidates = [HOME / ".config/Kvantum" / name,
                          HOME / ".themes" / name / "Kvantum",
                          HOME / ".local/share/themes" / name / "Kvantum", *candidates]
        found = [p for p in candidates if p.exists()]
        if not found:
            requirements.append({"kind": "asset", "name": rel})
            return
        log("  + " + rel)
        # Merge lower-priority system defaults first, then user overrides.
        for src in reversed(found):
            target_rel = (".config/" if base == "Kvantum" else ".local/share/") + rel
            copy_asset(src, target_rel, src.parent)
        if base == "icons":
            for src in found:
                for _, key, value in read_kconfig(src / "index.theme"):
                    if key == "Inherits":
                        for parent in value.split(","):
                            asset("icons", parent.strip())

    for filename in sorted(VISUAL_CONFIGS):
        # Plasma stores global-theme defaults separately. Export their effective
        # values, then overlay explicit user choices, so distro defaults on the
        # receiving machine cannot replace the source's selected theme.
        defaults = read_kconfig(HOME / ".config/kdedefaults" / filename)
        overrides = read_kconfig(HOME / ".config" / filename)
        values = list({(g, k): (g, k, v) for g, k, v in [*defaults, *overrides]}.values())
        lines, group_before = [], None
        for group, key, value in values:
            enabled_effect = filename == "kwinrc" and group == "[Plugins]" and key.endswith("Enabled")
            if key not in VISUAL_KEYS and not enabled_effect:
                omitted.append(filename + ":" + key)
                continue
            if "\x00" in value or len(value) > 8192:
                continue
            if key == "Image":
                raw = urllib.parse.unquote(value.removeprefix("file://"))
                wallpaper = Path(raw)
                if not wallpaper.is_file():
                    requirements.append({"kind": "wallpaper", "name": "Unavailable wallpaper"})
                    continue
                if wallpaper.stat().st_size > SHARE_LIMIT:
                    raise ValueError("Wallpaper exceeds 200 MB")
                digest = sha256_file(wallpaper)[:16]
                rel = ".local/share/wallpapers/sdd/" + digest + wallpaper.suffix
                copy_asset(wallpaper, rel, wallpaper.parent)
                value = "file://" + HOME_TOKEN + "/" + rel
            elif "/" in value or "\\" in value or "://" in value or str(HOME) in value:
                omitted.append(filename + ":" + key)
                continue
            if filename == "kdeglobals":
                if key == "LookAndFeelPackage":
                    asset("plasma/look-and-feel", value)
                elif key == "ColorScheme":
                    asset("color-schemes", value + ".colors")
                elif group == "[Icons]" and key == "Theme":
                    asset("icons", value)
                elif key == "widgetStyle":
                    requirements.append({"kind": "style", "name": value})
            if key in {"font", "fixed", "menuFont", "smallestReadableFont", "toolBarFont",
                       "activeFont", "fontFamily", "gtk-font-name"}:
                family = value.split(",")[0].strip()
                if key == "gtk-font-name":
                    family = re.sub(r"\s+\d+(?:\.\d+)?$", "", family)
                if family and family not in exported_fonts:
                    exported_fonts.add(family)
                    fonts = selected_font_files(family)
                    for fp in fonts:
                        copy_asset(fp, ".local/share/fonts/sdd/" + sha256_file(fp)[:16] + fp.suffix, fp.parent)
                    if not fonts:
                        requirements.append({"kind": "font", "name": family})
            if filename == "kcminputrc" and key == "cursorTheme":
                asset("icons", value)
            if filename.startswith("gtk-"):
                if key == "gtk-theme-name":
                    asset("themes", value)
                elif key in {"gtk-icon-theme-name", "gtk-cursor-theme-name"}:
                    asset("icons", value)
            if filename == "plasmarc" and group == "[Theme]" and key == "name":
                asset("plasma/desktoptheme", value)
            if key == "wallpaperplugin":
                asset("plasma/wallpapers", value)
            if filename == "plasma-org.kde.plasma.desktop-appletsrc" and key == "plugin":
                asset("plasma/plasmoids", value)
            if filename == "kwinrc" and key == "library":
                requirements.append({"kind": "decoration", "name": value})
            if filename == "kwinrc" and key == "theme" and value.startswith("__aurorae__svg__"):
                asset("aurorae/themes", value.removeprefix("__aurorae__svg__"))
            if enabled_effect and value.lower() == "true":
                effect = key.removesuffix("Enabled")
                # User scripts/effects are portable assets; native effects must
                # already be installed in a compatible build on the target.
                available = False
                for base in ("kwin/scripts", "kwin/effects"):
                    if any((root / base / effect).exists() for root in sources):
                        asset(base, effect)
                        available = True
                if not available:
                    requirements.append({"kind": "effect", "name": effect})
            if group != group_before:
                lines.append(group)
                group_before = group
            lines.append(key + "=" + value)
        if lines:
            dest = home / ".config" / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
            paths.add(".config/" + filename)

    # Kvantum's selected theme includes its own SVG/config assets.
    kv = read_kconfig(HOME / ".config/Kvantum/kvantum.kvconfig")
    theme = next((v for _, k, v in kv if k == "theme"), "")
    if _safe_asset_name(theme):
        asset("Kvantum", theme)
        if theme.endswith("#"):
            asset("Kvantum", theme.removesuffix("#"))
        rel = ".config/Kvantum/kvantum.kvconfig"
        (home / rel).parent.mkdir(parents=True, exist_ok=True)
        (home / rel).write_text("[General]\ntheme=" + theme + "\n")
        paths.add(rel)
    if not paths:
        raise ValueError("No shareable KDE design found")
    profile = desktop_profile(screens)
    if not profile.get("plasma") or not profile.get("session") or not profile.get("screens"):
        raise ValueError("Cannot determine the KDE version, session or screen layout; export from your KDE desktop session")
    if "desktop" in profile and profile["desktop"] != "KDE":
        raise ValueError("Export from a KDE Plasma session / Bitte aus einer KDE-Plasma-Sitzung exportieren")
    return {"app": APP_NAME, "version": VERSION, "public_design": 1,
            "created": datetime.now().isoformat(timespec="seconds"),
            "profile": profile, "paths": sorted(set(paths)),
            "requirements": requirements, "omitted_settings": len(omitted),
            "categories": [], "with_packages": False}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected redirect from Catbox")


def catbox_open(request):
    return urllib.request.build_opener(NoRedirect()).open(request, timeout=60)


def upload_design(path: Path, progress=lambda value: None) -> str:
    size = path.stat().st_size
    if not 0 < size <= SHARE_LIMIT:
        raise ValueError("Catbox accepts design packages up to 200 MB")
    boundary = "sdd" + uuid.uuid4().hex
    head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"reqtype\"\r\n\r\nfileupload\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"fileToUpload\"; filename=\"design.sdd\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n").encode()
    tail = f"\r\n--{boundary}--\r\n".encode()

    def body():
        yield head
        sent = 0
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                yield chunk
                sent += len(chunk)
                progress(int(sent * 100 / size))
        yield tail

    request = urllib.request.Request(CATBOX_API, data=body(), headers={
        "Content-Type": "multipart/form-data; boundary=" + boundary,
        "Content-Length": str(len(head) + size + len(tail)),
        "User-Agent": APP_NAME + "/" + VERSION}, method="POST")
    with catbox_open(request) as response:
        url = response.read(4096).decode("utf-8").strip()
    match = re.fullmatch(re.escape(CATBOX_FILES) + r"([a-zA-Z0-9]{6,16}\.sdd)", url)
    if not match:
        raise ValueError("Catbox rejected the upload or returned an unexpected response")
    return "SDD1:" + match.group(1) + ":" + sha256_file(path)


def download_design(code: str, path: Path, progress=lambda value: None):
    match = CODE_RE.fullmatch(code.strip())
    if not match:
        raise ValueError("Invalid SDD1 code. Copy the complete code, including its checksum.")
    req = urllib.request.Request(CATBOX_FILES + match.group(1),
                                 headers={"User-Agent": APP_NAME + "/" + VERSION})
    created = False
    try:
        with catbox_open(req) as response, path.open("xb") as stream:
            created = True
            length = int(response.headers.get("Content-Length", "0"))
            if length < 0 or length > SHARE_LIMIT:
                raise ValueError("Download exceeds 200 MB")
            total = 0
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                total += len(chunk)
                if total > SHARE_LIMIT:
                    raise ValueError("Download exceeds 200 MB")
                stream.write(chunk)
                progress(min(99, int(total * 100 / length)) if length else 0)
        if sha256_file(path) != match.group(2):
            raise ValueError("Checksum mismatch: the design package is damaged or has changed")
        progress(100)
    except Exception:
        if created:
            path.unlink(missing_ok=True)
        raise


def public_tar_metadata(member):
    # tar.add otherwise publishes the local username, UID/GID, timestamps,
    # and possible PAX metadata even if the manifest contains no identity.
    member.uid = member.gid = 0
    member.uname = member.gname = ""
    member.mtime = 0
    member.mode = 0o644
    member.pax_headers = {}
    return member


def inspect_public_archive(path: Path) -> dict:
    with tarfile.open(path, "r:gz") as archive:
        total, count, names, actual = 0, 0, set(), set()
        manifest = None
        for member in archive:
            count += 1
            if member.name != "manifest.json":
                total += member.size
            if count > SHARE_FILE_LIMIT + 1 or total > EXPANDED_LIMIT:
                raise ValueError("Archive exceeds the unpacked size/file limit")
            if member.name in names or not member.isfile():
                raise ValueError("Design archives must contain unique regular files only")
            names.add(member.name)
            if member.name == "manifest.json":
                if member.size > MANIFEST_LIMIT:
                    raise ValueError("Manifest too large")
                manifest = json.load(archive.extractfile(member))
            elif member.name.startswith("home/") and share_path_allowed(member.name[5:]):
                actual.add(member.name[5:])
            else:
                raise ValueError("Unexpected path in public design archive")
        if not isinstance(manifest, dict) or manifest.get("public_design") != 1:
            raise ValueError("Not a supported public design package")
        paths = manifest.get("paths")
        if (not isinstance(paths, list) or not paths
                or not all(isinstance(p, str) and share_path_allowed(p) for p in paths)
                or len(paths) != len(set(paths)) or set(paths) != actual):
            raise ValueError("Design manifest does not match the archive contents")
        if not isinstance(manifest.get("profile"), dict):
            raise ValueError("Missing compatibility profile")
        profile = manifest["profile"]
        if any(not isinstance(profile.get(k), str) or len(profile[k]) > 80 for k in ("plasma", "session")):
            raise ValueError("Invalid desktop profile")
        screens = profile.get("screens")
        if not isinstance(screens, list) or len(screens) > 32:
            raise ValueError("Invalid screen profile")
        for screen in screens:
            if (not isinstance(screen, dict) or set(screen) != {"width", "height", "x", "y", "scale"}
                    or any(type(value) not in (int, float) or not -100000 < value < 100000
                           for value in screen.values())
                    or screen["width"] <= 0 or screen["height"] <= 0 or screen["scale"] <= 0):
                raise ValueError("Invalid screen profile")
        requirements = manifest.get("requirements")
        if not isinstance(requirements, list) or len(requirements) > 1000:
            raise ValueError("Invalid requirements")
        for req in requirements:
            if (not isinstance(req, dict) or req.get("kind") not in
                    {"asset", "style", "effect", "decoration", "font", "wallpaper"}
                    or not isinstance(req.get("name"), str) or len(req["name"]) > 512):
                raise ValueError("Invalid component requirement")
        return manifest


def profile_value(profile: dict, key: str):
    value = profile.get(key)
    if key == "screens" and isinstance(value, list):
        return sorted(value, key=lambda row: tuple(row.get(k, 0) for k in
                      ("x", "y", "width", "height", "scale")))
    return value


def matching_profile(source: dict, current: dict) -> bool:
    return all(profile_value(source, k) and profile_value(source, k) == profile_value(current, k)
               for k in ("plasma", "session", "screens"))


def package_profile_compatible(source: dict, current: dict) -> bool:
    """Display layout/session differences must not prevent dependency repair.

    Applying the design still runs the full compatibility check independently.
    """
    return bool(current.get("plasma") and current["plasma"] == source.get("plasma"))


def plugin_roots(current: dict):
    major = "5" if current.get("plasma", "").startswith("5.") else "6"
    return [Path(p.format(major=major)) for p in (
        "/usr/lib/qt{major}/plugins", "/usr/lib64/qt{major}/plugins",
        "/usr/lib/x86_64-linux-gnu/qt{major}/plugins",
        "/usr/lib/aarch64-linux-gnu/qt{major}/plugins")]


def native_effect_available(name: str, current: dict) -> bool:
    if not _safe_asset_name(name):
        return False
    candidates = {name + ".so", "kwin_effect_" + name + ".so", "kwin4_effect_" + name + ".so"}
    # A config key such as kwin4_effect_glass may refer to glass.so.
    candidates.add(name.removeprefix("kwin4_effect_") + ".so")
    return any((root / folder / filename).is_file()
               for root in plugin_roots(current)
               for folder in ("kwin/effects/plugins", "kwin-x11/effects/plugins")
               for filename in candidates)


def compatibility_issues(manifest: dict, current: dict, styles: list[str]) -> list[str]:
    source = manifest["profile"]
    issues = []
    if "desktop" in current and "kde" not in current["desktop"].lower().split(":"):
        issues.append("Please log into a KDE Plasma session / Bitte in KDE Plasma anmelden")
    for key in ("plasma", "session", "screens"):
        if not source.get(key) or not current.get(key) or profile_value(source, key) != profile_value(current, key):
            issues.append(f"{key}: {source.get(key)} → {current.get(key)}")
    effects = None
    for req in manifest["requirements"]:
        kind, name = req["kind"], req["name"]
        if kind == "asset" and share_path_allowed(".local/share/" + name):
            if any((root / name).exists() for root in
                   (HOME / ".local/share", Path("/usr/local/share"), Path("/usr/share"))):
                continue
            if name.startswith("plasma/plasmoids/"):
                plugin = name.removeprefix("plasma/plasmoids/")
                if _safe_asset_name(plugin) and any(
                        (root / "plasma/applets" / (plugin + ".so")).is_file()
                        for root in plugin_roots(current)):
                    continue
        if kind == "style" and name.lower() in {s.lower() for s in styles}:
            continue
        if kind == "font" and selected_font_files(name):
            continue
        if kind == "effect":
            if native_effect_available(name, current):
                continue
            if effects is None:
                effects = ""
                for command in ("qdbus6", "qdbus", "qdbus-qt6"):
                    if shutil.which(command):
                        effects = _run_cmd([command, "org.kde.KWin", "/Effects",
                                            "org.kde.kwin.Effects.listOfEffects"], 10) or ""
                        break
            if name in {line.strip() for line in effects.splitlines()}:
                continue
            # Older configs may retain a redundant pre-KWin-6 key. Only ignore
            # it when the design also explicitly requires its available successor.
            successor = name.removeprefix("kwin4_effect_")
            if (successor != name and successor in effects.splitlines()
                    and {"kind": "effect", "name": successor} in manifest["requirements"]):
                continue
        if kind == "decoration" and _safe_asset_name(name):
            roots = plugin_roots(current)
            filenames = [name + ".so", name.rsplit(".", 1)[-1] + "decoration.so"]
            if any((root / folder / filename).is_file()
                   for root in roots for folder in ("org.kde.kdecoration3", "org.kde.kdecoration2") for filename in filenames):
                continue
        issues.append(kind + ": " + name)
    return issues


def plasma_version(value: str):
    """Compare upstream versions, ignoring a distro's epoch/release suffix."""
    match = re.match(r"^(?:\d+:)?(\d+)\.(\d+)(?:\.(\d+))?(?:[-+~.]|$)", value)
    return tuple(int(v or 0) for v in match.groups()) if match else None


def desktop_setup(manifest: dict, current: dict) -> dict:
    """Read-only repository preflight. Commands are local constants, never payload data.

    Only missing desktops are installed here. Upgrades remain suggestions so a
    theme import cannot silently upgrade a whole distribution or downgrade KDE.
    """
    result = {"notes": [], "command": None}
    if current.get("plasma") == manifest["profile"].get("plasma"):
        return result
    de = _current_lang == "de"
    def note(german, english):
        result["notes"].append(german if de else english)
    try:
        release = platform.freedesktop_os_release()
        distro = release.get("ID", "")
        if "arch" in release.get("ID_LIKE", "").split():
            distro = "arch"
    except OSError:
        distro = ""
    if Path("/run/ostree-booted").exists():
        note("Fedora Atomic: KDE benötigt einen eigenen Umstellungsweg (Kinoite). Keine automatische Systemumstellung.",
             "Fedora Atomic: KDE needs a separate migration to Kinoite. No automatic system rebase.")
        return result
    candidate, command = "", None
    if distro == "ubuntu" and shutil.which("apt-cache") and shutil.which("apt-get"):
        output = _run_cmd(["apt-cache", "policy", "plasma-workspace"], 30) or ""
        match = re.search(r"^\s*Candidate:\s*(\S+)", output, re.M)
        candidate = match.group(1) if match else ""
        # Minimal KDE metapackage; keep the existing desktop and login manager.
        command = ["apt-get", "install", "--no-remove", "--no-install-recommends", "-y",
                   "kde-plasma-desktop", "polkit-kde-agent-1"]
        if not _run_cmd(["apt-cache", "show", "kde-plasma-desktop", "polkit-kde-agent-1"], 30):
            command = None
        # Plasma 5 distributions split the Wayland session into this package.
        if manifest["profile"].get("session") == "wayland" and _run_cmd(
                ["apt-cache", "show", "plasma-workspace-wayland"], 30):
            if command:
                command.append("plasma-workspace-wayland")
    elif distro == "fedora" and shutil.which("dnf"):
        output = _run_cmd(["dnf", "repoquery", "--available", "--latest-limit=1",
                           "--qf", "%{version}\\n", "plasma-workspace"], 60) or ""
        versions = [s.strip() for s in output.splitlines() if plasma_version(s.strip())]
        candidate = max(versions, key=plasma_version) if versions else ""
        command = ["dnf", "install", "-y", "@kde-desktop-environment"]
    elif distro == "arch" and shutil.which("pacman"):
        output = _run_cmd(["pacman", "-Si", "plasma-workspace"], 30) or ""
        match = re.search(r"^Version\s*:\s*(\S+)", output, re.M)
        candidate = match.group(1) if match else ""
        command = ["pacman", "-S", "--needed", "--noconfirm", "plasma-meta"]
        if _run_cmd(["pacman", "-Qu"], 30):
            command = None
            note("Arch: ausstehende Systemupdates zuerst vollständig über die Systemaktualisierung installieren. Keine Plasma-Teilaktualisierung.",
                 "Arch: complete pending system updates through the system updater first. No partial Plasma upgrade.")
    else:
        note("Für dieses System ist keine automatische KDE-Installation hinterlegt.",
             "Automatic KDE installation is not configured for this system.")
        return result
    needed = manifest["profile"].get("plasma", "")
    result.update(candidate=candidate, distro=distro)
    note(f"Plasma: installiert {current.get('plasma') or 'nicht vorhanden'}; benötigt {needed}; Paketquellen {candidate or 'unbekannt'}.",
         f"Plasma: installed {current.get('plasma') or 'missing'}; required {needed}; repositories {candidate or 'unknown'}.")
    note("Paketquellen können veraltet sein. Bei Bedarf über die Systemaktualisierung auffrischen und erneut prüfen.",
         "Repository metadata may be stale. Refresh it through the system updater if needed and check again.")
    if not plasma_version(candidate) or plasma_version(candidate) != plasma_version(needed):
        note("Die benötigte Plasma-Version ist nicht als Paketkandidat verfügbar. Keine fremden Quellen, kein Downgrade und kein automatisches Distributions-Upgrade. Prüfe einen passenden Distributionsstand.",
             "The required Plasma version is not the repository candidate. No third-party repositories, downgrade or automatic distribution upgrade. Check for a suitable distribution release.")
    elif current.get("plasma"):
        installed = plasma_version(current["plasma"])
        if installed and installed < plasma_version(candidate):
            note("Passendes Plasma-Update verfügbar: zuerst mit der Systemaktualisierung installieren, neu anmelden und den Code erneut importieren.",
                 "A matching Plasma update is available: install it through the system updater, log in again, then import the code again.")
        else:
            note("Kein automatischer Plasma-Downgrade. Eine passende KDE-Umgebung ist erforderlich.",
                 "No automatic Plasma downgrade. A matching KDE environment is required.")
    elif command and shutil.which("pkexec"):
        result["command"] = command
        note("KDE zusätzlich installieren; vorhandene Oberfläche bleibt erhalten. Danach abmelden, Plasma auswählen und denselben Code erneut importieren. Systempakete sind nicht Teil des Design-Rollbacks.",
             "Install KDE alongside the existing desktop. Afterwards log out, select Plasma and import the same code again. System packages are not covered by design rollback.")
    else:
        note("KDE-Installation nicht verfügbar: Paket oder Administrator-Authentifizierung fehlt.",
             "KDE installation unavailable: package or administrator authentication missing.")
    return result


def extension_preflight(path: Path, current: dict):
    """Inspect the bundled versions, without executing scripts or trusting URLs."""
    rows, issues = [], []
    prefixes = ("plasma/plasmoids", "plasma/wallpapers", "kwin/scripts", "kwin/effects")
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            rel = member.name.removeprefix("home/.local/share/")
            base = next((p for p in prefixes if rel.startswith(p + "/")), None)
            if not base or not rel.endswith("/metadata.json") or rel.count("/") != base.count("/") + 2:
                continue
            if member.size > 256000 or not member.isfile():
                raise ValueError("Invalid extension metadata")
            data = json.load(archive.extractfile(member))
            if not isinstance(data, dict) or not isinstance(data.get("KPlugin", {}), dict):
                raise ValueError("Invalid extension metadata")
            name = rel[len(base) + 1:].split("/")[0]
            version = str(data.get("KPlugin", {}).get("Version", "unknown"))[:80]
            minimum = str(data.get("X-Plasma-API-Minimum-Version", ""))
            local_version = "not installed / nicht installiert"
            for root in (HOME / ".local/share", Path("/usr/local/share"), Path("/usr/share")):
                local = root / rel
                if local.is_file():
                    try:
                        if local.stat().st_size <= 256000:
                            local_version = str(json.loads(local.read_text()).get("KPlugin", {}).get("Version", "unknown"))[:80]
                    except (ValueError, OSError, AttributeError):
                        local_version = "unknown"
                    break
            rows.append(f"{base}/{name}: {local_version} → {version} (bundled / mitgeliefert)")
            if minimum and (not plasma_version(minimum) or not plasma_version(current.get("plasma", ""))
                            or plasma_version(current["plasma"]) < plasma_version(minimum)):
                issues.append(f"{name}: Plasma minimum / mindestens {minimum[:80]}")
    return rows, issues


def desktop_transaction_preview(command: list[str]) -> str:
    """Ask the native solver without elevation or any package installation."""
    if command == ["pacman", "-Fy"]:
        return "Nur Dateiindex der konfigurierten Paketquellen aktualisieren; keine Pakete installieren. / Refresh repository file indexes only; no packages installed."
    manager = command[0]
    args = [arg for arg in command if arg not in ("-y", "--noconfirm")]
    if manager == "apt-get":
        args.insert(1, "--simulate")
    elif manager == "dnf":
        args.insert(1, "--assumeno")
    elif manager == "pacman":
        args.extend(["--print", "--print-format", "%n %v"])
    else:
        raise ValueError("Unsupported package manager")
    result = subprocess.run(args, capture_output=True, text=True, timeout=180,
                            env={**os.environ, "LC_ALL": "C"})
    output = result.stdout + "\n" + result.stderr
    if manager == "dnf":
        valid = result.returncode in (0, 1) and "Transaction Summary:" in output and "Operation aborted" in output
    else:
        valid = result.returncode == 0 and bool(result.stdout.strip())
    if not valid:
        raise ValueError("Package transaction could not be previewed; nothing installed.\n" + output[-2000:])
    # Preserve the transaction summary and tail of the package list in the UI.
    prefix = "[Auszug: letzte 12000 Zeichen / Excerpt: last 12000 characters]\n" if len(output) > 12000 else ""
    return prefix + output[-12000:]


def native_extension_plan(manifest: dict, current: dict, styles: list[str], issues: list[str]):
    """Resolve providers from this machine's repositories, never source package names.

    File indexes are required on apt/pacman. A missing/ambiguous provider cannot
    be replaced with a guessed package or an untrusted build script.
    """
    result = {"command": None, "notes": [], "providers": []}
    if not package_profile_compatible(manifest["profile"], current):
        result["notes"].append("Zuerst die Plasma-Version angleichen; die Bildschirm-Anordnung verhindert keine Paketsuche. / Match the Plasma version first; screen layout does not block package lookup.")
        return result
    if not shutil.which("pkexec"):
        result["notes"].append("Administratorfreigabe (pkexec) ist nicht verfügbar. / Administrator authentication (pkexec) is unavailable.")
        return result
    if Path("/run/ostree-booted").exists():
        return result
    try:
        system = platform.freedesktop_os_release()
    except OSError:
        return result
    distro = system.get("ID", "")
    if "arch" in system.get("ID_LIKE", "").split():
        distro = "arch"
    manager = {"ubuntu": "apt-get", "debian": "apt-get", "fedora": "dnf", "arch": "pacman"}.get(distro)
    if not manager or not shutil.which(manager):
        return result
    requested = [r for r in manifest["requirements"] if (r["kind"] in ("effect", "decoration")
                 or (r["kind"] == "asset" and r["name"].startswith("plasma/plasmoids/")))
                 and r["kind"] + ": " + r["name"] in issues]
    if not requested:
        return result
    if manager == "apt-get" and (not shutil.which("apt-file") or not any(Path("/var/lib/apt/lists").glob("*Contents*"))):
        result["notes"].append("Zuerst apt-file installieren und Paket-/Dateiindizes aktualisieren; danach Code erneut prüfen / First install apt-file and refresh repository/file indexes, then check the code again.")
        result["command"] = ["apt-get", "install", "--no-remove", "-y", "apt-file"]
        result["prepare_index"] = "apt"
        return result
    if manager == "pacman" and not any(Path("/var/lib/pacman/sync").glob("*.files")):
        result["command"] = ["pacman", "-Fy"]
        result["prepare_index"] = "pacman"
        result["notes"].append("Zuerst Paket-Dateiindex aktualisieren, danach Code erneut prüfen / Refresh the repository file index first, then check the code again.")
        return result
    if manager == "pacman" and _run_cmd(["pacman", "-Qu"], 30):
        result["notes"].append("Arch: zuerst alle Systemupdates installieren / Complete system updates first.")
        return result
    major = str(plasma_version(current["plasma"])[0])
    packages = set()
    for req in requested[:32]:
        name = req["name"]
        if req["kind"] == "asset":
            name = name.removeprefix("plasma/plasmoids/")
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,159}", name):
            result["notes"].append("Invalid native plugin identifier")
            continue
        if req["kind"] == "asset":
            folders = ["plasma/applets"]
            files = [name + ".so"]
        elif req["kind"] == "decoration":
            folders = ["org.kde.kdecoration2", "org.kde.kdecoration3"]
            files = [name + ".so", name.rsplit(".", 1)[-1] + "decoration.so"]
        else:
            folders = ["kwin/effects/plugins", "kwin-x11/effects/plugins"]
            files = [name + ".so", "kwin_effect_" + name + ".so", "kwin4_effect_" + name + ".so"]
        pattern = r"/qt" + major + r"/plugins/(" + "|".join(re.escape(f) for f in folders) + r")/(" + "|".join(re.escape(f) for f in files) + r")$"
        if manager == "apt-get":
            output = _run_cmd(["apt-file", "search", "--package-only", "--regexp", pattern], 45) or ""
        elif manager == "pacman":
            output = _run_cmd(["pacman", "-Fqx", pattern], 45) or ""
        else:
            globs = ["*/qt" + major + "/plugins/" + folder + "/" + file for folder in folders for file in files]
            # --whatprovides consumes one filter; extra positional patterns
            # would constrain package names instead of adding file alternatives.
            output = "\n".join(_run_cmd(["dnf", "repoquery", "--available", "--qf", "%{name}\\n",
                                          "--whatprovides", glob], 60) or "" for glob in globs)
        candidates = set()
        for line in output.splitlines():
            package = line.strip()
            if manager == "pacman" and package.count("/") == 1:
                package = package.split("/", 1)[1]
            if re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9+_.-]{0,159}", package):
                candidates.add(package)
        if len(candidates) == 1:
            package = candidates.pop()
            packages.add(package)
            result["providers"].append(f"{req['kind']}: {name} → {package}")
        else:
            result["notes"].append(f"{name}: " + ("multiple providers / mehrere Anbieter: " + ", ".join(sorted(candidates))
                                                 if candidates else "no verified repository provider / kein bestätigtes Paket (Dateiindex prüfen)."))
    if len(requested) > 32:
        result["notes"].append("Only the first 32 native requirements were queried.")
    if packages:
        prefix = {"apt-get": ["apt-get", "install", "--no-remove", "-y"],
                  "dnf": ["dnf", "install", "-y"],
                  "pacman": ["pacman", "-S", "--needed", "--noconfirm"]}[manager]
        result["command"] = prefix + sorted(packages)
    return result


def design_install_plan(manifest: dict, current: dict, styles: list[str]):
    """A deliberately small local package mapping, never an archive command.

    Plasma 5 and unknown native effects require manual setup. Installing a
    different desktop version/repository is outside the design import.
    """
    if not package_profile_compatible(manifest["profile"], current):
        return None
    if not current["plasma"].startswith("6.") or not shutil.which("pkexec"):
        return None
    missing = any(r["kind"] == "style" and r["name"].lower() in {"kvantum", "kvantum-dark"}
                  and r["name"].lower() not in {s.lower() for s in styles}
                  for r in manifest["requirements"])
    if not missing:
        return None
    if shutil.which("pacman"):
        return ("pacman", "kvantum", ["pacman", "-Si", "kvantum"],
                ["pacman", "-S", "--needed", "--noconfirm", "kvantum"])
    if shutil.which("apt-get") and shutil.which("apt-cache"):
        return ("apt", "qt6-style-kvantum", ["apt-cache", "show", "qt6-style-kvantum"],
                ["apt-get", "install", "-y", "qt6-style-kvantum"])
    if shutil.which("dnf"):
        return ("dnf", "kvantum", ["dnf", "repoquery", "--available", "kvantum"],
                ["dnf", "install", "-y", "kvantum"])
    return None


def safe_extract(archive: tarfile.TarFile, destination: Path):
    """Reject escapes, special files and unsafe links on every Python version.

    Write regular files first, links last, so an archive cannot create a link
    and subsequently write through it. Also used by private backup restores.
    """
    links, names, total = [], set(), 0
    for member in archive:
        name = member.name.rstrip("/")
        parts = name.split("/")
        if (not name or any(p in ("", ".", "..") for p in parts)
                or "\\" in name or "\x00" in name or name in names):
            raise ValueError("Unsafe or duplicate archive path")
        names.add(name)
        total += member.size
        if len(names) > SHARE_FILE_LIMIT + 1 or total > 4_000_000_000:
            raise ValueError("Archive exceeds extraction limits")
        target = destination / name
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
        elif member.isfile():
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            target.chmod(member.mode & 0o777)
        elif member.issym() or member.islnk():
            links.append((member, target))
        else:
            raise ValueError("Unsupported archive member")
    for member, target in links:
        if target.exists() or target.is_symlink():
            raise ValueError("Archive link conflicts with another file")
        link = member.linkname
        if os.path.isabs(link) or "\\" in link:
            raise ValueError("External archive link rejected")
        resolved = ((target.parent if member.issym() else destination) / link).resolve()
        if not resolved.is_relative_to(destination.resolve()):
            raise ValueError("External archive link rejected")
        target.parent.mkdir(parents=True, exist_ok=True)
        if member.issym():
            target.symlink_to(link)
        elif resolved.is_file():
            shutil.copyfile(resolved, target)
        else:
            raise ValueError("Invalid archive hard link")


class ShareWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    ready = pyqtSignal(str, object)
    failed = pyqtSignal(str)

    def __init__(self, screens, code="", dest=None, styles=None, recheck=False):
        super().__init__()
        self.screens, self.code, self.dest = screens, code, dest
        self.styles = styles or []
        self.recheck = recheck

    def run(self):
        try:
            if self.dest is not None:
                if not self.recheck:
                    download_design(self.code, self.dest, self.progress.emit)
                manifest = inspect_public_archive(self.dest)
                current = desktop_profile(self.screens)
                issues = compatibility_issues(manifest, current, self.styles)
                extensions, extension_issues = extension_preflight(self.dest, current)
                issues.extend(extension_issues)
                setup = desktop_setup(manifest, current)
                if setup.get("command"):
                    try:
                        setup["preview"] = desktop_transaction_preview(setup["command"])
                    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                        setup["command"] = None
                        setup["notes"].append(str(error))
                native = native_extension_plan(manifest, current, self.styles, issues)
                if native.get("command"):
                    try:
                        native["preview"] = desktop_transaction_preview(native["command"])
                    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                        native["command"] = None
                        native["notes"].append(str(error))
                self.ready.emit(str(self.dest), {"manifest": manifest, "issues": issues,
                                "setup": setup, "extensions": extensions, "native": native, "styles": self.styles,
                                "plan": design_install_plan(manifest, current, self.styles)})
            else:
                with tempfile.TemporaryDirectory(prefix="sdd-share-") as tmp:
                    root = Path(tmp)
                    manifest = public_design(root, self.screens, self.log.emit)
                    path = root / "design.sdd"
                    with tarfile.open(path, "w:gz") as archive:
                        for rel in manifest["paths"]:
                            archive.add(root / "home" / rel, arcname="home/" + rel,
                                        recursive=False, filter=public_tar_metadata)
                        data = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
                        info = tarfile.TarInfo("manifest.json")
                        info.size = len(data)
                        archive.addfile(info, io.BytesIO(data))
                    inspect_public_archive(path)
                    code = upload_design(path, self.progress.emit)
                    self.ready.emit(code, {"manifest": manifest})
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class DesktopSetupWorker(ShareWorker):
    def __init__(self, screens, dest, approved):
        super().__init__(screens, dest=dest)
        self.approved = approved

    def run(self):
        try:
            manifest = inspect_public_archive(self.dest)
            # Recompute after consent; repository changes require a new review.
            plan = desktop_setup(manifest, desktop_profile(self.screens))
            if not plan.get("command") or any(plan.get(k) != self.approved.get(k)
                                              for k in ("command", "candidate", "distro")):
                raise ValueError("Installation plan changed. Import the code again / Installationsplan geändert: Code erneut importieren.")
            command = plan["command"]
            executable = shutil.which(command[0])
            auth = shutil.which("pkexec")
            if not executable or not auth:
                raise ValueError("Package manager or administrator authentication unavailable")
            # Ubuntu debconf must not wait for an invisible terminal. Keep the
            # existing login manager by installing without recommended packages.
            args = [auth, executable, *command[1:]]
            if command[0] == "apt-get":
                args = [auth, "/usr/bin/env", "DEBIAN_FRONTEND=noninteractive", executable, *command[1:]]
            self.log.emit(shlex.join(command))
            # Never timeout/kill a package transaction mid-write. Closing the
            # application is already prohibited while its worker is running.
            result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True)
            if result.returncode:
                raise ValueError("KDE installation failed or was cancelled. System packages may have changed.\n" + result.stderr[-4000:])
            if not desktop_profile(self.screens).get("plasma"):
                raise ValueError("Package transaction finished, but Plasma was not detected. Check the system package manager.")
            self.ready.emit(str(self.dest), {"manifest": manifest, "desktop_installed": True})
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class NativeInstallWorker(ShareWorker):
    def __init__(self, screens, dest, styles, approved):
        super().__init__(screens, dest=dest, styles=styles)
        self.approved = approved

    def run(self):
        try:
            manifest = inspect_public_archive(self.dest)
            current = desktop_profile(self.screens)
            issues = compatibility_issues(manifest, current, self.styles)
            plan = native_extension_plan(manifest, current, self.styles, issues)
            if not plan["command"] or any(plan[k] != self.approved.get(k) for k in ("command", "providers")):
                raise ValueError("Native package providers changed. Review the import again.")
            executable, auth = shutil.which(plan["command"][0]), shutil.which("pkexec")
            if not executable or not auth:
                raise ValueError("Package manager or administrator authentication missing")
            args = [auth, executable, *plan["command"][1:]]
            if plan["command"][0] == "apt-get":
                args = [auth, "/usr/bin/env", "DEBIAN_FRONTEND=noninteractive", executable, *plan["command"][1:]]
            self.log.emit(shlex.join(plan["command"]))
            result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True)
            if result.returncode:
                raise ValueError("Native package installation failed/cancelled; packages may have changed.\n" + result.stderr[-4000:])
            if plan.get("prepare_index") == "apt":
                result = subprocess.run([auth, executable, "update"], stdin=subprocess.DEVNULL,
                                        capture_output=True, text=True)
                if result.returncode:
                    raise ValueError("File index refresh failed; apt-file may already be installed.\n" + result.stderr[-4000:])
            self.ready.emit(str(self.dest), {"manifest": manifest, "native_installed": True,
                                            "prepare_index": bool(plan.get("prepare_index"))})
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class DesignInstallWorker(ShareWorker):
    def run(self):
        try:
            manifest = inspect_public_archive(self.dest)
            current = desktop_profile(self.screens)
            plan = design_install_plan(manifest, current, self.styles)
            if plan is None:
                raise ValueError("No supported package installation available")
            manager, package, query, command = plan
            if not _run_cmd(query, 60):
                raise ValueError(f"{package}: not available in the configured {manager} repositories")
            self.log.emit(f"{manager}: {package}")
            executable = shutil.which(command[0])
            if not executable:
                raise ValueError("Package manager is unavailable")
            result = subprocess.run([shutil.which("pkexec"), executable, *command[1:]],
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True)
            if result.returncode:
                raise ValueError("Package installation failed or was cancelled:\n" + result.stderr[-4000:])
            # Discover plugins in a fresh process; Qt caches style factories.
            output = _run_cmd([sys.executable, "-c",
                              "import json; from PyQt6.QtWidgets import QStyleFactory; print(json.dumps(QStyleFactory.keys()))"], 15)
            styles = json.loads(output) if output else self.styles
            self.styles, self.recheck = styles, True
            ShareWorker.run(self)
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


# ----------------------------------------------------------------------------
# Worker-Threads
# ----------------------------------------------------------------------------
class UpdateWorker(QThread):
    """Fragt das neueste GitHub-Release ab und lädt auf Wunsch die neue
    Programmdatei. Bewusst nur Standardbibliothek — keine zusätzliche
    Abhängigkeit und kein Token nötig."""
    checked = pyqtSignal(str, str)      # Tag, Release-Notes
    downloaded = pyqtSignal(str, str)   # Tag, Quelltext
    no_release = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, tag: str = "", timeout: int = 30):
        super().__init__()
        self.tag = tag                  # leer = nur prüfen
        self.timeout = timeout

    def _get(self, url: str, accept: str) -> bytes:
        urls = [url]
        # Temporary rename bridge: both repositories are owned by the same
        # maintainer. Only a missing new endpoint falls back, not arbitrary errors.
        if url.startswith(("https://api.github.com/repos/" + GITHUB_REPO + "/",
                           "https://raw.githubusercontent.com/" + GITHUB_REPO + "/")):
            urls.append(url.replace(GITHUB_REPO, LEGACY_GITHUB_REPO, 1))
        for index, endpoint in enumerate(urls):
            req = urllib.request.Request(endpoint, headers={
                "Accept": accept, "User-Agent": f"{APP_NAME}/{VERSION}",
            })
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    content = resp.read(MAX_DOWNLOAD + 1)
                    if len(content) > MAX_DOWNLOAD:
                        raise ValueError("Update response too large")
                    return content
            except urllib.error.HTTPError as error:
                if error.code != 404 or index == len(urls) - 1:
                    raise

    def run(self):
        try:
            if not self.tag:
                data = json.loads(self._get(RELEASE_API,
                                            "application/vnd.github+json"))
                tag = str(data.get("tag_name") or "")
                if not tag:
                    self.no_release.emit()
                    return
                self.checked.emit(tag, str(data.get("body") or ""))
            else:
                url = RAW_URL.format(tag=urllib.parse.quote(self.tag, safe=""))
                self.downloaded.emit(
                    self.tag, self._get(url, "text/plain").decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404 and not self.tag:
                self.no_release.emit()      # Repo hat noch kein Release
            else:
                self.failed.emit(f"HTTP {e.code} — {e.reason}")
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")


class BackupWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, dest: str, categories: list[str], with_packages: bool):
        super().__init__()
        self.dest = dest
        self.categories = categories
        self.with_packages = with_packages

    def run(self):
        try:
            paths: list[tuple[str, Path]] = []  # (kategorie, absoluter pfad)
            for cat in self.categories:
                for rel in CATEGORIES[cat]:
                    p = HOME / rel
                    if p.exists():
                        paths.append((cat, p))

            total = len(paths) + (1 if self.with_packages else 0) + 1
            done = 0

            manifest = {
                "app": APP_NAME,
                "version": VERSION,
                "created": datetime.now().isoformat(timespec="seconds"),
                "hostname": socket.gethostname(),
                "user": os.environ.get("USER", ""),
                "categories": self.categories,
                "with_packages": self.with_packages,
                "paths": [str(p.relative_to(HOME)) for _, p in paths],
            }

            with tarfile.open(self.dest, "w:gz") as tar:
                for cat, p in paths:
                    rel = p.relative_to(HOME)
                    self.log.emit(f"  + {rel}")
                    try:
                        tar.add(p, arcname=f"home/{rel}")
                    except (PermissionError, OSError) as e:
                        self.log.emit(f"{T('log_skipped')} ({e})")
                    done += 1
                    self.progress.emit(int(done / total * 100))

                # Die App selbst beilegen: auf dem neuen Gerät genügt dann
                # `tar xzf … app/savedesktopdesign.py` und ein Doppelklick.
                try:
                    tar.add(Path(__file__).resolve(),
                            arcname="app/savedesktopdesign.py")
                    manifest["app_included"] = True
                    self.log.emit(T("log_app_added"))
                except OSError as e:
                    self.log.emit(f"{T('log_skipped')} app ({e})")

                if self.with_packages:
                    self.log.emit(T("log_pkg_creating"))
                    for fname, content in gather_package_lists().items():
                        data = content.encode()
                        info = tarfile.TarInfo(f"packages/{fname}")
                        info.size = len(data)
                        info.mtime = int(datetime.now().timestamp())
                        tar.addfile(info, io.BytesIO(data))
                    done += 1
                    self.progress.emit(int(done / total * 100))

                mdata = json.dumps(manifest, indent=2).encode()
                info = tarfile.TarInfo("manifest.json")
                info.size = len(mdata)
                info.mtime = int(datetime.now().timestamp())
                tar.addfile(info, io.BytesIO(mdata))

            self.progress.emit(100)
            size_mb = Path(self.dest).stat().st_size / 1024 / 1024
            self.finished_ok.emit(f"{self.dest} ({size_mb:.1f} MB)")
        except Exception:
            self.failed.emit(traceback.format_exc())


class RestoreWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal(bool)   # True wenn Paketlisten enthalten
    failed = pyqtSignal(str)

    def __init__(self, archive: str, categories: list[str] | None = None,
                 rollback: bool = True, public: bool = False,
                 screens=None, styles=None):
        super().__init__()
        self.archive = archive
        self.categories = categories   # None = alles aus dem Archiv
        self.rollback = rollback
        self.public = public
        self.screens = screens or []
        self.styles = styles or []

    def run(self):
        try:
            if self.public:
                manifest = inspect_public_archive(Path(self.archive))
                issues = compatibility_issues(manifest, desktop_profile(self.screens), self.styles)
                issues.extend(extension_preflight(Path(self.archive), desktop_profile(self.screens))[1])
                if issues:
                    raise ValueError(T("share_blocked") + "\n".join(issues))
            with tempfile.TemporaryDirectory(prefix="sdd-restore-") as tmp:
                tmpp = Path(tmp)
                self.log.emit(T("log_extracting"))
                with tarfile.open(self.archive, "r:gz") as tar:
                    safe_extract(tar, tmpp)
                self.progress.emit(30)

                src_home = tmpp / "home"
                pkg_dir = tmpp / "packages"
                # Ein reines Paketlisten-Backup (keine Kategorie angehakt) hat
                # kein home/ — das darf den Restore nicht abbrechen.
                if not src_home.exists() and not pkg_dir.exists():
                    self.failed.emit(T("err_invalid_archive"))
                    return

                manifest = {}
                mf = tmpp / "manifest.json"
                if mf.exists():
                    try:
                        manifest = json.loads(mf.read_text())
                    except (ValueError, OSError):
                        manifest = {}

                if manifest.get("public_design") and not self.public:
                    raise ValueError("Public designs must be imported through the Share design tab")

                # Aus dem Manifest wissen wir pfadgenau, was zurückkommt —
                # und können danach filtern. Ohne Manifest (alte Archive)
                # bleibt es beim bisherigen Verhalten: alles.
                rel_paths = manifest.get("paths")
                if rel_paths is None:
                    # Legacy backups have no manifest paths. Limit them to
                    # the paths this application actually backs up.
                    rel_paths = [r for values in CATEGORIES.values() for r in values
                                 if os.path.lexists(src_home / r)]
                allowed = {r for values in CATEGORIES.values() for r in values}
                if not isinstance(rel_paths, list) or not all(
                        isinstance(r, str) and (share_path_allowed(r) if self.public else
                        (r in allowed or (manifest.get("rollback") and share_path_allowed(r))))
                        for r in rel_paths):
                    raise ValueError("Invalid restore paths in manifest")
                if self.categories is not None and rel_paths:
                    wanted = set()
                    for cat in self.categories:
                        wanted.update(CATEGORIES.get(cat, []))
                    rel_paths = [r for r in rel_paths if r in wanted]

                # No writes through existing directory symlinks in the target
                # home. Check before creating the rollback, too.
                for rel in rel_paths:
                    target = HOME / rel
                    if self.public and target.is_symlink() and os.path.isabs(os.readlink(target)):
                        raise ValueError(f"Cannot safely roll back an absolute target symlink: {rel}")
                    for parent in target.parents:
                        if parent == HOME:
                            break
                        if parent.is_symlink():
                            raise ValueError(f"Restore path uses a directory symlink: {rel}")

                if self.public:
                    for rel in rel_paths:
                        if rel in {".config/" + n for n in VISUAL_CONFIGS}:
                            config = src_home / rel
                            if config.stat().st_size > 4_000_000:
                                raise ValueError("Configuration too large")
                            config.write_text(config.read_text(encoding="utf-8").replace(
                                HOME_TOKEN, str(HOME)), encoding="utf-8")

                if src_home.exists():
                    if self.rollback:
                        self.log.emit(T("log_rollback"))
                        saved = make_rollback(rel_paths, self.categories
                                              or manifest.get("categories", []))
                        if saved:
                            self.log.emit(f"  → {saved}")

                    entries = [src_home / r for r in rel_paths]
                    entries = [e for e in entries if os.path.lexists(e)]
                    total = max(len(entries), 1)
                    for i, entry in enumerate(entries, 1):
                        self._copy_into_home(entry, src_home)
                        self.progress.emit(30 + int(i / total * 60))

                # Paketlisten ins Home legen, damit sie nach dem Restore greifbar sind
                has_packages = False
                if pkg_dir.exists():
                    dest = HOME / ".savedesktopdesign-packages"
                    if dest.is_symlink():
                        raise ValueError("Package directory must not be a symlink")
                    dest.mkdir(exist_ok=True)
                    for f in pkg_dir.iterdir():
                        if f.name not in {"pacman-explicit.txt", "pacman-foreign.txt",
                                          "pacman-repos.txt", "apt-manual.txt",
                                          "dnf-packages.txt", "flatpak.txt"} or not f.is_file() or f.is_symlink():
                            raise ValueError("Unexpected package list")
                        if (dest / f.name).is_symlink():
                            (dest / f.name).unlink()
                        shutil.copy2(f, dest / f.name)
                    has_packages = True
                    self.log.emit(T("log_pkglists_saved") + str(dest))

                if src_home.exists():
                    self._post_restore()

                self.progress.emit(100)
                self.finished_ok.emit(has_packages)
        except Exception:
            self.failed.emit(traceback.format_exc())

    def _post_restore(self):
        """Schrift-Cache, KWin und sycoca auffrischen. Fehlt eines der
        Werkzeuge, ist das kein Grund, den bereits erfolgreichen Restore
        als fehlgeschlagen zu melden — daher jeder Schritt einzeln gekapselt."""
        if shutil.which("fc-cache"):
            self.log.emit(T("log_fontcache"))
            try:
                subprocess.run(["fc-cache", "-f"], capture_output=True, timeout=300)
            except (OSError, subprocess.SubprocessError) as e:
                self.log.emit(f"{T('log_skipped')} fc-cache ({e})")

        # KWin & Co. zwingen, die restaurierten Configs sofort zu laden —
        # sonst überschreibt die laufende Sitzung sie beim Abmelden wieder
        self.log.emit(T("log_kwin_reload"))
        for qdbus in ("qdbus6", "qdbus", "qdbus-qt6", "qdbus-qt5"):
            if shutil.which(qdbus):
                try:
                    subprocess.run([qdbus, "org.kde.KWin", "/KWin", "reconfigure"],
                                   capture_output=True, timeout=30)
                except (OSError, subprocess.SubprocessError) as e:
                    self.log.emit(f"{T('log_skipped')} {qdbus} ({e})")
                break
        for sycoca in ("kbuildsycoca6", "kbuildsycoca5"):
            if shutil.which(sycoca):
                try:
                    subprocess.run([sycoca], capture_output=True, timeout=120)
                except (OSError, subprocess.SubprocessError) as e:
                    self.log.emit(f"{T('log_skipped')} {sycoca} ({e})")
                break

    def _copy_into_home(self, entry: Path, src_root: Path):
        rel = entry.relative_to(src_root)
        target = HOME / rel
        self.log.emit(f"  → {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        self._merge(entry, target)

    def _remove_existing(self, dst: Path):
        """Vorhandenes Ziel (Datei, Symlink oder Ordner) entfernen."""
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    def _merge(self, src: Path, dst: Path):
        """Rekursives Kopieren, das vorhandene Dateien/Symlinks ersetzt.
        Einzelne Fehler werden protokolliert, brechen aber nicht alles ab."""
        try:
            if src.is_symlink():
                link = os.readlink(src)
                if os.path.lexists(dst):
                    self._remove_existing(dst)
                os.symlink(link, dst)
            elif src.is_dir():
                if os.path.lexists(dst) and not (dst.is_dir() and not dst.is_symlink()):
                    self._remove_existing(dst)
                dst.mkdir(parents=True, exist_ok=True)
                for child in src.iterdir():
                    self._merge(child, dst / child.name)
            else:
                if os.path.lexists(dst):
                    self._remove_existing(dst)
                shutil.copy2(src, dst)
        except OSError as e:
            raise OSError(f"Could not restore {dst}: {e}") from e


# ----------------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------------
class RestoreOptionsDialog(QDialog):
    """Ersetzt die alte Ja/Nein-Rückfrage: welche Kategorien zurück sollen
    und ob vorher der aktuelle Zustand gesichert wird."""

    def __init__(self, parent, cats: list[str], info: str):
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        lay = QVBoxLayout(self)

        head = QLabel(T("msg_confirm_restore"))
        head.setWordWrap(True)
        lay.addWidget(head)
        if info:
            details = QLabel(info)
            details.setWordWrap(True)
            lay.addWidget(details)

        self.checks: dict[str, QCheckBox] = {}
        if cats:
            box = QGroupBox(T("dlg_restore_title"))
            blay = QVBoxLayout(box)
            for cat in cats:
                cb = QCheckBox(T(cat))
                cb.setChecked(True)
                self.checks[cat] = cb
                blay.addWidget(cb)
            lay.addWidget(box)

        self.rollback_cb = QCheckBox(T("cb_rollback"))
        self.rollback_cb.setChecked(True)
        lay.addWidget(self.rollback_cb)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def selected(self) -> list[str]:
        return [c for c, cb in self.checks.items() if cb.isChecked()]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        global _current_lang
        self.settings = QSettings(LEGACY_APP_NAME, LEGACY_APP_NAME)
        _current_lang = detect_language(self.settings)
        self.setWindowIcon(QIcon.fromTheme("preferences-desktop-theme"))
        self.resize(720, 660)
        # Getrennte Referenzen: ein gemeinsames self.worker konnte einen noch
        # laufenden QThread verdrängen -> "QThread: Destroyed while running".
        self.backup_worker = None
        self.restore_worker = None
        self.update_worker = None
        self.silent_worker = None
        self.share_worker = None
        self.action_process = None
        self.share_temp = None
        self._attempted_installs = set()
        self._public_restore = False
        self._last_share_code = self.settings.value("last_share_code", "", type=str)
        self._latest_tag = ""        # zuletzt von GitHub gemeldeter Tag
        self._build_ui()
        if self.settings.value("resume_import_after_login", False, type=bool):
            QTimer.singleShot(500, self._resume_import)
        elif self.settings.value("check_updates_on_start", True, type=bool):
            # Still: ändert nur die Versionsanzeige, öffnet nie einen Dialog.
            QTimer.singleShot(1500, self._silent_check)

    # ---------------- Worker-Verwaltung ----------------
    def _worker_running(self) -> bool:
        return any(w is not None and w.isRunning()
                   for w in (self.backup_worker, self.restore_worker,
                             self.update_worker, self.share_worker))

    def _set_busy(self, busy: bool):
        """Während eines Jobs Buttons und Sprachwahl sperren: ein zweiter
        Worker würde den laufenden Thread verdrängen, ein Sprachwechsel
        würde die Widgets neu bauen, an denen seine Signale hängen."""
        self.backup_btn.setEnabled(not busy)
        self.restore_btn.setEnabled(not busy)
        self.rollback_btn.setEnabled(not busy)
        self.update_btn.setEnabled(not busy)
        self.lang_combo.setEnabled(not busy)
        self.share_export_btn.setEnabled(not busy)
        self.share_import_btn.setEnabled(not busy)
        self.pkg_btn.setEnabled(not busy)
        self.plasma_btn.setEnabled(not busy)

    def closeEvent(self, event):
        if self._worker_running():
            QMessageBox.information(self, APP_NAME, T("msg_busy_close"))
            event.ignore()
            return
        # Die stille Abfrage sperrt nichts, darf aber nicht mitten im Lauf
        # zerstört werden — ihr Timeout begrenzt die Wartezeit auf 8 s.
        if self.silent_worker is not None and self.silent_worker.isRunning():
            self.silent_worker.wait()
        if self.share_temp is not None:
            self.share_temp.cleanup()
        event.accept()

    # ---------------- UI-Aufbau (bei Sprachwechsel neu) ----------------
    def _build_ui(self):
        self.setWindowTitle(f"{APP_NAME} {VERSION} — {T('app_subtitle')}")

        root = QWidget()
        root_lay = QVBoxLayout(root)

        # Sprachauswahl oben rechts
        lang_lay = QHBoxLayout()
        self.update_btn = QPushButton(
            QIcon.fromTheme("system-software-update"), T("btn_update"))
        self.update_btn.clicked.connect(self.check_update)
        lang_lay.addWidget(self.update_btn)
        self.version_label = QLabel()
        lang_lay.addWidget(self.version_label)
        self._apply_version_label()
        lang_lay.addStretch()
        self.autocheck_cb = QCheckBox(T("cb_autocheck"))
        self.autocheck_cb.setChecked(
            self.settings.value("check_updates_on_start", True, type=bool))
        self.autocheck_cb.toggled.connect(
            lambda on: self.settings.setValue("check_updates_on_start", on))
        lang_lay.addWidget(self.autocheck_cb)
        lang_lay.addWidget(QLabel(T("lang_label")))
        self.lang_combo = QComboBox()
        for code, name in LANG_NAMES.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(list(LANG_NAMES).index(_current_lang))
        self.lang_combo.currentIndexChanged.connect(self._change_language)
        lang_lay.addWidget(self.lang_combo)
        root_lay.addLayout(lang_lay)

        tabs = QTabWidget()
        tabs.addTab(self._build_backup_tab(), QIcon.fromTheme("document-save"), T("tab_backup"))
        tabs.addTab(self._build_restore_tab(), QIcon.fromTheme("document-open"), T("tab_restore"))
        tabs.addTab(self._build_share_tab(), QIcon.fromTheme("document-send"), T("tab_share"))
        root_lay.addWidget(tabs)
        self.setCentralWidget(root)

    def _change_language(self):
        global _current_lang
        code = self.lang_combo.currentData()
        if code and code != _current_lang:
            _current_lang = code
            self.settings.setValue("language", code)
            self._build_ui()

    def _build_share_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        title = QLabel(T("share_title"))
        layout.addWidget(title)
        hint = QLabel(T("share_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.share_export_btn = QPushButton(T("share_export"))
        self.share_export_btn.clicked.connect(self.export_code)
        layout.addWidget(self.share_export_btn)
        layout.addWidget(QLabel(T("share_last_code")))
        self.share_code = QLineEdit()
        self.share_code.setReadOnly(True)
        self.share_code.setAccessibleName(T("share_code"))
        self.share_code.setText(getattr(self, "_last_share_code", ""))
        layout.addWidget(self.share_code)
        copy = QPushButton(T("share_copy"))
        copy.setEnabled(bool(self.share_code.text()))
        self.share_code.textChanged.connect(lambda value: copy.setEnabled(bool(value)))
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.share_code.text()))
        layout.addWidget(copy)
        self.share_import_btn = QPushButton(T("share_import"))
        self.share_import_btn.clicked.connect(self.import_code)
        layout.addWidget(self.share_import_btn)
        self.share_progress = QProgressBar()
        layout.addWidget(self.share_progress)
        self.share_log = QTextEdit()
        self.share_log.setReadOnly(True)
        layout.addWidget(self.share_log)
        return widget

    def export_code(self):
        if self._worker_running():
            return
        if QMessageBox.question(self, APP_NAME, T("share_consent"),
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self._start_share(ShareWorker(screen_profile()), "share_upload")

    def import_code(self):
        if self._worker_running():
            return
        code, ok = QInputDialog.getText(self, T("share_import"), T("share_code"),
                                       text=self.settings.value("last_import_code", ""))
        if not ok or not code.strip():
            return
        if not CODE_RE.fullmatch(code.strip()):
            self._share_failed("Invalid SDD1 code / Ungültiger SDD1-Code")
            return
        self.settings.setValue("last_import_code", code.strip())
        self._download_import(code.strip())

    def _resume_import(self):
        self.settings.setValue("resume_import_after_login", False)
        code = self.settings.value("last_import_code", "", type=str)
        if CODE_RE.fullmatch(code) and not self._worker_running():
            self._download_import(code)

    def _download_import(self, code):
        self.settings.setValue("resume_import_after_login", False)
        self._attempted_installs.clear()
        self._clean_share_temp()
        self.share_temp = tempfile.TemporaryDirectory(prefix="sdd-download-")
        dest = Path(self.share_temp.name) / "design.sdd"
        self._start_share(ShareWorker(screen_profile(), code, dest,
                                      QStyleFactory.keys()), "share_download")

    def _start_share(self, worker, message):
        self._set_busy(True)
        self.share_progress.setValue(0)
        if not worker.recheck and not isinstance(worker, (NativeInstallWorker, DesktopSetupWorker, DesignInstallWorker)):
            self.share_log.clear()
        self.share_log.append(T(message))
        self.share_worker = worker
        worker.log.connect(self.share_log.append)
        worker.progress.connect(self.share_progress.setValue)
        # Wait for QThread.finished before enabling controls/replacing the
        # worker reference. queued ready/failed signals store the outcome.
        self._share_outcome = None
        worker.ready.connect(lambda value, details: setattr(self, "_share_outcome", (value, details)))
        worker.failed.connect(lambda error: setattr(self, "_share_outcome", (None, error)))
        worker.finished.connect(self._share_finished)
        worker.start()

    def _share_finished(self):
        self._set_busy(False)
        value, details = self._share_outcome or (None, "No transfer result")
        if value is None:
            self._share_failed(details)
            return
        manifest = details["manifest"]
        self.share_log.append(f"{T('share_details')}: {len(manifest['paths'])} files")
        self.share_log.append(f"{T('share_omitted')}: {manifest.get('omitted_settings', 0)} settings")
        if value.startswith("SDD1:"):
            self._last_share_code = value
            self.settings.setValue("last_share_code", value)
            self.share_code.setText(value)
            self.share_log.append(T("share_ready"))
            self.share_progress.setValue(100)
            return
        if details.get("desktop_installed"):
            self.settings.setValue("resume_import_after_login", True)
            message = T("share_desktop_done")
            self.share_log.append(message)
            QMessageBox.information(self, APP_NAME, message)
            self._clean_share_temp()
            return
        if details.get("native_installed"):
            self._start_share(ShareWorker(screen_profile(), dest=Path(value),
                              styles=QStyleFactory.keys(), recheck=True), "share_download")
            return
        for row in details.get("extensions", []):
            self.share_log.append(row)
        setup = details.get("setup", {})
        native = details.get("native", {})
        if details.get("plan") and tuple(details["plan"][3]) in self._attempted_installs:
            details["plan"] = None
        if native.get("command") and tuple(native["command"]) in self._attempted_installs:
            self.settings.setValue("resume_import_after_login", True)
            native["command"] = None
            native.setdefault("notes", []).append(
                "Die Installation wurde bereits ausgeführt, aber die Komponente ist noch nicht verfügbar. "
                "Bitte nach einem neuen Plasma-Login dieses Programm öffnen: Der Import wird automatisch fortgesetzt. / "
                "After a new Plasma login, reopen this app to resume the import automatically.")
        for note in setup.get("notes", []):
            self.share_log.append(note)
        if details["issues"]:
            message = T("share_blocked") + "\n".join(details["issues"])
            if setup.get("notes"):
                message += "\n\n" + "\n".join(setup["notes"])
            if native.get("notes"):
                message += "\n\n" + "\n".join(native["notes"])
            self.share_log.append(message)
            if setup.get("command"):
                question = ("Für dieses Design fehlt eine passende KDE-Plasma-Installation. "
                            "SaveYourKDEDesign kann die benötigten Pakete jetzt installieren. / "
                            "This design needs a matching KDE Plasma installation. "
                            "SaveYourKDEDesign can install the required packages now.")
                dialog = QMessageBox(self)
                dialog.setWindowTitle(APP_NAME)
                dialog.setText(question)
                dialog.setDetailedText(message + "\n\n" + shlex.join(setup["command"])
                                       + "\n\n" + setup.get("preview", ""))
                dialog.setInformativeText("Paketplan unter Details prüfen / Review the package plan under Details")
                dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                dialog.setDefaultButton(QMessageBox.StandardButton.No)
                if dialog.exec() == QMessageBox.StandardButton.Yes:
                    self._start_share(DesktopSetupWorker(screen_profile(), Path(value), setup), "share_desktop_working")
                    return
            if native.get("command"):
                dialog = QMessageBox(self)
                dialog.setWindowTitle(APP_NAME)
                dialog.setText("Benötigte KDE-Erweiterungen wurden in deinen Paketquellen gefunden. Jetzt installieren? / "
                               "Required KDE extensions were found in your repositories. Install them now?\n\n"
                               + ("\n".join(native["providers"]) or "Paket-Dateiindex vorbereiten / Prepare package file index"))
                dialog.setInformativeText("Nach der Installation prüft das Programm automatisch weiter.")
                dialog.setDetailedText(message + "\n\n" + shlex.join(native["command"])
                                       + "\n\n" + native.get("preview", ""))
                dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                dialog.setDefaultButton(QMessageBox.StandardButton.No)
                if dialog.exec() == QMessageBox.StandardButton.Yes:
                    self._attempted_installs.add(tuple(native["command"]))
                    self._start_share(NativeInstallWorker(screen_profile(), Path(value), QStyleFactory.keys(), native), "share_installing")
                    return
            if details.get("plan"):
                question = ("Für das Design fehlt der Oberflächenstil " + details["plan"][1]
                            + ". Jetzt installieren?\n\nNach der Installation wird automatisch weitergeprüft.")
                if QMessageBox.question(self, APP_NAME, question,
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                    self._attempted_installs.add(tuple(details["plan"][3]))
                    self._start_share(DesignInstallWorker(screen_profile(), dest=Path(value),
                                                          styles=QStyleFactory.keys()), "share_installing")
                    return
            screen_issue = next((row for row in details["issues"] if row.startswith("screens:")), None)
            other_issues = [row for row in details["issues"] if not row.startswith("screens:")]
            if screen_issue and not other_issues and shutil.which("kcmshell6"):
                dialog = QMessageBox(self)
                dialog.setWindowTitle(APP_NAME)
                dialog.setIcon(QMessageBox.Icon.Information)
                dialog.setText("Die benötigten Erweiterungen sind geprüft. Jetzt muss noch die Bildschirm-Anordnung zum Design passen.")
                dialog.setInformativeText("Öffne die Anzeige-Einstellungen. Sobald du sie schließt, prüft SaveYourKDEDesign automatisch erneut.")
                open_button = dialog.addButton("Anzeige-Einstellungen öffnen", QMessageBox.ButtonRole.AcceptRole)
                dialog.addButton(QMessageBox.StandardButton.Cancel)
                dialog.setDetailedText(message)
                dialog.exec()
                if dialog.clickedButton() is open_button:
                    self._open_screen_settings_and_recheck(Path(value))
                    return
            else:
                dialog = QMessageBox(self)
                dialog.setWindowTitle(APP_NAME)
                dialog.setIcon(QMessageBox.Icon.Warning)
                dialog.setText("Einige benötigte Erweiterungen konnten in den eingerichteten Paketquellen nicht eindeutig gefunden werden.")
                dialog.setInformativeText("Unter „Details“ steht, welche Komponente fehlt. Es wurden keine Design-Einstellungen geändert.")
                dialog.setDetailedText(message)
                dialog.setStandardButtons(QMessageBox.StandardButton.Close)
                dialog.exec()
            self._clean_share_temp()
            return
        review = T("share_review") + "\n\n" + T("share_extensions") + "\n" + "\n".join(details.get("extensions", [])) + "\n\n" + T("share_apply")
        if QMessageBox.question(self, APP_NAME, review,
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            self._clean_share_temp()
            return
        self._start_restore(value, None, True, public=True, styles=details.get("styles"))

    def _open_screen_settings_and_recheck(self, archive: Path):
        executable = shutil.which("kcmshell6")
        if not executable:
            return
        self._set_busy(True)
        self.action_process = QProcess(self)
        self.action_process.finished.connect(
            lambda *_: self._start_share(ShareWorker(screen_profile(), dest=archive,
                                      styles=QStyleFactory.keys(), recheck=True), "share_download"))
        self.action_process.errorOccurred.connect(lambda *_: self._screen_settings_failed())
        self.action_process.start(executable, ["kcm_kscreen"])

    def _screen_settings_failed(self):
        self._set_busy(False)
        self._clean_share_temp()
        QMessageBox.warning(self, APP_NAME, "Die Anzeige-Einstellungen konnten nicht geöffnet werden.")

    def _clean_share_temp(self):
        if self.share_temp is not None:
            self.share_temp.cleanup()
            self.share_temp = None

    def _share_failed(self, error):
        self._set_busy(False)
        self.share_log.append(str(error))
        self._clean_share_temp()
        QMessageBox.warning(self, T("share_error"), str(error))

    # ---------------- Backup-Tab ----------------
    def _build_backup_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        title = QLabel(T("backup_title"))
        f = QFont(); f.setPointSize(12); f.setBold(True)
        title.setFont(f)
        title.setWordWrap(True)
        lay.addWidget(title)

        box = QGroupBox(T("choose_box"))
        blay = QVBoxLayout(box)
        self.cat_checks: dict[str, QCheckBox] = {}
        for cat_id in CATEGORIES:
            cb = QCheckBox(T(cat_id))
            cb.setChecked(True)
            self.cat_checks[cat_id] = cb
            blay.addWidget(cb)
        self.pkg_check = QCheckBox(T("cat_packages"))
        self.pkg_check.setChecked(True)
        blay.addWidget(self.pkg_check)
        lay.addWidget(box)

        self.backup_btn = QPushButton(QIcon.fromTheme("document-save"), T("btn_backup"))
        self.backup_btn.setMinimumHeight(42)
        self.backup_btn.clicked.connect(self.start_backup)
        lay.addWidget(self.backup_btn)

        self.backup_progress = QProgressBar()
        lay.addWidget(self.backup_progress)

        self.backup_log = QTextEdit()
        self.backup_log.setReadOnly(True)
        lay.addWidget(self.backup_log)
        return w

    def start_backup(self):
        if self._worker_running():
            QMessageBox.information(self, APP_NAME, T("msg_busy"))
            return
        cats = [c for c, cb in self.cat_checks.items() if cb.isChecked()]
        if not cats and not self.pkg_check.isChecked():
            QMessageBox.warning(self, APP_NAME, T("msg_select_one"))
            return
        default = str(HOME / f"plasma-design-{datetime.now():%Y-%m-%d}.tar.gz")
        dest, _ = QFileDialog.getSaveFileName(
            self, T("dlg_save"), default, T("dlg_archive_filter"))
        if not dest:
            return
        if not dest.endswith(".tar.gz"):
            dest += ".tar.gz"

        self._set_busy(True)
        self.backup_progress.setValue(0)
        self.backup_log.clear()
        self.backup_log.append(T("log_creating"))
        self.backup_worker = BackupWorker(dest, cats, self.pkg_check.isChecked())
        self.backup_worker.log.connect(self.backup_log.append)
        self.backup_worker.progress.connect(self.backup_progress.setValue)
        self.backup_worker.finished_ok.connect(self._backup_done)
        self.backup_worker.failed.connect(self._backup_fail)
        self.backup_worker.start()

    def _backup_done(self, info: str):
        self._set_busy(False)
        self.backup_log.append(T("done_prefix") + info)
        QMessageBox.information(self, APP_NAME, f"{T('msg_backup_done')}\n{info}")

    def _backup_fail(self, err: str):
        self._set_busy(False)
        self.backup_log.append(T("err_prefix") + err)
        QMessageBox.critical(self, APP_NAME, T("msg_backup_failed"))

    # ---------------- Restore-Tab ----------------
    def _build_restore_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        title = QLabel(T("restore_title"))
        f = QFont(); f.setPointSize(12); f.setBold(True)
        title.setFont(f)
        title.setWordWrap(True)
        lay.addWidget(title)

        hint = QLabel(T("restore_hint"))
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.restore_btn = QPushButton(QIcon.fromTheme("document-open"), T("btn_restore"))
        self.restore_btn.setMinimumHeight(42)
        self.restore_btn.clicked.connect(self.start_restore)
        lay.addWidget(self.restore_btn)

        self.pkg_btn = QPushButton(QIcon.fromTheme("system-software-install"), T("btn_packages"))
        # IMMER aktiv: ein Klick muss garantiert eine sichtbare Reaktion erzeugen.
        # Fehlen Paketlisten, sagt _install_packages es per Dialog — nie stumm.
        self.pkg_btn.setEnabled(True)
        self.pkg_btn.clicked.connect(self.install_packages)
        lay.addWidget(self.pkg_btn)

        self.rollback_btn = QPushButton(
            QIcon.fromTheme("edit-undo"), T("btn_rollback"))
        # Immer aktiv — fehlt die Sicherungskopie, sagt es der Dialog.
        self.rollback_btn.clicked.connect(self.restore_rollback)
        lay.addWidget(self.rollback_btn)

        self.plasma_btn = QPushButton(QIcon.fromTheme("system-reboot"), T("btn_plasma"))
        self.plasma_btn.setEnabled(False)
        self.plasma_btn.clicked.connect(self.restart_plasma)
        lay.addWidget(self.plasma_btn)

        self.restore_progress = QProgressBar()
        lay.addWidget(self.restore_progress)

        self.restore_log = QTextEdit()
        self.restore_log.setReadOnly(True)
        lay.addWidget(self.restore_log)
        return w

    def start_restore(self):
        if self._worker_running():
            QMessageBox.information(self, APP_NAME, T("msg_busy"))
            return
        archive, _ = QFileDialog.getOpenFileName(
            self, T("dlg_open"), str(HOME), T("dlg_archive_filter"))
        if not archive:
            return

        # Manifest anzeigen
        info_txt = ""
        cats: list[str] = []
        try:
            with tarfile.open(archive, "r:gz") as tar:
                mf = tar.extractfile("manifest.json")
                if mf:
                    m = json.loads(mf.read())
                    cats = [c for c in m.get("categories", [])
                            if isinstance(c, str) and c in CATEGORIES]
                    info_txt = (f"{T('mf_created')}: {m.get('created')}\n"
                                f"{T('mf_host')}: {m.get('hostname')}\n"
                                f"{T('mf_categories')}: {len(m.get('categories', []))}\n"
                                f"{T('mf_packages')}: "
                                f"{T('yes') if m.get('with_packages') else T('no')}")
        except Exception:
            pass

        dlg = RestoreOptionsDialog(self, cats, info_txt)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = dlg.selected() if cats else None
        if cats and not chosen:
            QMessageBox.warning(self, APP_NAME, T("msg_select_one"))
            return
        self._start_restore(archive, chosen, dlg.rollback_cb.isChecked())

    def _start_restore(self, archive: str, categories, rollback: bool, public: bool = False, styles=None):
        self._set_busy(True)
        self.restore_progress.setValue(0)
        self.restore_log.clear()
        self._public_restore = public
        self.restore_worker = RestoreWorker(archive, categories, rollback, public,
                                            screen_profile(), styles if styles is not None else QStyleFactory.keys())
        self.restore_worker.log.connect(self.restore_log.append)
        self.restore_worker.progress.connect(self.restore_progress.setValue)
        self.restore_worker.finished_ok.connect(self._restore_done)
        self.restore_worker.failed.connect(self._restore_fail)
        if public:
            self.restore_worker.log.connect(self.share_log.append)
            self.restore_worker.progress.connect(self.share_progress.setValue)
        self.restore_worker.start()

    def restore_rollback(self):
        """Zurück auf den Zustand vor der letzten Wiederherstellung.
        Erzeugt bewusst KEINE neue Sicherungskopie — sonst würde das
        Quellarchiv beim Lesen überschrieben."""
        if self._worker_running():
            QMessageBox.information(self, APP_NAME, T("msg_busy"))
            return
        path = rollback_path()
        if not path.is_file():
            QMessageBox.information(self, APP_NAME, T("msg_no_rollback"))
            return
        when = datetime.fromtimestamp(path.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M")
        if QMessageBox.question(
                self, APP_NAME, T("msg_confirm_rollback").format(when=when)
                ) != QMessageBox.StandardButton.Yes:
            return
        self._start_restore(str(path), None, False)

    def _restore_done(self, has_packages: bool):
        self._set_busy(False)
        self.plasma_btn.setEnabled(True)
        # pkg_btn bleibt grundsätzlich aktiv (siehe _build_restore_tab) — nie deaktivieren
        self.restore_log.append(T("log_restored"))
        if self._public_restore:
            self.share_log.append(T("share_complete"))
            self._clean_share_temp()
            QMessageBox.information(self, APP_NAME, T("share_complete"))
            return
        QMessageBox.information(
            self, APP_NAME,
            T("msg_restored_pkg") if has_packages else T("msg_restored"))

    def _restore_fail(self, err: str):
        self._set_busy(False)
        self.restore_log.append(T("err_prefix") + err)
        if self._public_restore:
            self.share_log.append(err)
            self._clean_share_temp()
        QMessageBox.critical(self, APP_NAME, T("msg_restore_failed"))

    def _has_pkg_lists(self) -> bool:
        """True, wenn nach einem Restore Paketlisten im Home liegen."""
        pkg_dir = HOME / ".savedesktopdesign-packages"
        if not pkg_dir.is_dir():
            return False
        return any((pkg_dir / n).exists() for n in (
            "pacman-explicit.txt", "pacman-foreign.txt",
            "apt-manual.txt", "dnf-packages.txt", "flatpak.txt"))

    def install_packages(self):
        try:
            self._install_packages()
        except Exception:
            err = traceback.format_exc()
            self.restore_log.append(T("err_prefix") + err)
            QMessageBox.critical(self, APP_NAME, T("err_prefix") + err)

    def _install_packages(self):
        pkg_dir = HOME / ".savedesktopdesign-packages"
        if not self._has_pkg_lists():
            QMessageBox.warning(
                self, APP_NAME,
                T("msg_no_pkglists") + f"\n\n({pkg_dir})")
            return

        # Garantierte Sicht-Rückmeldung: zeigt, welche Listen gefunden wurden,
        # bevor irgendein Terminal startet. Klick kann nie stumm bleiben.
        found = [n for n in (
            "pacman-explicit.txt", "pacman-foreign.txt",
            "apt-manual.txt", "dnf-packages.txt", "flatpak.txt")
            if (pkg_dir / n).exists()]
        if QMessageBox.question(
                self, APP_NAME,
                T("msg_confirm_pkg") + "\n\n" + ", ".join(found)
                ) != QMessageBox.StandardButton.Yes:
            return

        script = pkg_dir / "install.sh"
        lines = [
            "#!/usr/bin/env bash",
            'cd "$(dirname "$0")"',
            "echo '=== SaveYourKDEDesign ==='",
        ]
        # --- Arch / CachyOS ---
        if (pkg_dir / "pacman-repos.txt").exists() and shutil.which("pacman-conf"):
            lines += [
                "echo; echo '--- Repos vom alten Gerät / repos on the old machine ---'",
                "cat pacman-repos.txt",
                "echo 'Active here:'; pacman-conf --repo-list",
                "echo 'Missing repos must be enabled in /etc/pacman.conf first,'",
                "echo 'otherwise their packages will be skipped below.'",
            ]
        if (pkg_dir / "pacman-explicit.txt").exists():
            if shutil.which("pacman"):
                lines.append("echo; echo '--- pacman ---'")
                lines.append("sudo pacman -S --needed - < pacman-explicit.txt || true")
            else:
                lines.append("echo 'pacman list found, but this is not an Arch system — skipping.'")
        if (pkg_dir / "pacman-foreign.txt").exists() and shutil.which("pacman"):
            lines += [
                "echo; echo '--- AUR (Glass, Rounded Corners, Klassy, Krohnkite …) ---'",
                "echo 'Packages in list:'; cat pacman-foreign.txt; echo",
                # AUR-Helper automatisch nachinstallieren, falls keiner da ist
                "if ! command -v paru >/dev/null 2>&1 && ! command -v yay >/dev/null 2>&1; then",
                "  echo 'No AUR helper found - installing paru ...'",
                "  sudo pacman -S --needed --noconfirm base-devel git",
                "  rm -rf /tmp/sdd-paru",
                "  git clone https://aur.archlinux.org/paru-bin.git /tmp/sdd-paru",
                "  (cd /tmp/sdd-paru && makepkg -si --noconfirm) || echo 'paru installation failed'",
                "fi",
                'AURHELPER="$(command -v paru || command -v yay || true)"',
                'if [ -n "$AURHELPER" ]; then',
                '  echo "Using AUR helper: $AURHELPER"',
                '  "$AURHELPER" -S --needed --noconfirm - < pacman-foreign.txt || \\',
                '    "$AURHELPER" -S --needed - < pacman-foreign.txt || true',
                "else",
                "  echo 'Skipping AUR packages (no helper available) - see pacman-foreign.txt'",
                "fi",
            ]
        # --- Ubuntu / Debian ---
        if (pkg_dir / "apt-manual.txt").exists():
            if shutil.which("apt-get"):
                lines.append("echo; echo '--- apt ---'")
                lines.append("sudo apt-get update || true")
                lines.append("xargs -r -a apt-manual.txt sudo apt-get install -y --ignore-missing || true")
            else:
                lines.append("echo 'apt list found, but apt is not available — skipping.'")
        # --- Fedora ---
        if (pkg_dir / "dnf-packages.txt").exists():
            if shutil.which("dnf"):
                lines.append("echo; echo '--- dnf ---'")
                lines.append("xargs -r -a dnf-packages.txt sudo dnf install -y --skip-broken || "
                             "xargs -r -a dnf-packages.txt sudo dnf install -y || true")
            else:
                lines.append("echo 'dnf list found, but dnf is not available — skipping.'")
        # --- Flatpak (alle Distros) ---
        if (pkg_dir / "flatpak.txt").exists():
            if shutil.which("flatpak"):
                lines.append("echo; echo '--- Flatpak ---'")
                lines.append("xargs -r -a flatpak.txt -I{} flatpak install -y --noninteractive flathub {} || true")
            else:
                lines.append("echo 'flatpak list found, but flatpak is not installed — skipping.'")
        lines.append("echo; echo '=== Done! ==='; read -r -p 'Press Enter to close …'")
        script.write_text("\n".join(lines))
        script.chmod(0o755)

        # Terminal je nach Emulator korrekt aufrufen; konsole als eigenes Fenster,
        # das bei Fehlern offen bleibt (--hold), damit man die Meldung sieht.
        konsole = shutil.which("konsole")
        gnome = shutil.which("gnome-terminal")
        xfce = shutil.which("xfce4-terminal")
        alacritty = shutil.which("alacritty")
        kitty = shutil.which("kitty")
        xterm = shutil.which("xterm")
        # xfce4-terminal und xterm bekommen eine Kommandozeile als String —
        # ohne Quoting bricht jeder Pfad mit Leerzeichen.
        script_q = shlex.quote(str(script))
        if konsole:
            cmd = [konsole, "--separate", "--hold", "-e", "bash", str(script)]
        elif gnome:
            cmd = [gnome, "--", "bash", str(script)]
        elif xfce:
            cmd = [xfce, "--hold", "-e", f"bash {script_q}"]
        elif kitty:
            cmd = [kitty, "bash", str(script)]
        elif alacritty:
            cmd = [alacritty, "-e", "bash", str(script)]
        elif xterm:
            cmd = [xterm, "-hold", "-e", f"bash {script_q}"]
        else:
            QMessageBox.warning(self, APP_NAME, T("msg_no_terminal") + str(script))
            return

        manual = f"bash {script_q}"
        try:
            subprocess.Popen(cmd)
            self.restore_log.append(T("log_pkg_terminal"))
            # Info inkl. manuellem Befehl als Rückfallebene, falls kein
            # Terminalfenster erscheint (z. B. ungewöhnlicher Emulator).
            QMessageBox.information(
                self, APP_NAME, T("msg_pkg_opened") + f"\n\n{manual}")
        except Exception as e:
            QMessageBox.warning(
                self, APP_NAME,
                f"{T('msg_term_failed')}\n\n{e}\n\n{T('msg_no_terminal')}{manual}")

    # ---------------- Update über das GitHub-Release ----------------
    def _app_file(self) -> Path:
        """Die laufende Programmdatei — genau die wird ersetzt."""
        return Path(__file__).resolve()

    def check_update(self):
        if self._worker_running():
            QMessageBox.information(self, APP_NAME, T("msg_busy"))
            return
        target = self._app_file()
        # Im Git-Klon würde ein Überschreiben die Arbeitskopie zerschießen.
        if (target.parent / ".git").is_dir():
            QMessageBox.information(self, APP_NAME, T("upd_git_clone"))
            return
        if not os.access(target, os.W_OK):
            QMessageBox.warning(self, APP_NAME,
                                T("upd_not_writable").format(path=target))
            return
        self._set_busy(True)
        self.update_btn.setText(T("upd_checking"))
        self.update_worker = UpdateWorker()
        self.update_worker.checked.connect(self._update_checked)
        self.update_worker.no_release.connect(self._update_no_release)
        self.update_worker.failed.connect(self._update_failed)
        self.update_worker.start()

    def _apply_version_label(self):
        """Zeigt immer die installierte Version — und, sobald GitHub einmal
        befragt wurde, ob sie aktuell ist. Überlebt den Sprachwechsel."""
        text = f"v{VERSION}"
        newer = (self._latest_tag
                 and _version_tuple(self._latest_tag) > _version_tuple(VERSION))
        if newer:
            text += " · " + T("ver_update").format(
                new=self._latest_tag.lstrip("vV"))
        elif self._latest_tag:
            text += " · " + T("ver_current")
        self.version_label.setText(text)
        self.version_label.setStyleSheet("font-weight: bold;" if newer else "")

    def _silent_check(self):
        """Startabfrage: setzt nur das Label. Kein Dialog, keine Busy-Sperre —
        sie darf einen Backup- oder Restore-Klick nicht blockieren."""
        if not self.autocheck_cb.isChecked():
            return
        if self.silent_worker is not None and self.silent_worker.isRunning():
            return
        self.silent_worker = UpdateWorker(timeout=8)
        self.silent_worker.checked.connect(self._silent_result)
        self.silent_worker.start()

    def _silent_result(self, tag: str, notes: str):
        self._latest_tag = tag
        self._apply_version_label()

    def _update_reset(self):
        self._set_busy(False)
        self.update_btn.setText(T("btn_update"))

    def _update_no_release(self):
        self._update_reset()
        QMessageBox.information(self, APP_NAME, T("upd_no_release"))

    def _update_failed(self, err: str):
        self._update_reset()
        QMessageBox.critical(self, APP_NAME, f"{T('upd_failed')}\n{err}")

    def _update_checked(self, tag: str, notes: str):
        self._update_reset()
        self._latest_tag = tag
        self._apply_version_label()
        if _version_tuple(tag) <= _version_tuple(VERSION):
            QMessageBox.information(self, APP_NAME,
                                    T("upd_current").format(cur=VERSION))
            return
        msg = T("upd_available").format(new=tag.lstrip("vV"), cur=VERSION)
        if notes.strip():
            msg += "\n\n" + notes.strip()[:1200]
        if QMessageBox.question(self, APP_NAME,
                                msg) != QMessageBox.StandardButton.Yes:
            return
        self._set_busy(True)
        self.update_btn.setText(T("upd_installing"))
        self.update_worker = UpdateWorker(tag)
        self.update_worker.downloaded.connect(self._update_downloaded)
        self.update_worker.failed.connect(self._update_failed)
        self.update_worker.start()

    def _update_downloaded(self, tag: str, src: str):
        self._update_reset()
        try:
            target = self._app_file()
            # Nichts ungeprüft an die Stelle des laufenden Programms schreiben:
            # es muss diese App sein und fehlerfrei kompilieren.
            if (len(src) < 20000 or APP_NAME not in src
                    or "class MainWindow" not in src):
                raise ValueError("downloaded file is not " + APP_NAME)
            compile(src, str(target), "exec")
            mode = target.stat().st_mode & 0o777
            shutil.copy2(target, target.with_name(target.name + ".bak"))
            tmp = target.with_name(target.name + ".new")
            tmp.write_text(src, encoding="utf-8")
            tmp.chmod(mode)
            os.replace(tmp, target)      # atomar, kein halb geschriebenes Skript
        except Exception as e:
            QMessageBox.critical(
                self, APP_NAME,
                f"{T('upd_failed')}\n{type(e).__name__}: {e}")
            return
        if QMessageBox.question(
                self, APP_NAME, T("upd_done").format(new=tag.lstrip("vV"))
                ) == QMessageBox.StandardButton.Yes:
            os.execv(sys.executable, [sys.executable, str(self._app_file())])

    def restart_plasma(self):
        if QMessageBox.question(
                self, APP_NAME, T("msg_confirm_plasma")) != QMessageBox.StandardButton.Yes:
            return
        subprocess.Popen(
            "kquitapp6 plasmashell 2>/dev/null || kquitapp5 plasmashell 2>/dev/null; "
            "sleep 1; (kstart plasmashell >/dev/null 2>&1 &) || (plasmashell --replace >/dev/null 2>&1 &)",
            shell=True)


def migrate_installed_branding(app_file: Path):
    """In-app updates replace only the source; migrate the old menu label too.

    Git checkouts and custom launchers are untouched. Legacy settings/storage
    deliberately keep their paths and are not copied or deleted.
    """
    installed = HOME / ".local/share/savedesktopdesign/savedesktopdesign.py"
    if app_file.resolve() != installed.resolve():
        return
    entry = HOME / ".local/share/applications/savedesktopdesign.desktop"
    if entry.is_file() and not entry.is_symlink():
        content = entry.read_text()
        if "\nName=SaveDesktopDesign\n" in content:
            entry.write_text(content.replace("\nName=SaveDesktopDesign\n", "\nName=" + APP_NAME + "\n"))
    launcher = HOME / ".local/bin/saveyourkdedesign"
    if not launcher.exists() and not launcher.is_symlink():
        launcher.parent.mkdir(parents=True, exist_ok=True)
        with launcher.open("x") as stream:
            stream.write("#!/bin/sh\nexec python3 " + shlex.quote(str(installed)) + ' "$@"\n')
        launcher.chmod(0o755)


def main():
    try:
        migrate_installed_branding(Path(__file__))
    except OSError as error:
        print(f"Launcher migration skipped: {error}", file=sys.stderr)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
