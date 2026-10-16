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
import configparser
import hashlib
import gzip
import json
import os
import platform
import re
import shlex
import shutil
import socket
import struct
import zlib
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QProcess, QSettings, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QGuiApplication, QImageReader
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
VERSION = "1.8.8"

# Update über die GitHub-Releases — nur Standardbibliothek, kein Token.
GITHUB_REPO = "redsoul1905/SaveYourKDEDesign"
LEGACY_GITHUB_REPO = "redsoul1905/Savedesktopdesign"
RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RAW_URL = ("https://raw.githubusercontent.com/" + GITHUB_REPO
           + "/{tag}/saveyourkdedesign.py")
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
    "share_complete": "Design applied and Plasma restarted. Check the wallpaper, panels and widgets. Pinned apps were retained or cleared according to your selection; source launchers were not imported.",
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
    "share_complete": "Design übernommen und Plasma neu gestartet. Bitte Wallpaper, Panels und Widgets prüfen. Angeheftete Programme wurden gemäß deiner Auswahl beibehalten oder geleert; Quell-Verknüpfungen wurden nicht importiert.",
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


def safe_public_restore_target(rel: str) -> Path:
    """Resolve a public restore destination without escaping the user's HOME."""
    logical = HOME / rel
    try:
        home = HOME.resolve(strict=True)
        # Resolve the nearest existing component strictly, then append missing
        # children. This detects symlink loops even on Python versions whose
        # non-strict resolve leaves a cyclic component unresolved.
        existing = logical
        missing = []
        while not os.path.lexists(existing):
            if existing == HOME:
                raise OSError("missing HOME")
            missing.append(existing.name)
            existing = existing.parent
        resolved = existing.resolve(strict=True)
        for name in reversed(missing):
            resolved /= name
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"Restore target cannot be resolved safely: {rel}") from exc
    if resolved != home and not resolved.is_relative_to(home):
        raise ValueError(f"Restore target leaves the user folder: {rel}")
    return resolved


def make_rollback(rel_paths: list[str], categories: list[str],
                  dereference: bool = False) -> str:
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
        # Public restores may deliberately write through a safe dotfile-manager
        # link. Back up the data behind that link, not merely the link itself.
        # Resolve only the restore roots. Nested links are replaced by _merge,
        # not written through; following them could escape HOME or loop forever.
        tar.dereference = False
        for rel in present:
            source = safe_public_restore_target(rel) if dereference else HOME / rel
            tar.add(source, arcname=f"home/{rel}")
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
RESTORE_FILE_LIMIT = 1_000_000  # Full local backups can contain hundreds of thousands of icon links.
RESTORE_EXPANDED_LIMIT = 4_000_000_000
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
panelLengthMode panelOpacity
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


def primary_screen_index() -> int:
    # Plasma's ScreenPool orders outputs by priority: primaryScreen() is first
    # and idForScreen() indexes that ordered list, NOT QGuiApplication.screens().
    # https://github.com/KDE/plasma-workspace/blob/v6.5.0/shell/screenpool.cpp
    return 0


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


def portable_wallpaper_config(text: str, included_roots: tuple[Path, ...] = ()) -> tuple[str, list[tuple[Path, str]]]:
    """Embed every selected file wallpaper and replace machine-specific paths."""
    assets = {}
    output = []
    for line in text.splitlines():
        if line.startswith("Image="):
            value = line.split("=", 1)[1]
            raw = urllib.parse.unquote(value.removeprefix("file://"))
            source = Path(raw)
            if source.is_absolute() and not source.exists():
                raise ValueError("Wallpaper nicht erreichbar / Wallpaper unavailable: " + str(source)
                                 + ". Laufwerk verbinden und erneut sichern / Connect the drive and retry.")
            if source.is_absolute() and source.is_file():
                included = next((root for root in included_roots
                                 if source.is_relative_to(root)), None)
                if included is not None:
                    rel = str(source.relative_to(HOME))
                else:
                    digest = sha256_file(source)[:24]
                    suffix = source.suffix if len(source.suffix) <= 16 else ""
                    rel = ".local/share/wallpapers/SaveYourKDEDesign/" + digest + suffix
                    assets[rel] = source.resolve(strict=True)
                line = "Image=file://" + HOME_TOKEN + "/" + rel
        output.append(line)
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(output) + suffix, [(source, rel) for rel, source in assets.items()]


def portable_launchers(value: str) -> str:
    """Keep desktop IDs, never publish local file paths or executable commands."""
    result = []
    for item in value.split(','):
        if item in {'preferred://filemanager', 'preferred://browser', 'preferred://mailer', 'preferred://terminal'}:
            result.append(item)
            continue
        for root in ('file:///var/lib/flatpak/exports/share/applications/',
                     'file:///usr/share/applications/',
                     'file://' + str(HOME / '.local/share/applications') + '/',
                     'file://' + str(HOME / '.local/share/flatpak/exports/share/applications') + '/'):
            if item.startswith(root):
                item = 'applications:' + urllib.parse.unquote(item[len(root):])
                break
        if item.startswith('applications:'):
            name = item[len('applications:'):]
            if (re.fullmatch(r'[\w .+&()@-]+\.desktop', name)
                    and not name.startswith('.') and len(name) <= 255):
                result.append(item)
    return ','.join(result)


def repair_launcher_icons(text: str, staged_home: Path, available=None) -> str:
    """Older codes may reference a distro icon not present on the receiver."""
    available = available or QIcon.hasThemeIcon
    preamble, blocks = _kconfig_blocks(text)
    launchers = {group for group, lines in blocks if any(line in {
        'plugin=org.kde.plasma.kickoff', 'plugin=org.kde.plasma.kicker',
        'plugin=org.kde.plasma.kickerdash'} for line in lines)}
    output = list(preamble)
    for group, lines in blocks:
        output.append(group)
        for line in lines:
            if group in {g + '[Configuration][General]' for g in launchers} and line.startswith('icon='):
                name = line[5:]
                bundled = _safe_asset_name(name) and any(
                    path.is_file() for suffix in ('.svg', '.png', '.svgz')
                    for path in (staged_home / '.local/share/icons').rglob(name + suffix))
                if not bundled and not available(name):
                    line = 'icon=start-here-kde'
            output.append(line)
    return '\n'.join(output) + '\n'


def share_layout_setting_allowed(key: str, value: str) -> bool:
    """Permit typed visual values, never arbitrary text from unknown widgets."""
    lowered = key.casefold().replace("-", "").replace("_", "")
    blocked = ("command", "execute", "executable", "password", "passwd", "secret",
               "token", "apikey", "username", "email", "note", "text", "shell",
               "script", "program", "history", "recent", "clipboard")
    if any(word in lowered for word in blocked):
        return False
    identity = {os.environ.get("USER", ""), socket.gethostname()}
    if any(item and len(item) >= 3 and item.casefold() in value.casefold()
           for item in identity):
        return False
    if key == 'launchers':
        return bool(value) and portable_launchers(value) == value
    if key == 'icon':
        return bool(re.fullmatch(r'[A-Za-z0-9_.+-]+', value))
    if re.search(r"(?:^|[=\s])/(?:home|root|run/user)/", value) or "file://" in value:
        return False
    if "://" in value and not value.startswith(("applications:", "preferred:")):
        return False
    if key == "globalSettings" and len(value) <= 256000:
        # Panel Colorizer's structured appearance settings contain no free text.
        # Reject unknown text, paths and commands rather than publishing them.
        literals = {"", "View", "Window", "Button", "Selection", "Tooltip",
                    "Complementary", "Header", "adaptive", "center", "fill",
                    "none", "top", "bottom", "left", "right", "backgroundColor",
                    "highlightColor", "textColor", "foregroundColor"}
        def visual(node, depth=0):
            if depth > 32:
                return False
            if isinstance(node, dict):
                return all(re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", k)
                           and not any(word in k.casefold() for word in blocked)
                           and visual(v, depth + 1) for k, v in node.items())
            if isinstance(node, list):
                return all(visual(v, depth + 1) for v in node)
            if isinstance(node, str):
                return node in literals or bool(re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", node))
            return node is None or isinstance(node, (bool, int, float))
        try:
            return visual(json.loads(value))
        except (ValueError, RecursionError):
            return False
    return (len(value) <= 8192 and bool(re.fullmatch(
        r"(?:true|false|-?\d+(?:\.\d+)?(?:[,;]-?\d+(?:\.\d+)?)*)", value)))


def read_setting_schema(path: Path) -> dict:
    """Read data-only KConfigXT metadata. Schemas are not permission to publish text."""
    if not path.is_file():
        return {}
    if path.stat().st_size > 512000:
        raise ValueError('Configuration schema exceeds 512 KB')
    data = path.read_text(encoding='utf-8')
    if '<!DOCTYPE' in data.upper() or '<!ENTITY' in data.upper():
        raise ValueError('Entities in configuration schemas are not supported')
    root = ET.fromstring(data)
    for element in root.iter():
        element.tag = element.tag.rsplit('}', 1)[-1]
    result = {}
    for group in root.iter('group'):
        for entry in group.findall('entry'):
            name = entry.get('name', '')
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,127}', name):
                continue
            default = entry.find('default')
            result[name] = {'type': entry.get('type', ''), 'group': group.get('name', ''),
                            'default': default.text if default is not None and not default.attrib else None,
                            'choices': [c.get('name', '') for c in entry.findall('./choices/choice')]}
    return result


ROOT_DISK_TOKEN = '__SYKD_ROOT_DISK__'


def root_disk_uuid() -> str:
    value = (_run_cmd(['findmnt', '-n', '-o', 'UUID', '/'], 10) or '').strip()
    return value if re.fullmatch(r'[A-Za-z0-9-]{4,100}', value) else ''


def widget_setting_adapter(plugin: str, key: str, value: str):
    """Reviewed semantic adapters, not permission to copy arbitrary strings."""
    if plugin == 'org.kde.windowbuttons':
        if key == 'buttons' and re.fullmatch(r'(?:10|[0-9])(?:\|(?:10|[0-9])){0,15}', value):
            return 'copy', value, 'Reihenfolge der Fensterknöpfe übernehmen.'
        if key == 'selectedPlugin' and value == 'org.kde.breeze':
            return 'copy', value, 'Breeze-Fensterknöpfe übernehmen.'
        if key == 'selectedScheme' and value == '_plasmatheme_':
            return 'copy', value, 'Farben aus dem Plasma-Design verwenden.'
    if plugin == 'plasmusic-toolbar':
        boolean_keys = {'songTextInPanel', 'pauseTextScrollingWhileMediaIsNotPlaying',
                        'textScrollingEnabled', 'textScrollingResetOnPause',
                        'useSongTextFixedWidth', 'fullViewSongTextVisible'}
        integer_keys = {'textScrollingSpeed', 'textScrollingBehaviour', 'songTextAlignment',
                        'songTextFixedWidth', 'fullViewTextScrollingSpeed', 'titlePosition',
                        'fullTitlePosition', 'fullViewSongTextAlignment', 'fullViewSongTextPosition',
                        'compactTruncatedTextStyle'}
        if key in boolean_keys and value.lower() in {'true', 'false'}:
            return 'copy', value.lower(), 'Text-Darstellung übernehmen, keine Musiktitel oder Wiedergabeverläufe.'
        if key in integer_keys and re.fullmatch(r'\d{1,5}', value):
            return 'copy', value, 'Text-Anordnung und Scrollverhalten übernehmen.'
        if key == 'panelIcon' and value in {'view-media-track', 'media-playback-start', 'audio-x-generic', 'media-optical-audio'}:
            return 'copy', value, 'Standard-Musiksymbol übernehmen.'
    if plugin == 'org.kde.plasma.kickoff':
        if key == 'systemFavorites' and all(item in {'', 'suspend', 'hibernate', 'reboot', 'shutdown',
                'logout', 'lock-screen', 'switch-user', 'save-session'} for item in value.replace('\\', '').split(',')):
            return 'copy', value, 'Systemaktionen übernehmen, keine eigenen Befehle.'
        if key == 'global' and re.fullmatch(r'(?:(?:Alt|Ctrl|Shift|Meta)\+)*(?:F\d{1,2}|Space|[A-Z])', value):
            return 'copy', value, 'Tastenkürzel für den Anwendungsstarter übernehmen.'
    if plugin == 'org.kde.olib.thermalmonitor' and key == 'sensors':
        try:
            items = json.loads(value)
            if (isinstance(items, list) and len(items) <= 32 and all(
                    isinstance(item, dict) and set(item) == {'name', 'sensorId'}
                    and isinstance(item['name'], str) and isinstance(item['sensorId'], str)
                    and re.fullmatch(r'(?:CPU|GPU|Processor|Graphics|Temperature|\d{3,5}[A-Za-z0-9 -]{0,20})', item['name'])
                    and re.fullmatch(r'(?:cpu/(?:all|cpu\d+)/(?:averageTemperature|temperature)|gpu/gpu\d+/(?:temperature|temp\d+))', item['sensorId'])
                    for item in items)):
                return 'copy', value, 'Temperatursensoren ohne private Pfade und Hardware-Seriennummern übernehmen.'
        except ValueError:
            pass
    if plugin == 'luisbocanegra.panel.colorizer':
        if key in {'panelWidgets', 'lastPreset'}:
            return 'exclude', '', 'Lokaler Cache; Panel Colorizer ermittelt die Ziel-Widgets selbst neu.'
        if key == 'configurationOverrides':
            try:
                if json.loads(value) == {'overrides': {}, 'associations': []}:
                    return 'copy', value, 'Leere Überschreibungen vollständig übernehmen.'
            except ValueError:
                pass
    if plugin == 'org.kde.plasma.pager' and key == 'displayedText' and value in {'Number', 'Name', 'None'}:
        return 'copy', value, 'Arbeitsflächen-Darstellung übernehmen.'
    if plugin == 'org.kde.plasma.digitalclock':
        if key == 'fontStyleName' and value in {'Regular', 'Bold', 'Italic', 'Bold Italic', 'Light', 'Medium', 'DemiBold'}:
            return 'copy', value, 'Schriftschnitt übernehmen.'
        if key == 'enabledCalendarPlugins' and all(v in {'', 'pimevents', 'holidaysevents', 'astronomicalevents'} for v in value.split(',')):
            return 'copy', value, 'Kalender-Erweiterungsauswahl übernehmen, keine Kalendereinträge.'
    if plugin.startswith('org.kde.plasma.systemmonitor.'):
        if key in {'CurrentPreset', 'chartFace'} and re.fullmatch(r'org\.kde\.[A-Za-z0-9_.-]+', value):
            return 'copy', value, 'Monitor-Darstellung übernehmen.'
        if key in {'highPrioritySensorIds', 'lowPrioritySensorIds', 'totalSensors'}:
            try:
                sensors = json.loads(value)
                if not isinstance(sensors, list) or not all(isinstance(s, str) for s in sensors):
                    return None
                source_root = root_disk_uuid()
                result = []
                for sensor in sensors:
                    if source_root and sensor.startswith('disk/' + source_root + '/'):
                        sensor = 'disk/' + ROOT_DISK_TOKEN + '/' + sensor.split('/')[-1]
                    if not re.fullmatch(r'(?:disk/' + ROOT_DISK_TOKEN + r'/(?:free|used|total|freePercent|usedPercent)|memory/(?:physical|swap)/(?:free|used|total|usedPercent))', sensor):
                        return None
                    result.append(sensor)
                return 'copy', json.dumps(result), 'Systemlaufwerk anhand seiner Rolle am Ziel zuordnen, nicht anhand der Quell-UUID.'
            except ValueError:
                pass
    return None


def private_setting(key: str) -> bool:
    lower = key.casefold()
    return (any(part in lower for part in ('password', 'secret', 'token', 'credential', 'apikey',
            'command', 'executable', 'username', 'email', 'history', 'clipboard', 'note'))
            or lower in {'floatingtitle', 'title', 'text', 'activelocation', 'countrycode', 'locationname',
                         'savedlocations', 'timezone', 'notificationsentkeys', 'alertnotificationstate',
                         'notificationspaceweatherlastdate', 'notificationuvlastdate'})


def kwin_setting_adapter(group: str, key: str, value: str):
    if group == '[Script-karousel]' and key == 'presetWidths':
        widths = [part.strip() for part in value.split(',')]
        if (1 <= len(widths) <= 32 and all(re.fullmatch(r'\d{1,3}(?:\.\d{1,2})?%', width)
                                        and 0 < float(width[:-1]) <= 100 for width in widths)):
            return 'copy', ', '.join(widths), 'Karousel-Spaltenbreiten relativ zur Ziel-Bildschirmbreite übernehmen.'
    return None


def portable_setting(key: str, value: str, spec: dict | None = None) -> tuple[str, str, str]:
    """Classify extension settings without executing or trusting their schemas."""
    lower = key.casefold()
    if any(s in lower for s in ('password', 'secret', 'token', 'credential', 'apikey', 'command',
                                'executable', 'username', 'email', 'history', 'clipboard', 'note')):
        return 'review', '', 'Privater oder ausführbarer Inhalt: nicht veröffentlichen; bei Bedarf nur am Ziel konfigurieren.'
    if lower in {'ignoreactivity', 'ignorescreen', 'screen', 'activityid'}:
        return 'reset', '', 'Lokalen Bildschirm-/Aktivitätsfilter am Ziel neu zuordnen; im öffentlichen Design leer setzen.'
    if spec and lower in {'displayedtext', 'showtext', 'showtitle'}:
        if value in {'0', '1', 'true', 'false'} or value in spec.get('choices', []):
            return 'copy', value, 'Deklarierte Darstellungsoption übernehmen.'
    if 'title' in lower or 'text' in lower:
        return 'review', '', 'Freitext/Fenstertitel kann privat sein: in den Einstellungen dieser Erweiterung am Ziel neu zuordnen.'
    if len(value) > 8192 or '\x00' in value:
        return 'review', '', 'Strukturierte Einstellung benötigt einen Format-Adapter; Schema und Datentyp prüfen.'
    identities = {os.environ.get('USER', ''), socket.gethostname()}
    if any(len(s) >= 3 and s.casefold() in value.casefold() for s in identities):
        return 'review', '', 'Persönlichen Rechner-/Benutzerbezug entfernen oder nur lokal am Ziel setzen.'
    kind = (spec or {}).get('type', '').lower()
    if kind in {'path', 'pathlist', 'url', 'urllist', 'password'}:
        return 'review', '', 'Dateibezug im Erweiterungsdialog neu auswählen; für automatische Übernahme ist ein geprüfter Datei-Adapter erforderlich.'
    if kind in {'int', 'uint', 'longlong', 'ulonglong', 'double', 'bool'}:
        valid = (value.lower() in {'true', 'false', '0', '1'} if kind == 'bool' else
                 bool(re.fullmatch(r'-?\d+(?:\.\d+)?' if kind == 'double' else r'-?\d+', value)))
        if not valid:
            return 'review', '', 'Wert passt nicht zum deklarierten Typ ' + kind + '; im Erweiterungsdialog korrigieren oder Erweiterung aktualisieren.'
    if value.casefold() in {'true', 'false'}:
        return 'copy', value.lower(), 'Boolesche Einstellung übernehmen.'
    if re.fullmatch(r'-?\d+(?:\.\d+)?(?:[,;]-?\d+(?:\.\d+)?)*', value):
        kind = (spec or {}).get('type', '').lower()
        if kind == 'bool' and value not in {'0', '1'}:
            return 'review', '', 'Ungültiger Bool-Wert: im Einstellungsdialog auf true/false zurücksetzen.'
        if kind in {'uint', 'ulonglong'} and value.startswith('-'):
            return 'review', '', 'Negativen Wert im Einstellungsdialog auf einen zulässigen Wert ändern.'
        return 'copy', value, 'Typisierte Zahl/Geometrie übernehmen.'
    if re.fullmatch(r'#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?', value):
        return 'copy', value, 'Farbwert übernehmen.'
    if spec and value in spec.get('choices', []):
        return 'copy', value, 'Deklarierte Auswahl übernehmen.'
    if 'class' in lower and re.fullmatch(r'[A-Za-z0-9_.\[\]*? ,;\\-]*', value):
        return 'copy', value, 'Fensterklassen-Filter übernehmen; auf dem Ziel verfügbare Anwendungen prüfen.'
    if not value:
        return 'copy', value, 'Leeren Wert übernehmen.'
    if '/' in value or '\\' in value:
        return 'review', '', 'Datei/URL-Bezug: benötigte Design-Datei bündeln und Pfad umsetzen; private Dateien nicht teilen.'
    if 'title' in lower or 'text' in lower:
        return 'review', '', 'Freitext/Fenstertitel kann privat sein: im Ziel-Einstellungsdialog manuell zuordnen.'
    return 'review', '', 'Unbekannter Text/Struktur: main.xml/KConfigXT-Schema ergänzen oder einen geprüften Format-Adapter verwenden.'


def extension_package_info(package: Path) -> dict[str, str]:
    """Read a KPackage identity from current JSON or legacy desktop metadata."""
    metadata = package / "metadata.json"
    if metadata.is_file() and metadata.stat().st_size <= 256000:
        try:
            data = json.loads(metadata.read_text(encoding="utf-8"))
            plugin = data.get("KPlugin", {})
            if isinstance(data, dict) and isinstance(plugin, dict):
                return {"id": str(plugin.get("Id", "")),
                        "version": str(plugin.get("Version", "unknown")),
                        "minimum": str(data.get("X-Plasma-API-Minimum-Version", ""))}
        except (OSError, UnicodeError, ValueError, AttributeError):
            pass
    legacy = package / "metadata.desktop"
    if legacy.is_file() and legacy.stat().st_size <= 256000:
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            parser.read(legacy, encoding="utf-8")
            entry = parser["Desktop Entry"]
            return {"id": entry.get("X-KDE-PluginInfo-Name", ""),
                    "version": entry.get("X-KDE-PluginInfo-Version", "unknown"),
                    "minimum": entry.get("X-Plasma-API-Minimum-Version", "")}
        except (OSError, UnicodeError, configparser.Error, KeyError):
            pass
    return {}


def extension_package(root: Path, base: str, plugin_id: str) -> Path | None:
    """Find a package by metadata ID; directory names are not authoritative."""
    parent = root / base
    direct = parent / plugin_id
    if direct.exists():
        return direct
    try:
        # Path.iterdir() is lazy on Python 3.10/3.12: a missing directory can
        # raise while iterating rather than when the iterator is constructed.
        for child in parent.iterdir():
            if child.is_dir() and extension_package_info(child).get("id") == plugin_id:
                return child
    except OSError:
        return None
    return None


def primary_layout_values(values: list[tuple[str, str, str]], primary: int):
    """Keep only Plasma containments belonging to the exporting primary screen."""
    selected = set()
    for group, key, value in values:
        match = re.fullmatch(r"\[Containments\]\[(\d+)\]", group)
        if match and key == "lastScreen" and value == str(primary):
            selected.add(match.group(1))
    while True:
        linked = {value for group, key, value in values
                  if (match := re.match(r"^\[Containments\]\[(\d+)\]", group))
                  and match.group(1) in selected
                  and key == "SystrayContainmentId" and value.isdigit()}
        if linked <= selected:
            break
        selected.update(linked)
    result = []
    for row in values:
        group = row[0]
        match = re.match(r"^\[Containments\]\[(\d+)\]", group)
        if match:
            if match.group(1) in selected:
                result.append(row)
        elif group != "[ScreenMapping]":
            result.append(row)
    return result


def _kconfig_blocks(text: str):
    preamble, blocks, current = [], [], None
    for line in text.splitlines():
        if line.startswith("[") and line.endswith("]"):
            current = [line, []]
            blocks.append(current)
        elif current is None:
            preamble.append(line)
        else:
            current[1].append(line)
    return preamble, blocks


def _screen_containments(blocks, screen: int):
    selected = set()
    for group, lines in blocks:
        match = re.fullmatch(r"\[Containments\]\[(\d+)\]", group)
        if match and any(line == f"lastScreen={screen}" for line in lines):
            selected.add(match.group(1))
    while True:
        linked = {line.split("=", 1)[1] for group, lines in blocks
                  if (match := re.match(r"^\[Containments\]\[(\d+)\]", group))
                  and match.group(1) in selected for line in lines
                  if re.fullmatch(r"SystrayContainmentId=\d+", line)}
        if linked <= selected:
            break
        selected.update(linked)
    return selected


def merge_primary_applet_config(source: str, target: str,
                                source_primary: int, target_primary: int,
                                id_mapping: dict | None = None,
                                target_activity: str = '', preserve_pins: bool = True) -> str:
    """Replace only the target primary-screen containments and retain all others."""
    target_preamble, target_blocks = _kconfig_blocks(target)
    _, source_blocks = _kconfig_blocks(source)
    source_ids = _screen_containments(source_blocks, source_primary)
    target_ids = _screen_containments(target_blocks, target_primary)
    # Pinned applications belong to the receiver, not the shared visual design.
    target_pins = []
    for group, lines in target_blocks:
        match = re.fullmatch(r'\[Containments\]\[(\d+)\]\[Applets\]\[\d+\]', group)
        if preserve_pins and match and match[1] in target_ids and any(line in {
                'plugin=org.kde.plasma.icontasks', 'plugin=org.kde.plasma.taskmanager'} for line in lines):
            for pin in _block_values(target_blocks, group + '[Configuration][General]').get('launchers', '').split(','):
                if pin and pin not in target_pins:
                    target_pins.append(pin)
    task_groups = {group + '[Configuration][General]' for group, lines in source_blocks
                   if any(line in {'plugin=org.kde.plasma.icontasks', 'plugin=org.kde.plasma.taskmanager'} for line in lines)}
    existing_groups = {group for group, _ in source_blocks}
    source_blocks += [(group, []) for group in sorted(task_groups - existing_groups)]
    if not target_activity:
        for group, lines in target_blocks:
            if re.fullmatch(r'\[Containments\]\[\d+\]', group):
                values = dict(line.split('=', 1) for line in lines if '=' in line)
                if (values.get('lastScreen') == str(target_primary)
                        and values.get('plugin') != 'org.kde.panel' and values.get('activityId')):
                    target_activity = values['activityId']
                    break
    if not source_ids:
        return target if target.endswith("\n") or not target else target + "\n"

    retained = []
    for block in target_blocks:
        match = re.match(r"^\[Containments\]\[(\d+)\]", block[0])
        if not match or match.group(1) not in target_ids:
            retained.append(block)
    incoming = [block for block in source_blocks
                if (match := re.match(r"^\[Containments\]\[(\d+)\]", block[0]))
                and match.group(1) in source_ids]

    used = {int(number) for group, _ in retained if group.startswith("[Containments]")
            for number in re.findall(r"\[(\d+)\]", group)}
    source_numbers = sorted({int(number) for group, _ in incoming
                             for number in re.findall(r"\[(\d+)\]", group)})
    next_id = max(used | set(source_numbers) | {0}) + 1
    mapping = {}
    for old in source_numbers:
        while next_id in used:
            next_id += 1
        mapping[str(old)] = str(next_id)
        used.add(next_id)
        next_id += 1
    if id_mapping is not None:
        id_mapping.update(mapping)

    def remap_group(group):
        return re.sub(r"\[(Containments|Applets)\]\[(\d+)\]",
                      lambda m: "[" + m.group(1) + "][" + mapping.get(m.group(2), m.group(2)) + "]", group)

    transformed = []
    for group, lines in incoming:
        top = bool(re.fullmatch(r"\[Containments\]\[(\d+)\]", group))
        updated = []
        for line in lines:
            key, sep, value = line.partition("=")
            if group in task_groups and key == 'launchers':
                continue
            if sep and top and key == "lastScreen":
                value = str(target_primary)
            elif sep and key in {"containmentId", "SystrayContainmentId", "AppletOrder"}:
                value = re.sub(r"\d+", lambda m: mapping.get(m.group(0), m.group(0)), value)
            updated.append(key + sep + value if sep else line)
        if group in task_groups:
            updated.append('launchers=' + ','.join(target_pins))
        if top and target_activity and any(line in {'plugin=org.kde.plasma.folder', 'plugin=org.kde.desktopcontainment'} for line in lines):
            updated = [line for line in updated if not line.startswith('activityId=')]
            updated.append('activityId=' + target_activity)
        transformed.append((remap_group(group), updated))

    output = list(target_preamble)
    for group, lines in [*retained, *transformed]:
        output.append(group)
        output.extend(lines)
    return "\n".join(output).rstrip() + "\n"


def merge_panel_views(source: str, target: str, mapping: dict, removed: set) -> str:
    """Keep target secondary panels and map imported Panel IDs with the layout."""
    preamble, target_blocks = _kconfig_blocks(target)
    _, source_blocks = _kconfig_blocks(source)
    result = list(preamble)
    for group, lines in target_blocks:
        match = re.match(r"^\[PlasmaViews\]\[Panel (\d+)\]", group)
        if match and match.group(1) in removed:
            continue
        result.extend([group, *lines])
    for group, lines in source_blocks:
        match = re.match(r"^\[PlasmaViews\]\[Panel (\d+)\]", group)
        if match and match.group(1) in mapping:
            group = group.replace("[Panel " + match.group(1) + "]",
                                  "[Panel " + mapping[match.group(1)] + "]", 1)
            result.extend([group, *lines])
    return "\n".join(result).rstrip() + "\n"


PANEL_VIEW_KEYS = ("alignment", "floating", "panelLengthMode", "panelOpacity",
                   "panelVisibility", "maxLength", "minLength", "offset", "thickness")


def _block_values(blocks, group: str) -> dict[str, str]:
    """Return the last value for each key in one KConfig group."""
    result = {}
    for candidate, lines in blocks:
        if candidate == group:
            result.update(line.split("=", 1) for line in lines if "=" in line)
    return result


def merge_design_kconfig(source: str, target: str) -> str:
    """Only replace exported keys; preserve unrelated target preferences."""
    groups = {}
    for is_source, text in ((False, target), (True, source)):
        for group, lines in _kconfig_blocks(text)[1]:
            groups.setdefault(group, {}).update(line.split('=', 1) for line in lines
                if '=' in line and not line.startswith(('#', ';'))
                and not (is_source and group == '[Desktops]' and re.match(r'(?:Id|Name)_', line)))
    # Source desktop IDs/names are private; reuse target identities and create
    # only missing IDs locally, never copy IDs from another computer.
    if '[Desktops]' in groups and 'Number' in groups['[Desktops]']:
        desktops = groups['[Desktops]']
        number = int(desktops['Number'])
        if not 1 <= number <= 100:
            raise ValueError('Invalid virtual desktop count')
        for key in list(desktops):
            match = re.fullmatch(r'(?:Id|Name)_(\d+)', key)
            if match and int(match[1]) > number:
                del desktops[key]
        for index in range(1, number + 1):
            desktops.setdefault(f'Id_{index}', str(uuid.uuid4()))
            desktops.setdefault(f'Name_{index}', str(index))
    return '\n'.join(line for group, settings in groups.items()
                     for line in [group, *(key + '=' + value for key, value in settings.items())]) + '\n'


def activate_kwin_design(settings: dict, dbus: str, required_effects=()):
    """Apply imported script settings and desktop count without restarting KWin."""
    def call(path, method, *args):
        result = _run_cmd([dbus, 'org.kde.KWin', path, method, *map(str, args)], 30)
        if result is None:
            raise ValueError('KWin konnte die Design-Einstellungen nicht aktivieren: ' + method +
                             '. Ab- und wieder anmelden, dann Import erneut prüfen.')
        return result.strip()

    desktop = settings.get('[Desktops]', {})
    if 'Number' in desktop:
        desired = int(desktop['Number'])
        method = 'org.kde.KWin.VirtualDesktopManager.'
        current = int(call('/VirtualDesktopManager', method + 'count'))
        # Never silently remove workspaces containing the target user's windows.
        if current > desired:
            raise ValueError(f'Das Design benötigt {desired} virtuelle Arbeitsflächen, vorhanden sind {current}. '
                             'Systemeinstellungen → Fensterverwaltung → Virtuelle Arbeitsflächen: '
                             'überzählige Arbeitsflächen entfernen und Import wiederholen.')
        for position in range(current, desired):
            call('/VirtualDesktopManager', method + 'createDesktop', position, str(position + 1))
        if 'Rows' in desktop:
            call('/VirtualDesktopManager', method + 'rows', desktop['Rows'])
            if call('/VirtualDesktopManager', method + 'rows') != desktop['Rows']:
                raise ValueError('Arbeitsflächen-Reihen nicht übernommen; Systemeinstellungen → Virtuelle Arbeitsflächen prüfen.')
        if int(call('/VirtualDesktopManager', method + 'count')) != desired:
            raise ValueError('Virtuelle Arbeitsflächen wurden nicht übernommen; Anzahl in den Systemeinstellungen prüfen.')

    scripts = [g[8:-1] for g in settings if re.fullmatch(r'\[Script-[\w.-]+\]', g)
               and settings.get('[Plugins]', {}).get(g[8:-1] + 'Enabled') == 'true']
    for plugin in scripts:
        if call('/Scripting', 'org.kde.kwin.Scripting.isScriptLoaded', plugin) == 'true':
            call('/Scripting', 'org.kde.kwin.Scripting.unloadScript', plugin)
            for _ in range(20):
                if call('/Scripting', 'org.kde.kwin.Scripting.isScriptLoaded', plugin) == 'false':
                    break
                time.sleep(0.1)
            else:
                raise ValueError('KWin-Skript konnte nicht neu geladen werden: ' + plugin + '. Bitte ab- und wieder anmelden.')
    call('/KWin', 'org.kde.KWin.reconfigure')
    # reconfigure is queued by KWin; wait before starting scripts from refreshed config.
    time.sleep(0.5)
    call('/Scripting', 'org.kde.kwin.Scripting.start')
    activate_kwin_effects(settings.get('[Plugins]', {}), call, required_effects)
    for plugin in scripts:
        if call('/Scripting', 'org.kde.kwin.Scripting.isScriptLoaded', plugin) != 'true':
            raise ValueError('KWin-Skript nicht geladen: ' + plugin +
                             '. In Systemeinstellungen → KWin-Skripte aktivieren; Plasma-Kompatibilität prüfen.')


def activate_kwin_effects(plugins, call, required_effects=()):
    """Availability is not activation: explicitly reload and verify effects."""
    if not plugins:
        return
    prefix = 'org.kde.kwin.Effects.'
    available = set(call('/Effects', prefix + 'listOfEffects').splitlines())
    # Disable requested effects first, especially competing blur implementations.
    for key, value in plugins.items():
        name = key.removesuffix('Enabled')
        if key.endswith('Enabled') and value == 'false' and name in available:
            call('/Effects', prefix + 'unloadEffect', name)
    for key, value in plugins.items():
        if not key.endswith('Enabled') or value != 'true':
            continue
        name = key[:-7]
        if name not in available:
            successor = name.removeprefix('kwin4_effect_')
            if successor != name and successor in available and plugins.get(successor + 'Enabled') == 'true':
                continue  # Historical duplicate key, not a second plugin.
            if name in required_effects or name in {'glass', 'blur', 'kwin4_effect_shapecorners'}:
                raise ValueError('KWin erkennt den benötigten Effekt nicht: ' + name +
                                 '. Passendes Effektpaket für die installierte KWin-Version installieren und erneut anmelden.')
            continue  # Scripts are handled separately; preflight checks missing requirements.
        if call('/Effects', prefix + 'isEffectLoaded', name) != 'true':
            if call('/Effects', prefix + 'loadEffect', name) != 'true':
                raise ValueError('Effekt installiert, aber nicht ladbar: ' + name +
                                 '. Passende Version für Plasma/KWin installieren und Grafiktreiber prüfen.')
        call('/Effects', prefix + 'reconfigureEffect', name)
        if call('/Effects', prefix + 'isEffectLoaded', name) != 'true':
            raise ValueError('Effekt wurde nicht aktiv: ' + name + '. Import nicht vollständig abgeschlossen.')


def panel_layout_snapshot(applet_config: str, views_config: str, screen: int) -> list[dict]:
    """Describe panels without machine-local IDs or widget settings.

    The snapshot is deliberately small: it is only a fidelity contract for the
    panel edge, view geometry and ordered widget plugin IDs.  It never exports
    widget data such as commands, notes, paths or credentials.
    """
    applet_blocks = _kconfig_blocks(applet_config)[1]
    view_blocks = _kconfig_blocks(views_config)[1]
    result = []
    for containment_id in sorted(_screen_containments(applet_blocks, screen), key=int):
        top = _block_values(applet_blocks, f"[Containments][{containment_id}]")
        if top.get("plugin") != "org.kde.panel":
            continue
        applets = {}
        prefix = f"[Containments][{containment_id}][Applets]["
        for group, lines in applet_blocks:
            if group.startswith(prefix) and group.endswith("]"):
                applet_id = group[len(prefix):-1]
                values = dict(line.split("=", 1) for line in lines if "=" in line)
                if applet_id.isdigit() and values.get("plugin"):
                    applets[applet_id] = values["plugin"]
        general = _block_values(applet_blocks, f"[Containments][{containment_id}][General]")
        order = [item for item in general.get("AppletOrder", top.get("AppletOrder", "")).split(";")
                 if item in applets]
        order += [item for item in sorted(applets, key=int) if item not in order]
        view = _block_values(view_blocks, f"[PlasmaViews][Panel {containment_id}]")
        defaults = _block_values(view_blocks, f"[PlasmaViews][Panel {containment_id}][Defaults]")
        geometry = {key: (view.get(key) if key in view else defaults.get(key))
                    for key in PANEL_VIEW_KEYS
                    if key in view or key in defaults}
        result.append({"edge": top.get("location", ""),
                       "widgets": [applets[item] for item in order],
                       "geometry": geometry})
    return result


def duplicate_panel_ids(layout: str, views: str, screen: int) -> list[str]:
    blocks = _kconfig_blocks(layout)[1]
    ids = [cid for cid in sorted(_screen_containments(blocks, screen), key=int)
           if _block_values(blocks, f'[Containments][{cid}]').get('plugin') == 'org.kde.panel']
    seen, duplicates = set(), []
    for cid, snapshot in zip(ids, panel_layout_snapshot(layout, views, screen)):
        fingerprint = json.dumps(snapshot, sort_keys=True)
        if fingerprint in seen:
            duplicates.append(cid)
        seen.add(fingerprint)
    return duplicates


def without_panels(layout: str, excluded: set[str]) -> str:
    preamble, blocks = _kconfig_blocks(layout)
    excluded = set(excluded)
    while True:
        linked = {line.split('=', 1)[1] for group, lines in blocks
                  if (match := re.match(r'^\[Containments\]\[(\d+)\]', group))
                  and match[1] in excluded for line in lines
                  if re.fullmatch(r'SystrayContainmentId=\d+', line)}
        if linked <= excluded:
            break
        excluded |= linked
    output = list(preamble)
    for group, lines in blocks:
        match = re.match(r'^\[Containments\]\[(\d+)\]', group)
        if not match or match[1] not in excluded:
            output.extend([group, *lines])
    return '\n'.join(output) + '\n'


def panel_layout_warnings(snapshot: list[dict], screen_width: int) -> list[str]:
    """Flag objectively overlapping panels while preserving the source layout."""
    if screen_width <= 0:
        return []
    spans = []
    for index, panel in enumerate(snapshot, 1):
        geometry = panel["geometry"]
        if geometry.get('panelLengthMode') == '1':
            continue  # FitContent: persisted maximum is not the rendered width.
        try:
            minimum = int(geometry.get("minLength", "0"))
            maximum = int(geometry.get("maxLength", "0"))
            offset = int(geometry.get("offset", "0"))
            alignment = int(geometry.get("alignment", "132"))
        except ValueError:
            continue
        length = minimum if minimum == maximum else 0
        if length <= 0:
            continue
        if alignment & 1:  # left
            start = offset
        elif alignment & 2:  # right
            start = screen_width - length - offset
        else:  # horizontal centre
            start = (screen_width - length) // 2 + offset
        spans.append((panel["edge"], start, start + length, index))
    warnings = []
    for pos, (edge, start, end, index) in enumerate(spans):
        for other_edge, other_start, other_end, other_index in spans[pos + 1:]:
            if edge == other_edge and min(end, other_end) - max(start, other_start) > 4:
                warnings.append(f"Panels {index} and {other_index} overlap at edge {edge}")
    return warnings


def valid_layout_snapshot(value) -> bool:
    if not isinstance(value, list) or len(value) > 64:
        return False
    for panel in value:
        if not isinstance(panel, dict) or set(panel) != {"edge", "widgets", "geometry"}:
            return False
        if (not isinstance(panel["edge"], str) or len(panel["edge"]) > 16
                or not isinstance(panel["widgets"], list) or len(panel["widgets"]) > 128
                or not isinstance(panel["geometry"], dict) or set(panel["geometry"]) - set(PANEL_VIEW_KEYS)):
            return False
        if (not all(isinstance(plugin, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", plugin)
                    for plugin in panel["widgets"])
                or not all(isinstance(key, str) and isinstance(item, str) and len(item) <= 32
                           for key, item in panel["geometry"].items())):
            return False
    return True


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


class PublicPrivacyError(ValueError):
    """A failed privacy check, distinguishable from archive/resource failures."""


def privacy_block(rel: str, reason: str):
    # Never echo the matching secret or an absolute source path into an error.
    label = rel
    for identity in (str(HOME), os.environ.get('USER', ''), socket.gethostname()):
        if len(identity) >= 3:
            label = re.sub(re.escape(identity), '[privat]', label, flags=re.I)
    raise PublicPrivacyError('Datenschutz: Upload gesperrt / upload blocked: ' + label + '. ' + reason
                     + ' Datei lokal bereinigen oder eine unveränderte öffentliche Version der Erweiterung verwenden; dann neu exportieren.')


def check_public_filename(rel: str):
    parts = Path(rel).parts
    if (any(p.startswith('.') and p not in {'.config', '.local'} for p in parts)
            or Path(rel).suffix.lower() in {'.bak', '.old', '.orig', '.pem', '.key', '.p12', '.pfx',
                                           '.sqlite', '.db', '.zip', '.tar', '.gz', '.7z'}
            or any(p.lower() in {'id_rsa', 'id_ed25519', 'credentials', 'secrets'} for p in parts)):
        privacy_block(rel, 'Versteckte Datei, Sicherung, Schlüssel oder nicht prüfbarer Container im Design.')
    check_public_content(rel.encode(), rel)


def check_public_content(data: bytes, rel: str):
    # Decode common text encodings, including UTF-16; scan binary string tables
    # too. This is a privacy guard, not a claim of semantic anonymisation.
    text = data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8', errors='replace')
    text = urllib.parse.unquote(text).replace('\\/', '/')
    identities = {os.environ.get('USER', ''), HOME.name, socket.gethostname()}
    if any(len(v) >= 3 and re.search(r'(?<![\w])' + re.escape(v) + r'(?![\w])', text, re.I)
           for v in identities):
        privacy_block(rel, 'Persönlicher Benutzer-/Rechnerbezug gefunden.')
    # Literal shell/regex templates describe any home, not a user's identity.
    path_text = text.replace('/home/*/', '/GENERIC_HOME/').replace('/home/[^/]+/', '/GENERIC_HOME/')
    if re.search(r'(?:/home/[^/\s"\'<>]+/|/Users/[^/\s"\'<>]+/|/(?:mnt|media|run/media)/|[A-Z]:[\\/]Users[\\/])', path_text, re.I):
        privacy_block(rel, 'Lokaler persönlicher Dateipfad gefunden.')
    if re.search(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b', text):
        privacy_block(rel, 'Schlüsselmaterial oder Zugangstoken gefunden.')
    # Only literal assignments, not schema declarations such as name="password".
    if re.search(r'''(?im)(?:^|[,{;])\s*["']?(?:password|passwd|api[_-]?key|api[_-]?token|access[_-]?token|client[_-]?secret|authorization)["']?\s*[:=]\s*["']?[^\s"'{};,]+''', text):
        privacy_block(rel, 'Mögliche Zugangsdaten in einer eingebetteten Datei gefunden.')


def clean_public_media(data: bytes, rel: str) -> bytes:
    """Remove non-rendering metadata without recompressing image pixels.

    Malformed or unsupported metadata containers fail closed. ICC profiles are
    retained because they affect rendering. No interpretation of visible pixels.
    """
    if Path(rel).suffix.lower() == '.svgz':
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
                expanded = stream.read(4_000_001)
            if len(expanded) > 4_000_000:
                privacy_block(rel, 'SVGZ überschreitet die sichere entpackte Größe.')
            cleaned = clean_public_media(expanded, rel[:-1])
            check_public_content(cleaned, rel)
            # Deterministic header: no original filename or timestamp.
            return gzip.compress(cleaned, mtime=0)
        except (OSError, EOFError, zlib.error):
            privacy_block(rel, 'Beschädigte SVGZ-Datei.')
    if data.startswith((b'PK\x03\x04', b'\x1f\x8b', b'SQLite format 3', b'7z\xbc\xaf\x27\x1c', b'\x7fELF')):
        privacy_block(rel, 'Eingebetteter Container oder ausführbare Binärdatei kann nicht anonym geprüft werden.')
    # Removing EXIF orientation must not silently rotate the visible design.
    if b'Exif\x00\x00' in data or b'eXIf' in data or b'EXIF' in data:
        buffer = QBuffer(); buffer.setData(QByteArray(data)); buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        reader = QImageReader(buffer)
        if reader.transformation().value:
            privacy_block(rel, 'Bild verwendet EXIF-Drehung; zuerst aufrecht und ohne Metadaten als PNG speichern.')
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        output = bytearray(data[:8]); pos = 8; ended = False
        while pos < len(data):
            if pos + 12 > len(data):
                privacy_block(rel, 'Beschädigte PNG-Struktur.')
            size = int.from_bytes(data[pos:pos+4], 'big'); end = pos + 12 + size
            if end > len(data):
                privacy_block(rel, 'Beschädigte PNG-Struktur.')
            kind = data[pos+4:pos+8]; body = data[pos+8:pos+8+size]
            if zlib.crc32(kind + body) & 0xffffffff != int.from_bytes(data[end-4:end], 'big'):
                privacy_block(rel, 'Ungültige PNG-Prüfsumme.')
            if kind not in {b'tEXt', b'zTXt', b'iTXt', b'eXIf', b'tIME'}:
                # Unknown ancillary chunks can conceal unreviewed metadata.
                if kind not in {b'IHDR', b'PLTE', b'IDAT', b'IEND', b'tRNS', b'cHRM', b'gAMA',
                                b'iCCP', b'sBIT', b'sRGB', b'bKGD', b'hIST', b'pHYs', b'sPLT',
                                b'acTL', b'fcTL', b'fdAT', b'cICP', b'mDCv', b'cLLi'}:
                    privacy_block(rel, 'Unbekannter PNG-Metadatenblock.')
                output.extend(data[pos:end])
            pos = end
            if kind == b'IEND':
                ended = True
                break
        if not ended or pos != len(data):
            privacy_block(rel, 'PNG enthält Zusatzdaten oder keinen Abschluss.')
        return bytes(output)
    if data.startswith(b'\xff\xd8'):
        output = bytearray(data[:2]); pos = 2
        while pos < len(data):
            start = pos
            if data[pos] != 255:
                privacy_block(rel, 'Beschädigte JPEG-Struktur.')
            while pos < len(data) and data[pos] == 255:
                pos += 1
            if pos >= len(data):
                privacy_block(rel, 'Beschädigte JPEG-Struktur.')
            marker = data[pos]; pos += 1
            if marker == 0xd9:
                if pos != len(data):
                    privacy_block(rel, 'JPEG enthält angehängte Zusatzdaten.')
                output.extend(b'\xff\xd9')
                return bytes(output)
            if 0xd0 <= marker <= 0xd7 or marker == 1:
                output.extend(data[start:pos]); continue
            if pos + 2 > len(data):
                privacy_block(rel, 'Beschädigte JPEG-Struktur.')
            size = int.from_bytes(data[pos:pos+2], 'big'); end = pos + size
            if size < 2 or end > len(data):
                privacy_block(rel, 'Beschädigte JPEG-Struktur.')
            if marker not in {0xe1, 0xed, 0xfe}:
                if 0xe0 <= marker <= 0xef and not (marker == 0xe0 and data[pos+2:end].startswith(b'JFIF\0')
                                                       or marker == 0xe2 and data[pos+2:end].startswith(b'ICC_PROFILE\0')
                                                       or marker == 0xee and data[pos+2:end].startswith(b'Adobe')):
                    privacy_block(rel, 'Unbekannter JPEG-Metadatenblock.')
                output.extend(data[start:end])
            pos = end
            if marker == 0xda:
                # Preserve compressed scan data; resume marker parsing at the
                # next non-stuffed, non-restart marker (also progressive JPEG).
                scan = pos
                while pos < len(data):
                    if data[pos] == 255 and pos + 1 < len(data):
                        following = data[pos+1]
                        if following == 0 or 0xd0 <= following <= 0xd7:
                            pos += 2; continue
                        break
                    pos += 1
                output.extend(data[scan:pos])
        privacy_block(rel, 'JPEG ohne Abschluss.')
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        if len(data) < 12 or int.from_bytes(data[4:8], 'little') + 8 != len(data):
            privacy_block(rel, 'Beschädigte WebP-Struktur.')
        chunks = bytearray(); pos = 12
        while pos < len(data):
            if pos + 8 > len(data):
                privacy_block(rel, 'Beschädigte WebP-Struktur.')
            kind = data[pos:pos+4]; size = int.from_bytes(data[pos+4:pos+8], 'little')
            end = pos + 8 + size + size % 2
            if end > len(data):
                privacy_block(rel, 'Beschädigte WebP-Struktur.')
            if kind not in {b'EXIF', b'XMP '}:
                if kind not in {b'VP8 ', b'VP8L', b'VP8X', b'ALPH', b'ICCP', b'ANIM', b'ANMF'}:
                    privacy_block(rel, 'Unbekannter WebP-Metadatenblock.')
                chunk = bytearray(data[pos:end])
                if kind == b'VP8X' and size:
                    chunk[8] &= ~0x0c
                chunks.extend(chunk)
            pos = end
        return b'RIFF' + struct.pack('<I', 4 + len(chunks)) + b'WEBP' + bytes(chunks)
    if Path(rel).suffix.lower() == '.svg':
        try:
            tree = ET.fromstring(data)
            changed = False
            for parent in tree.iter():
                for child in list(parent):
                    if child.tag.split('}')[-1] in {'metadata', 'namedview'}:
                        parent.remove(child); changed = True
                for key in list(parent.attrib):
                    if key.split('}')[-1] in {'absref', 'docname', 'docbase', 'export-filename'}:
                        del parent.attrib[key]; changed = True
            if changed:
                return ET.tostring(tree, encoding='utf-8')
        except ET.ParseError:
            privacy_block(rel, 'SVG kann nicht sicher geprüft werden.')
    # Unsupported image metadata must not silently pass. These formats need a
    # dedicated adapter before public sharing (private backups are unaffected).
    if Path(rel).suffix.lower() in {'.gif', '.tif', '.tiff', '.heic', '.avif', '.svgz', '.mp4', '.webm'}:
        privacy_block(rel, 'Dieses Medienformat benötigt einen Datenschutz-Adapter; für öffentliche Designs PNG/JPEG/WebP/SVG verwenden.')
    return data


def audit_public_upload(path: Path):
    """Final, independent content gate: run before any network request."""
    inspect_public_archive(path)
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            if (member.uid or member.gid or member.uname or member.gname
                    or set(member.pax_headers) - {'path'}):
                privacy_block(member.name, 'Persönliche Archiv-Metadaten gefunden.')
            check_public_filename(member.name)
            data = archive.extractfile(member).read()
            if clean_public_media(data, member.name) != data:
                privacy_block(member.name, 'Bild-Metadaten wurden nicht vollständig entfernt.')
            check_public_content(data, member.name)


def public_design(stage: Path, screens: list[dict], log=lambda message: None,
                  primary_screen: int = 0, excluded_panels=None, settings_review=None) -> dict:
    """Build a visual-only tree, never a copy of the user's private backup."""
    home = stage / "home"
    home.mkdir()
    excluded_panels = set(excluded_panels or [])
    allowed_layout_groups = None
    if excluded_panels:
        layout_text = (HOME / '.config/plasma-org.kde.plasma.desktop-appletsrc').read_text(encoding='utf-8')
        views_text = (HOME / '.config/plasmashellrc').read_text(encoding='utf-8')
        if not excluded_panels <= set(duplicate_panel_ids(layout_text, views_text, primary_screen)):
            raise ValueError('Panel-Auswahl hat sich geändert; bitte Export erneut starten.')
        allowed_layout_groups = {group for group, _ in _kconfig_blocks(without_panels(layout_text, excluded_panels))[1]}
    sources = [HOME / ".local/share", Path("/usr/local/share"), Path("/usr/share")]
    requirements, omitted, paths = [], [], set()
    copied_bytes = 0
    copied_count = 0
    seen = set()
    exported_fonts = set()
    export_primary = primary_screen
    setting_actions = settings_review if settings_review is not None else []
    schema_cache = {}
    privacy_issues = set()

    def schema_for(base, plugin):
        cache_key = (base, plugin)
        if cache_key not in schema_cache:
            schema_cache[cache_key] = {}
            if _safe_asset_name(plugin):
                for root in sources:
                    package = extension_package(root, base, plugin)
                    if package is not None:
                        try:
                            schema_cache[cache_key] = read_setting_schema(package / 'contents/config/main.xml')
                        except (OSError, ValueError, ET.ParseError) as error:
                            setting_actions.append({'component': plugin, 'key': 'main.xml', 'action': 'review',
                                'solution': 'Schema reparieren oder Erweiterung aus vertrauenswürdiger Quelle aktualisieren: ' + type(error).__name__})
                        break
        return schema_cache[cache_key]

    def copy_asset(src: Path, rel: str, allowed_root: Path, related_root: Path | None = None):
        try:
            copy_asset_checked(src, rel, allowed_root, related_root)
        except PublicPrivacyError as error:
            privacy_issues.add(str(error))

    def copy_asset_checked(src: Path, rel: str, allowed_root: Path, related_root: Path | None = None):
        nonlocal copied_bytes, copied_count
        if not share_path_allowed(rel):
            raise ValueError("Invalid public asset destination")
        # Resolve icon symlinks into regular files, but never follow links into
        # private directories or copy sockets/devices/compiled binaries.
        real = src.resolve(strict=True)
        if not real.is_relative_to(allowed_root.resolve()) and not (
                related_root is not None and real.is_relative_to(related_root.resolve())):
            raise ValueError(f"Asset link leaves its theme directory: {src.name}")
        if real.is_dir():
            if real in seen:
                raise ValueError("Cyclic theme directory link")
            seen.add(real)
            for child in sorted(real.iterdir()):
                copy_asset(child, rel + "/" + child.name, allowed_root, related_root)
            seen.remove(real)
        elif real.is_file():
            # Packaging markers keep empty asset directories in source control.
            # They have no rendering role. Omit only recognised, truly empty
            # markers; never whitelist hidden files or their contents generally.
            if real.stat().st_size == 0 and (rel.startswith('.local/share/icons/')
                    or real.name in {'.placeholder', '.gitkeep', '.keep', '.empty'}):
                return
            # Breeze ships a compiled duplicate of its SVG tree. Do not publish
            # embedded editor metadata from that opaque acceleration cache.
            if (real.name == 'breeze-icons.rcc' and rel.startswith('.local/share/icons/breeze/')
                    and (real.parent / 'index.theme').is_file()
                    and (real.parent / 'actions').is_dir() and (real.parent / 'apps').is_dir()):
                return
            check_public_filename(rel)
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
            payload = clean_public_media(real.read_bytes(), rel)
            check_public_content(payload, rel)
            dst.write_bytes(payload)
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
        if base in {"kwin/scripts", "kwin/effects"}:
            candidates = [candidate for root in sources
                          if (candidate := extension_package(root, base, name)) is not None]
        else:
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
            # Kvantum's selected modified theme explicitly inherits the matching
            # base theme; do not permit links into any other neighbouring folder.
            related = src.with_name(src.name[:-1]) if base == 'Kvantum' and src.name.endswith('#') else None
            # Tela variants share their application icons with the base theme.
            # Permit only these reviewed sibling identities, not the whole
            # icons directory (which may also contain unrelated private files).
            icon_bases = {'Tela-dark': 'Tela', 'Tela-light': 'Tela',
                          'Tela-circle-dark': 'Tela-circle', 'Tela-circle-light': 'Tela-circle'}
            if base == 'icons' and name in icon_bases:
                candidate = src.parent / icon_bases[name]
                if (candidate.is_dir() and not candidate.is_symlink()
                        and (candidate / 'index.theme').is_file()):
                    related = candidate
            copy_asset(src, target_rel, src if src.is_dir() else src.parent, related)
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
        if filename == "plasma-org.kde.plasma.desktop-appletsrc":
            export_primary = primary_screen
            if allowed_layout_groups is not None:
                values = [row for row in values if row[0] in allowed_layout_groups]
            values = primary_layout_values(values, export_primary)
        specs = {}
        widget_owners = {}
        if filename == 'kwinrc':
            groups = {g for g, _, _ in values}
            groups |= {'[Script-' + k[:-7] + ']' for g, k, v in values
                       if g == '[Plugins]' and k.endswith('Enabled') and v == 'true'
                       and any(extension_package(root, 'kwin/scripts', k[:-7]) for root in sources)}
            for group in sorted(groups):
                match = re.fullmatch(r'\[(Script|Effect)-([\w.-]+)\]', group)
                if match:
                    schema = schema_for('kwin/scripts' if match[1] == 'Script' else 'kwin/effects', match[2])
                    specs.update({(group, key): spec for key, spec in schema.items()})
        elif filename == 'plasma-org.kde.plasma.desktop-appletsrc':
            for group, key, plugin in list(values):
                if key == 'plugin' and re.fullmatch(r'\[Containments\]\[\d+\]\[Applets\]\[\d+\]', group):
                    widget_owners[group] = plugin
                    for setting, spec in schema_for('plasma/plasmoids', plugin).items():
                        subgroup = spec.get('group') or 'General'
                        if re.fullmatch(r'[A-Za-z0-9_ -]+', subgroup):
                            specs[(group + '[Configuration][' + subgroup + ']', setting)] = spec
        existing = {(g, k) for g, k, _ in values}
        for (group, key), spec in sorted(specs.items()):
            default = spec.get('default')
            if (group, key) not in existing and default is not None:
                owner = next((plugin for prefix, plugin in widget_owners.items()
                              if group.startswith(prefix + '[Configuration]')), '')
                action, normalized, _ = (widget_setting_adapter(owner, key, default.strip())
                                         or (kwin_setting_adapter(group, key, default.strip()) if filename == 'kwinrc' else None)
                                         or portable_setting(key, default.strip(), spec))
                if action == 'copy':
                    values.append((group, key, normalized))
        lines, group_before = [], None
        for group, key, value in values:
            owner = next((plugin for prefix, plugin in widget_owners.items()
                          if group.startswith(prefix + '[Configuration]')), '')
            adapted = widget_setting_adapter(owner, key, value) if owner else None
            if filename == 'kwinrc':
                adapted = kwin_setting_adapter(group, key, value)
            if filename == 'kwinrc' and group == '[Round-Corners]' and key in {'Inclusions', 'Exclusions'}:
                adapted = portable_setting('windowClass', value)
            # Anonymous designs intentionally exclude personal content and caches.
            # Unknown visual formats remain actionable blockers, not silent losses.
            if private_setting(key) or (adapted and adapted[0] == 'exclude'):
                omitted.append(filename + ':' + key)
                continue
            # Generic names outside the selected Plasma theme are not visual
            # settings; in arbitrary groups they can be personal free text.
            if key == 'name' and not (filename == 'plasmarc' and group == '[Theme]'):
                omitted.append(filename + ':' + key)
                continue
            if key == 'launchers' and filename == 'plasma-org.kde.plasma.desktop-appletsrc':
                continue  # Receiver keeps its own pinned applications.
            enabled_effect = filename == "kwinrc" and group == "[Plugins]" and key.endswith("Enabled")
            extension_setting = ((filename == 'kwinrc' and bool(re.fullmatch(r'\[(?:Script|Effect)-[\w.-]+\]|\[Round-Corners\]', group)))
                                 or (group, key) in specs or adapted is not None)
            extension_extra = False
            if extension_setting and key not in {'globalSettings', 'launchers'}:
                action, replacement, solution = adapted or portable_setting(key, value, specs.get((group, key)))
                if action == 'review':
                    setting_actions.append({'component': filename + ':' + group, 'key': key,
                                            'action': action, 'solution': solution})
                if action == 'review':
                    omitted.append(filename + ':' + key)
                    continue
                value = replacement
                extension_extra = True
            desktop_extra = filename == 'kwinrc' and group == '[Desktops]' and key in {'Number', 'Rows'}
            if desktop_extra and (not value.isdigit() or not 1 <= int(value) <= 100):
                raise ValueError('Ungültige Anzahl/Reihen virtueller Arbeitsflächen')
            layout_extra = (key not in VISUAL_KEYS
                            and filename == "plasma-org.kde.plasma.desktop-appletsrc"
                            and share_layout_setting_allowed(key, value))
            if key not in VISUAL_KEYS and not enabled_effect and not layout_extra and not extension_extra and not desktop_extra:
                omitted.append(filename + ":" + key)
                owner = next((plugin for prefix, plugin in widget_owners.items()
                              if group.startswith(prefix + '[Configuration]')), None)
                if owner:
                    _, _, solution = portable_setting(key, value)
                    setting_actions.append({'component': owner + ' — ' + group, 'key': key,
                                            'action': 'review', 'solution': solution +
                                            ' Widget-Einstellungen öffnen; bis ein Adapter vorhanden ist, diesen Wert am Ziel setzen.'})
                continue
            if "\x00" in value or len(value) > (256000 if layout_extra and key == "globalSettings" else 8192):
                omitted.append(filename + ":" + key)
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
            elif (("/" in value or "\\" in value or "://" in value or str(HOME) in value)
                  and not layout_extra and not extension_extra):
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
            if filename == 'plasma-org.kde.plasma.desktop-appletsrc' and key == 'icon' and _safe_asset_name(value):
                # Selected themes are already bundled. App/distro icons in hicolor
                # were previously excluded with the whole application-icon tree.
                for root in sources:
                    icon_root = root / 'icons/hicolor'
                    candidates = sorted(icon_root.rglob(value + '.svg')) if icon_root.is_dir() else []
                    if not candidates and icon_root.is_dir():
                        candidates = sorted(icon_root.rglob(value + '.png'))
                    if candidates:
                        icon = candidates[0]
                        copy_asset(icon, '.local/share/icons/hicolor/' + str(icon.relative_to(icon_root)), icon_root)
                        break
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
                    if any(extension_package(root, base, effect) is not None for root in sources):
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
    # Inspect all generated configurations too, before reporting findings once.
    # Never upload a partial design merely because an unsafe asset was omitted.
    for rel in sorted(paths):
        if rel.startswith('.config/'):
            try:
                check_public_filename(rel)
                check_public_content((home / rel).read_bytes(), rel)
            except PublicPrivacyError as error:
                privacy_issues.add(str(error))
    if privacy_issues:
        findings = sorted(privacy_issues)
        raise PublicPrivacyError(
            f'Export-Prüfung abgeschlossen: {len(findings)} Datenschutz-Hindernisse. '
            'Nichts hochgeladen. Alle betroffenen Dateien werden gemeinsam gemeldet:\n\n'
            + '\n\n'.join(findings))
    if not paths:
        raise ValueError("No shareable KDE design found")
    profile = desktop_profile(screens)
    if not profile.get("plasma") or not profile.get("session"):
        raise ValueError("Cannot determine the KDE version or session; export from your KDE desktop session")
    profile["primary_screen"] = export_primary
    if "desktop" in profile and profile["desktop"] != "KDE":
        raise ValueError("Export from a KDE Plasma session / Bitte aus einer KDE-Plasma-Sitzung exportieren")
    exported_layout = panel_layout_snapshot(
        (home / ".config/plasma-org.kde.plasma.desktop-appletsrc").read_text(encoding="utf-8")
        if (home / ".config/plasma-org.kde.plasma.desktop-appletsrc").is_file() else "",
        (home / ".config/plasmashellrc").read_text(encoding="utf-8")
        if (home / ".config/plasmashellrc").is_file() else "",
        export_primary)
    original_layout = HOME / '.config/plasma-org.kde.plasma.desktop-appletsrc'
    original_views = HOME / '.config/plasmashellrc'
    if original_layout.is_file():
        source_layout = panel_layout_snapshot(
            without_panels(original_layout.read_text(encoding='utf-8'), excluded_panels),
            original_views.read_text(encoding='utf-8') if original_views.is_file() else '', export_primary)
        if source_layout != exported_layout:
            raise ValueError('Export würde Panel-Anordnung oder Widget-Reihenfolge verändern; es wurde kein Code veröffentlicht.')
    source_width = (screens[export_primary]["width"]
                    if export_primary < len(screens) else 0)
    return {"app": APP_NAME, "version": VERSION, "public_design": 1,
            "created": datetime.now().isoformat(timespec="seconds"),
            "profile": profile, "paths": sorted(set(paths)),
            "requirements": requirements, "omitted_settings": len(omitted),
            "settings_review_count": sum(row['action'] == 'review' for row in setting_actions),
            "layout": exported_layout,
            "layout_warnings": panel_layout_warnings(exported_layout, source_width),
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
    audit_public_upload(path)  # Mandatory even for callers outside ShareWorker.
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
        primary = profile.get("primary_screen", 0)
        if type(primary) is not int or primary < 0 or (screens and primary >= len(screens)):
            raise ValueError("Invalid primary screen")
        if "layout" in manifest and not valid_layout_snapshot(manifest["layout"]):
            raise ValueError("Invalid layout fidelity data")
        if "layout_warnings" in manifest and (not isinstance(manifest["layout_warnings"], list)
                                               or not all(isinstance(item, str) and len(item) <= 200
                                                          for item in manifest["layout_warnings"])):
            raise ValueError("Invalid layout warning data")
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
               for k in ("plasma", "session"))


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
    for key in ("plasma", "session"):
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
        packages = {}
        for member in archive.getmembers():
            rel = member.name.removeprefix("home/.local/share/")
            base = next((p for p in prefixes if rel.startswith(p + "/")), None)
            if not base:
                continue
            rest = rel[len(base) + 1:].split("/")
            if len(rest) >= 2 and rest[0]:
                packages.setdefault((base, rest[0]), {})["has_files"] = True
            if len(rest) != 2 or rest[1] not in {"metadata.json", "metadata.desktop"}:
                continue
            if member.size > 256000 or not member.isfile():
                raise ValueError("Invalid extension metadata")
            raw = archive.extractfile(member).read()
            try:
                if rest[1] == "metadata.json":
                    data = json.loads(raw.decode("utf-8"))
                    plugin = data.get("KPlugin", {})
                    if not isinstance(data, dict) or not isinstance(plugin, dict):
                        raise ValueError
                    info = {"id": str(plugin.get("Id", "")),
                            "version": str(plugin.get("Version", "unknown")),
                            "minimum": str(data.get("X-Plasma-API-Minimum-Version", ""))}
                    packages[(base, rest[0])]["json"] = info
                else:
                    parser = configparser.ConfigParser(interpolation=None, strict=False)
                    parser.read_string(raw.decode("utf-8"))
                    entry = parser["Desktop Entry"]
                    packages[(base, rest[0])]["desktop"] = {
                        "id": entry.get("X-KDE-PluginInfo-Name", ""),
                        "version": entry.get("X-KDE-PluginInfo-Version", "unknown"),
                        "minimum": entry.get("X-Plasma-API-Minimum-Version", "")}
            except (UnicodeError, ValueError, AttributeError, configparser.Error, KeyError) as exc:
                raise ValueError("Invalid extension metadata") from exc

        seen_ids = set()
        for (base, folder), metadata in sorted(packages.items()):
            info = metadata.get("json") or metadata.get("desktop")
            if not info:
                raise ValueError(f"Bundled extension has no valid metadata: {base}/{folder}")
            plugin_id = info.get("id") or folder
            if not _safe_asset_name(plugin_id) or (base, plugin_id) in seen_ids:
                raise ValueError(f"Invalid or duplicate extension identity: {base}/{folder}")
            seen_ids.add((base, plugin_id))
            version = str(info.get("version", "unknown"))[:80]
            minimum = str(info.get("minimum", ""))
            local_version = "wird installiert / will be installed"
            for root in (HOME / ".local/share", Path("/usr/local/share"), Path("/usr/share")):
                local = extension_package(root, base, plugin_id)
                if local is not None:
                    local_version = extension_package_info(local).get("version", "unknown")[:80]
                    break
            rows.append(f"{base}/{plugin_id}: {local_version} → {version} (im Design enthalten)")
            if minimum and (not plasma_version(minimum) or not plasma_version(current.get("plasma", ""))
                            or plasma_version(current["plasma"]) < plasma_version(minimum)):
                issues.append(f"{plugin_id}: Plasma minimum / mindestens {minimum[:80]}")
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


def community_extension_plan(manifest: dict, current: dict, issues: list[str]) -> dict:
    """Offer known community packages without pretending they are distro packages."""
    result = {"command": None, "packages": [], "notes": [], "urls": [],
              "manual_command": "", "kind": ""}
    if not package_profile_compatible(manifest["profile"], current):
        return result
    try:
        system = platform.freedesktop_os_release()
    except OSError:
        return result
    distro = system.get("ID", "")
    if "arch" in system.get("ID_LIKE", "").split():
        distro = "arch"
    corners_package = ("kwin-effect-rounded-corners-x11-git" if current.get("session") == "x11"
                       else "kwin-effect-rounded-corners-git")
    known = {
        ("effect", "kwin4_effect_shapecorners"): (
            corners_package, "https://github.com/matinlotfali/KDE-Rounded-Corners"),
        ("decoration", "org.kde.klassy"): ("klassy", "https://github.com/paulmcauley/klassy"),
        ("effect", "glass"): ("kwin-effects-glass-git", "https://github.com/4v3ngR/kwin-effects-glass"),
        ("effect", "kwin4_effect_glass"): ("kwin-effects-glass-git", "https://github.com/4v3ngR/kwin-effects-glass"),
    }
    wanted = []
    for req in manifest["requirements"]:
        item = known.get((req["kind"], req["name"]))
        if item and req["kind"] + ": " + req["name"] in issues:
            wanted.append(item)
    if not wanted:
        return result
    result["packages"] = sorted({package for package, _ in wanted})
    result["urls"] = sorted({url for _, url in wanted})
    if distro == "fedora":
        commands = ["sudo dnf install -y dnf5-plugins || sudo dnf install -y dnf-plugins-core"]
        wants_klassy = any(package == "klassy" for package in result["packages"])
        wants_glass = any(package == "kwin-effects-glass-git" for package in result["packages"])
        wants_corners = corners_package in result["packages"]
        fedora_packages = []
        if wants_klassy:
            commands.extend(["sudo dnf copr enable -y errornointernet/klassy",
                             "sudo dnf install -y klassy"])
            fedora_packages.append("klassy")
        if wants_glass:
            commands.extend(["sudo dnf copr enable -y ama1470/kwin-effects-glass",
                             "sudo dnf install -y kwin-effects-glass"])
            fedora_packages.append("kwin-effects-glass")
        if wants_corners:
            package = "kwin-effect-roundcorners" + ("-x11" if current.get("session") == "x11" else "")
            commands.extend(["sudo dnf copr enable -y matinlotfali/KDE-Rounded-Corners",
                             "sudo dnf install -y " + package])
            fedora_packages.append(package)
        result["packages"] = fedora_packages
        script = "set -e; " + "; ".join(commands)
        result["manual_command"] = script.removeprefix("set -e; ")
        terminal = shutil.which("konsole")
        shell = shutil.which("bash")
        if terminal and shell:
            result["command"] = [shell, "-lc", script]
            result["terminal"] = terminal
            result["kind"] = "fedora_copr"
            result["notes"].append(
                "Fedora: Die zugeordneten COPR-Paketquellen werden nach Zustimmung aktiviert. "
                "COPR sind von der Gemeinschaft gepflegte Drittanbieterquellen; im Terminal wird dein Passwort abgefragt.")
        else:
            result["notes"].append("Fedora-Terminalbefehle: " + result["manual_command"])
        return result
    if distro != "arch":
        if corners_package in result["packages"]:
            result["notes"].append(
                "Rounded Corners (ShapeCorners): Installiere die zur Distribution, Plasma-Version und "
                "Sitzung passenden Pakete nach der Entwickleranleitung und wiederhole den Import: "
                "https://github.com/matinlotfali/KDE-Rounded-Corners#installation")
        if any(package == "klassy" for package in result["packages"]):
            result["notes"].append(
                "Klassy: Verwende die offiziellen Pakete des Entwicklers: "
                "https://software.opensuse.org/download.html?project=home%3Apaulmcauley&package=klassy")
        if distro in ("ubuntu", "debian") and any(package == "kwin-effects-glass-git" for package in result["packages"]):
            result["notes"].append(
                "Glass für Ubuntu/Debian muss passend zur Plasma-Version nach der Anleitung gebaut werden: "
                "https://github.com/4v3ngR/kwin-effects-glass#installation")
        if not result["notes"]:
            result["notes"].append("Installationsseiten: " + " ".join(result["urls"]))
        return result
    helper = next((path for name in ("yay", "paru") if (path := shutil.which(name))), None)
    terminal = shutil.which("konsole")
    instruction = "yay -S --needed " + " ".join(result["packages"])
    result["manual_command"] = instruction
    if not helper:
        result["notes"].append("AUR-Hilfe fehlt. Installiere yay oder paru und führe aus: " + instruction)
        return result
    available = [package for package in result["packages"]
                 if _run_cmd([helper, "-Si", "--aur", package], 90)]
    if len(available) != len(result["packages"]):
        result["notes"].append("AUR-Pakete konnten nicht verifiziert werden. Manuelle Anleitung: "
                               + " ".join(result["urls"]))
        return result
    if not terminal:
        result["notes"].append("Öffne ein Terminal und führe aus: "
                               + Path(helper).name + " -S --needed " + " ".join(available))
        return result
    result["command"] = [helper, "-S", "--needed", *available]
    result["terminal"] = terminal
    result["kind"] = "aur"
    result["notes"].append(
        "AUR-Gemeinschaftspakete: Der Paketinhalt wird außerhalb der offiziellen Distribution gebaut. "
        "Vor der Installation zeigt yay/paru die Pakete an und fragt nach Bestätigung und Passwort.")
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


def safe_extract(archive: tarfile.TarFile, destination: Path,
                 skip_external_links: bool = False) -> list[str]:
    """Reject escapes, special files and unsafe links on every Python version.

    Write regular files first, links last, so an archive cannot create a link
    and subsequently write through it. Also used by private backup restores.
    """
    links, names, total, skipped = [], set(), 0, []
    for member in archive:
        name = member.name.rstrip("/")
        parts = name.split("/")
        if (not name or any(p in ("", ".", "..") for p in parts)
                or "\\" in name or "\x00" in name or name in names):
            raise ValueError("Unsafe or duplicate archive path")
        names.add(name)
        total += member.size
        if len(names) > RESTORE_FILE_LIMIT or total > RESTORE_EXPANDED_LIMIT:
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
            if skip_external_links:
                skipped.append(member.name)
                continue
            raise ValueError("External archive link rejected")
        resolved = ((target.parent if member.issym() else destination) / link).resolve()
        if not resolved.is_relative_to(destination.resolve()):
            if skip_external_links:
                skipped.append(member.name)
                continue
            raise ValueError("External archive link rejected")
        target.parent.mkdir(parents=True, exist_ok=True)
        if member.issym():
            target.symlink_to(link)
        elif resolved.is_file():
            shutil.copyfile(resolved, target)
        else:
            raise ValueError("Invalid archive hard link")
    return skipped


class ShareWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    ready = pyqtSignal(str, object)
    failed = pyqtSignal(str)

    def __init__(self, screens, code="", dest=None, styles=None, recheck=False,
                 primary_screen=0, manage_session=False, excluded_panels=None, accept_review=False):
        super().__init__()
        self.screens, self.code, self.dest = screens, code, dest
        self.styles = styles or []
        self.recheck = recheck
        self.primary_screen = primary_screen
        self.manage_session = manage_session
        self.excluded_panels = excluded_panels
        self.accept_review = accept_review

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
                community = community_extension_plan(manifest, current, issues)
                self.ready.emit(str(self.dest), {"manifest": manifest, "issues": issues,
                                "setup": setup, "extensions": extensions, "native": native,
                                "community": community, "styles": self.styles,
                                "plan": design_install_plan(manifest, current, self.styles)})
            else:
                with tempfile.TemporaryDirectory(prefix="sdd-share-") as tmp:
                    root = Path(tmp)
                    session = PlasmaSession() if self.manage_session else None
                    settings_review = []
                    try:
                        if session:
                            self.log.emit('Aktuelles Layout sichern: Plasma wird während der lokalen Paketerstellung kurz angehalten.')
                            session.stop()
                        manifest = public_design(root, self.screens, self.log.emit, self.primary_screen,
                                                 self.excluded_panels, settings_review)
                    finally:
                        if session:
                            session.start()
                    if settings_review and not self.accept_review:
                        self.ready.emit('', {'manifest': manifest, 'settings_review': settings_review})
                        return
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

            layout_path = HOME / ".config/plasma-org.kde.plasma.desktop-appletsrc"
            portable_layout = None
            wallpaper_assets: list[tuple[Path, str]] = []
            if layout_path.is_file() and any(p == layout_path for _, p in paths):
                included_wallpapers = ((HOME / ".local/share/wallpapers",)
                                       if any(p == HOME / ".local/share/wallpapers" for _, p in paths)
                                       else ())
                portable_layout, wallpaper_assets = portable_wallpaper_config(
                    layout_path.read_text(encoding="utf-8", errors="strict"), included_wallpapers)

            total = len(paths) + len(wallpaper_assets) + (1 if self.with_packages else 0) + 1
            done = 0

            manifest_paths = [str(p.relative_to(HOME)) for _, p in paths]
            if wallpaper_assets and ".local/share/wallpapers" not in manifest_paths:
                manifest_paths.append(".local/share/wallpapers")
            path_categories = {str(p.relative_to(HOME)): cat for cat, p in paths}
            if wallpaper_assets:
                path_categories[".local/share/wallpapers"] = "cat_plasma"

            manifest = {
                "app": APP_NAME,
                "version": VERSION,
                "created": datetime.now().isoformat(timespec="seconds"),
                "hostname": socket.gethostname(),
                "user": os.environ.get("USER", ""),
                "categories": self.categories,
                "with_packages": self.with_packages,
                "paths": manifest_paths,
                "path_categories": path_categories,
                "portable_home_token": bool(portable_layout and HOME_TOKEN in portable_layout),
            }

            with tarfile.open(self.dest, "w:gz") as tar:
                for cat, p in paths:
                    rel = p.relative_to(HOME)
                    self.log.emit(f"  + {rel}")
                    try:
                        if p == layout_path and portable_layout is not None:
                            data = portable_layout.encode("utf-8")
                            info = tarfile.TarInfo(f"home/{rel}")
                            info.size = len(data)
                            info.mode = p.stat().st_mode & 0o777
                            info.mtime = int(p.stat().st_mtime)
                            tar.addfile(info, io.BytesIO(data))
                        else:
                            tar.add(p, arcname=f"home/{rel}")
                    except (PermissionError, OSError) as e:
                        self.log.emit(f"{T('log_skipped')} ({e})")
                    done += 1
                    self.progress.emit(int(done / total * 100))

                for source, rel in wallpaper_assets:
                    self.log.emit(f"  + {rel}")
                    tar.add(source, arcname="home/" + rel)
                    done += 1
                    self.progress.emit(int(done / total * 100))

                # Die App selbst beilegen: auf dem neuen Gerät genügt dann
                # `tar xzf … app/saveyourkdedesign.py` und ein Doppelklick.
                try:
                    tar.add(Path(__file__).resolve(),
                            arcname="app/saveyourkdedesign.py")
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


class PlasmaSession:
    """Pause only the desktop shell, never KWin or the user's login session."""
    def __init__(self):
        self.mode = None
        self.activity = ''
        self.dbus = None

    def running(self):
        result = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'plasmashell'],
                                capture_output=True, timeout=10)
        if result.returncode not in (0, 1):
            raise RuntimeError('Cannot check the Plasma desktop process')
        return result.returncode == 0

    def stop(self):
        if not shutil.which('pgrep') or not shutil.which('plasmashell'):
            raise RuntimeError('Plasma/procps fehlt. Bitte plasmashell und procps/procps-ng installieren und erneut importieren.')
        for tool in ('qdbus6', 'qdbus', 'qdbus-qt6', 'qdbus-qt5'):
            if shutil.which(tool):
                value = _run_cmd([tool, 'org.kde.ActivityManager', '/ActivityManager/Activities',
                                  'org.kde.ActivityManager.Activities.CurrentActivity'], 10) or ''
                value = value.strip()
                if re.fullmatch(r'[0-9a-fA-F-]{36}', value):
                    self.activity = value
                    self.dbus = tool
                    break
        if not self.activity:
            raise RuntimeError('Aktive KDE-Aktivität nicht ermittelbar. Bitte Qt D-Bus-Werkzeuge installieren und in einer KDE-Sitzung erneut importieren.')
        if shutil.which('systemctl'):
            result = subprocess.run(['systemctl', '--user', 'is-active', 'plasma-plasmashell.service'],
                                    capture_output=True, timeout=15)
            if result.returncode == 0:
                self.mode = 'systemd'
                subprocess.run(['systemctl', '--user', 'stop', 'plasma-plasmashell.service'],
                               check=True, capture_output=True, timeout=45)
        if self.mode is None:
            tool = next((name for name in ('kquitapp6', 'kquitapp5') if shutil.which(name)), None)
            if not tool:
                raise RuntimeError('kquitapp fehlt: KDE-Werkzeuge installieren und Import erneut starten.')
            self.mode = 'direct'
            subprocess.run([tool, 'plasmashell'], check=True, capture_output=True, timeout=30)
        for _ in range(50):
            if not self.running():
                return
            QThread.msleep(100)
        raise RuntimeError('Plasma läuft weiter. Keine Design-Dateien wurden geschrieben; bitte erneut versuchen.')

    def start(self):
        if self.mode == 'systemd':
            subprocess.run(['systemctl', '--user', 'start', 'plasma-plasmashell.service'],
                           check=True, capture_output=True, timeout=45)
        elif self.mode == 'direct' and not self.running():
            subprocess.Popen(['plasmashell'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        if self.mode:
            for _ in range(100):
                if self.running():
                    self.mode = None
                    return
                QThread.msleep(100)
            raise RuntimeError('Plasma konnte nicht gestartet werden. Im Terminal: plasmashell; alternativ ab- und anmelden.')

    def verify(self, layout: str, screen: int, views: str = ''):
        """Check the loaded shell, not just the files written before startup."""
        expected_panels, expected_images = {}, []
        expected_geometry = {}
        blocks = _kconfig_blocks(layout)[1]
        view_blocks = _kconfig_blocks(views)[1]
        for group, lines in blocks:
            match = re.fullmatch(r'\[Containments\]\[(\d+)\]', group)
            if not match:
                continue
            values = dict(line.split('=', 1) for line in lines if '=' in line)
            if values.get('lastScreen') != str(screen):
                continue
            if values.get('plugin') == 'org.kde.panel':
                order = _block_values(blocks, group + '[General]').get('AppletOrder', '')
                expected_panels[int(match[1])] = [int(i) for i in order.split(';') if i.isdigit()]
                view = _block_values(view_blocks, f'[PlasmaViews][Panel {match[1]}]')
                geometry = {}
                edge = {'3': 'top', '4': 'bottom', '5': 'left', '6': 'right'}.get(values.get('location'))
                if edge:
                    geometry['location'] = edge
                for key, prop, mapping in (
                        ('alignment', 'alignment', {'1': 'left', '2': 'right', '132': 'center'}),
                        ('panelLengthMode', 'lengthMode', {'0': 'fill', '1': 'fit', '2': 'custom'})):
                    if view.get(key) in mapping:
                        geometry[prop] = mapping[view[key]]
                if 'floating' in view:
                    geometry['floating'] = view['floating'] in {'1', 'true'}
                expected_geometry[int(match[1])] = geometry
            elif values.get('activityId') == self.activity:
                image = _block_values(blocks, group + '[Wallpaper][org.kde.image][General]').get('Image')
                if image:
                    expected_images.append(image)
        script = ('var ps=panels().map(function(p){p.currentConfigGroup=["General"];'
                  'return {id:p.id,screen:p.screen,order:p.readConfig("AppletOrder",""),widgets:p.widgetIds,'
                  'location:p.location,alignment:p.alignment,lengthMode:p.lengthMode,floating:p.floating};});'
                  'var ds=desktopsForActivity(currentActivity()).map(function(d){'
                  'd.currentConfigGroup=["Wallpaper",d.wallpaperPlugin,"General"];'
                  'return {screen:d.screen,image:d.readConfig("Image","")};});'
                  'print(JSON.stringify({panels:ps,desktops:ds}));')
        for _ in range(15):
            raw = _run_cmd([self.dbus, 'org.kde.plasmashell', '/PlasmaShell',
                            'org.kde.PlasmaShell.evaluateScript', script], 5) or ''
            try:
                state = json.loads(raw)
                actual = {int(p['id']): p for p in state['panels'] if p['screen'] == screen}
                images = [d['image'] for d in state['desktops'] if d['screen'] == screen]
                order_ok = all(
                    (not order or order == ([int(i) for i in actual[pid]['order'].split(';') if i.isdigit()]
                                           if actual[pid]['order'] else actual[pid]['widgets']))
                    and set(order).issubset(set(actual[pid]['widgets']))
                    for pid, order in expected_panels.items() if pid in actual)
                geometry_ok = all(actual[pid].get(key) == value
                                  for pid, settings in expected_geometry.items() if pid in actual
                                  for key, value in settings.items())
                if set(actual) == set(expected_panels) and order_ok and geometry_ok and all(img in images for img in expected_images):
                    return
            except (ValueError, TypeError, KeyError):
                pass
            QThread.msleep(500)
        raise RuntimeError('Geladenes Design stimmt nicht mit dem Import überein (Panels, Widget-Reihenfolge oder Wallpaper). '
                           'Bitte das Importprotokoll senden; die vorherige Sicherung bleibt über Wiederherstellen verfügbar.')


class RestoreWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal(bool)   # True wenn Paketlisten enthalten
    failed = pyqtSignal(str)

    def __init__(self, archive: str, categories: list[str] | None = None,
                 rollback: bool = True, public: bool = False,
                 screens=None, styles=None, primary_screen=0, manage_session=False, preserve_pins=True):
        super().__init__()
        self.archive = archive
        self.categories = categories   # None = alles aus dem Archiv
        self.rollback = rollback
        self.public = public
        self.screens = screens or []
        self.styles = styles or []
        self.primary_screen = primary_screen
        self.manage_session = manage_session
        self.preserve_pins = preserve_pins

    def run(self):
        session = PlasmaSession() if self.manage_session else None
        self.imported_kwin = {}
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
                    skipped_links = safe_extract(
                        tar, tmpp, skip_external_links=not self.public)
                if skipped_links:
                    self.log.emit(
                        f"  ! {len(skipped_links)} unsichere externe Alt-Links wurden ausgelassen; "
                        "das Archiv wurde sonst vollständig entpackt. / "
                        f"Skipped {len(skipped_links)} unsafe legacy external links; "
                        "the rest of the archive was extracted.")
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
                    path_categories = manifest.get("path_categories", {})
                    if (isinstance(path_categories, dict) and path_categories
                            and all(isinstance(k, str) and isinstance(v, str)
                                    for k, v in path_categories.items())):
                        rel_paths = [r for r in rel_paths
                                     if path_categories.get(r) in self.categories]
                    else:
                        wanted = set()
                        for cat in self.categories:
                            wanted.update(CATEGORIES.get(cat, []))
                        rel_paths = [r for r in rel_paths if r in wanted]

                # Resolve every public destination before rollback or writes.
                # Safe dotfile-manager links inside HOME are preserved; links
                # escaping HOME and cycles remain blocked.
                for rel in rel_paths:
                    safe_public_restore_target(rel)

                kwin = src_home / '.config/kwinrc'
                if self.public and '.config/kwinrc' in rel_paths and kwin.is_file():
                    current = HOME / '.config/kwinrc'
                    for group, key, value in read_kconfig(kwin):
                        self.imported_kwin.setdefault(group, {})[key] = value
                    desired = self.imported_kwin.get('[Desktops]', {}).get('Number')
                    if desired and self.manage_session:
                        dbus = next((shutil.which(name) for name in ('qdbus6', 'qdbus', 'qdbus-qt6', 'qdbus-qt5')
                                     if shutil.which(name)), None)
                        current_count = (_run_cmd([dbus, 'org.kde.KWin', '/VirtualDesktopManager',
                                                  'org.kde.KWin.VirtualDesktopManager.count'], 30) if dbus else None)
                        if current_count is None or not current_count.strip().isdigit():
                            raise ValueError('Virtuelle Arbeitsflächen nicht prüfbar. Qt-DBus-Werkzeuge installieren und in einer KDE-Sitzung erneut importieren.')
                        if int(current_count.strip()) > int(desired):
                            raise ValueError(f'Dieses Design verwendet {desired} virtuelle Arbeitsflächen. '
                                             'Vor dem Import in Systemeinstellungen → Fensterverwaltung → Virtuelle Arbeitsflächen '
                                             'überzählige Arbeitsflächen entfernen. Noch keine Design-Einstellungen geändert.')
                    kwin.write_text(merge_design_kconfig(
                        kwin.read_text(encoding='utf-8'),
                        current.read_text(encoding='utf-8') if current.is_file() else ''), encoding='utf-8')

                if session and '.config/plasma-org.kde.plasma.desktop-appletsrc' in rel_paths:
                    self.log.emit('Plasma wird kurz angehalten; offene Programme bleiben geöffnet.')
                    session.stop()

                if self.public or manifest.get("portable_home_token") is True:
                    for rel in rel_paths:
                        if rel in {".config/" + n for n in VISUAL_CONFIGS}:
                            config = src_home / rel
                            if not config.is_file():
                                continue
                            if config.stat().st_size > 4_000_000:
                                raise ValueError("Configuration too large")
                            config.write_text(config.read_text(encoding="utf-8").replace(
                                HOME_TOKEN, str(HOME)), encoding="utf-8")
                            text = config.read_text(encoding='utf-8')
                            if ROOT_DISK_TOKEN in text:
                                target_uuid = root_disk_uuid()
                                if not target_uuid:
                                    raise ValueError('Systemlaufwerk für das Monitor-Widget nicht bestimmbar. '
                                                     'Datenträger-Sensor im Widget am Ziel auswählen; Design noch nicht geschrieben.')
                                config.write_text(text.replace(ROOT_DISK_TOKEN, target_uuid), encoding='utf-8')
                    layout_rel = ".config/plasma-org.kde.plasma.desktop-appletsrc"
                    layout = src_home / layout_rel
                    if self.public and layout_rel in rel_paths and layout.is_file():
                        if self.manage_session:
                            layout.write_text(repair_launcher_icons(layout.read_text(encoding='utf-8'), src_home), encoding='utf-8')
                        target = HOME / layout_rel
                        target_text = target.read_text(encoding="utf-8") if target.is_file() else ""
                        source_primary = manifest.get("profile", {}).get("primary_screen", 0)
                        target_primary = self.primary_screen
                        mapping = {}
                        layout.write_text(merge_primary_applet_config(
                            layout.read_text(encoding="utf-8"), target_text,
                            source_primary, target_primary, mapping,
                            session.activity if session else '', self.preserve_pins), encoding="utf-8")
                        shell_rel = ".config/plasmashellrc"
                        if shell_rel in rel_paths:
                            shell = src_home / shell_rel
                            current_shell = HOME / shell_rel
                            removed = _screen_containments(_kconfig_blocks(target_text)[1], target_primary)
                            shell.write_text(merge_panel_views(
                                shell.read_text(encoding="utf-8"),
                                current_shell.read_text(encoding="utf-8") if current_shell.is_file() else "",
                                mapping, removed), encoding="utf-8")
                        # Older manifests used the wrong AppletOrder group.
                        expected_layout = manifest.get("layout") if _version_tuple(manifest.get('version', '')) >= (1, 7, 9) else None
                        if expected_layout is not None:
                            applied_layout = panel_layout_snapshot(
                                layout.read_text(encoding="utf-8"),
                                (src_home / shell_rel).read_text(encoding="utf-8")
                                if (src_home / shell_rel).is_file() else "",
                                target_primary)
                            if applied_layout != expected_layout:
                                raise ValueError("Panel layout verification failed; the design was not written")
                            self.log.emit(f"  + Panel layout verified: {len(applied_layout)} panel(s), widget order preserved")
                        for warning in manifest.get("layout_warnings", []):
                            self.log.emit("  ! Layout warning from design source: " + warning)

                if src_home.exists():
                    if self.rollback:
                        self.log.emit(T("log_rollback"))
                        saved = make_rollback(rel_paths, self.categories
                                              or manifest.get("categories", []),
                                              dereference=True)
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
                    if self.public and self.manage_session and self.imported_kwin:
                        dbus = next((shutil.which(name) for name in ('qdbus6', 'qdbus', 'qdbus-qt6', 'qdbus-qt5')
                                     if shutil.which(name)), None)
                        if not dbus:
                            raise ValueError('qdbus fehlt: Qt-DBus-Werkzeuge mit dem Paketmanager installieren, dann Import wiederholen.')
                        activate_kwin_design(self.imported_kwin, dbus,
                                             {row['name'] for row in manifest.get('requirements', []) if row.get('kind') == 'effect'})
                        actual = {(group, key): value for group, key, value in read_kconfig(HOME / '.config/kwinrc')}
                        mismatches = [group + '/' + key for group, values in self.imported_kwin.items()
                                      for key, value in values.items() if actual.get((group, key)) != value
                                      and not (group == '[Desktops]' and re.match(r'(?:Id|Name)_', key))]
                        if mismatches:
                            raise ValueError('KWin-Einstellungen wurden nach dem Laden verändert: ' + ', '.join(mismatches[:10]) +
                                             '. Erweiterungsversionen abgleichen und Import nach erneuter Anmeldung wiederholen.')

                if session:
                    session.start()
                    if self.public and layout.is_file():
                        session.verify(layout.read_text(encoding='utf-8'), self.primary_screen,
                                       (src_home / '.config/plasmashellrc').read_text(encoding='utf-8')
                                       if (src_home / '.config/plasmashellrc').is_file() else '')
                        self.log.emit('Geladene Panels, Widget-Reihenfolge und Wallpaper geprüft.')

                self.progress.emit(100)
                self.finished_ok.emit(has_packages)
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            if session and session.mode:
                try:
                    session.start()
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

        # Update KDE's service/package cache before KWin is asked to reload so
        # newly copied scripts and effects are discoverable immediately.
        for sycoca in ("kbuildsycoca6", "kbuildsycoca5"):
            if shutil.which(sycoca):
                try:
                    subprocess.run([sycoca], capture_output=True, timeout=120)
                except (OSError, subprocess.SubprocessError) as e:
                    self.log.emit(f"{T('log_skipped')} {sycoca} ({e})")
                break

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

    def _copy_into_home(self, entry: Path, src_root: Path):
        rel = entry.relative_to(src_root)
        target = safe_public_restore_target(str(rel))
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
                # Same-directory replace prevents a truncated configuration if
                # the copy is interrupted. Existing safe symlinks were already
                # resolved by _copy_into_home and therefore remain intact.
                tmp = dst.with_name(dst.name + ".syd-new-" + uuid.uuid4().hex)
                shutil.copy2(src, tmp)
                os.replace(tmp, dst)
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
        self.share_keep_pins.setEnabled(not busy)
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
        self.share_keep_pins = QCheckBox('Eigene angeheftete Programme beim Import behalten / Keep my pinned apps')
        self.share_keep_pins.setChecked(True)
        self.share_keep_pins.setToolTip('Deaktivieren: ohne angeheftete Programme starten. Verknüpfungen aus dem Code werden nie übernommen.')
        layout.addWidget(self.share_keep_pins)
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
        if QMessageBox.question(self, APP_NAME, T("share_consent") + '\n\n'
                                'Damit das aktuelle Layout gespeichert wird, wird die Plasma-Oberfläche während '
                                'der Paketerstellung angehalten und danach wieder gestartet. Offene Programme bleiben geöffnet. / '
                                'The desktop shell briefly restarts to save the current layout.',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        excluded = []
        source = HOME / '.config/plasma-org.kde.plasma.desktop-appletsrc'
        views = HOME / '.config/plasmashellrc'
        if source.is_file() and views.is_file():
            duplicates = duplicate_panel_ids(source.read_text(encoding='utf-8'), views.read_text(encoding='utf-8'), primary_screen_index())
            if duplicates:
                choice = QMessageBox.question(self, APP_NAME,
                    f'{len(duplicates)} zusätzliche Panels mit gleicher Position, Anordnung und Widget-Liste erkannt '
                    f'(IDs: {", ".join(duplicates)}). Andere Widget-Einstellungen können abweichen. '
                    'Diese zusätzlichen Panels NUR aus dem Export entfernen? Dein Desktop bleibt unverändert. '
                    '/ Exclude these matching additional panels from the export only?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel)
                if choice == QMessageBox.StandardButton.Cancel:
                    return
                if choice == QMessageBox.StandardButton.Yes:
                    excluded = duplicates
        self._start_share(ShareWorker(screen_profile(), primary_screen=primary_screen_index(), manage_session=True,
                                     excluded_panels=excluded), "share_upload")

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
        if details.get('settings_review'):
            rows = details['settings_review']
            dialog = QMessageBox(self)
            dialog.setWindowTitle('Design-Einstellungen prüfen / Review design settings')
            dialog.setText('Noch nichts hochgeladen. Für nicht portable Einstellungen wurden konkrete Lösungen ermittelt. '
                           'Unter Details stehen Erweiterung, Schlüssel und Vorgehen. '
                           '„Ja“ bestätigt: lokale Filter zurücksetzen und nicht sicher übertragbare Werte auslassen. '
                           '„Nein“: Export abbrechen und zunächst Einstellungen/Erweiterung anpassen. '
                           'Ein Export mit Auslassungen ist keine vollständige Kopie.')
            dialog.setInformativeText('\n\n'.join(row['component'] + ' / ' + row['key'] + ': ' + row['solution']
                                                   for row in rows[:3]) +
                                      (f'\n\nWeitere {len(rows) - 3} Einträge unter Details.' if len(rows) > 3 else ''))
            dialog.setDetailedText('\n\n'.join(row['component'] + ' / ' + row['key'] + '\n' + row['solution'] for row in rows))
            dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            dialog.setDefaultButton(QMessageBox.StandardButton.No)
            if dialog.exec() == QMessageBox.StandardButton.Yes:
                previous = self.share_worker
                self._start_share(ShareWorker(screen_profile(), primary_screen=previous.primary_screen,
                                  manage_session=True, excluded_panels=previous.excluded_panels, accept_review=True), 'share_upload')
            return
        self.share_log.append(f"{T('share_details')}: {len(manifest['paths'])} files")
        self.share_log.append(f"{T('share_omitted')}: {manifest.get('omitted_settings', 0)} settings")
        for warning in manifest.get("layout_warnings", []):
            self.share_log.append("! Layout QC: " + warning)
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
        community = details.get("community", {})
        if details.get("plan") and tuple(details["plan"][3]) in self._attempted_installs:
            details["plan"] = None
        if native.get("command") and tuple(native["command"]) in self._attempted_installs:
            self.settings.setValue("resume_import_after_login", True)
            native["command"] = None
            native.setdefault("notes", []).append(
                "Die Installation wurde bereits ausgeführt, aber die Komponente ist noch nicht verfügbar. "
                "Bitte nach einem neuen Plasma-Login dieses Programm öffnen: Der Import wird automatisch fortgesetzt. / "
                "After a new Plasma login, reopen this app to resume the import automatically.")
        if community.get("command") and tuple(community["command"]) in self._attempted_installs:
            community["command"] = None
            community.setdefault("notes", []).append(
                "Die Gemeinschaftspakete wurden bereits aufgerufen, die Erweiterung ist aber noch nicht verfügbar. "
                "Prüfe die Terminalausgabe oder melde dich neu in Plasma an.")
        for note in setup.get("notes", []):
            self.share_log.append(note)
        if details["issues"]:
            message = T("share_blocked") + "\n".join(details["issues"])
            if setup.get("notes"):
                message += "\n\n" + "\n".join(setup["notes"])
            if native.get("notes"):
                message += "\n\n" + "\n".join(native["notes"])
            if community.get("notes"):
                message += "\n\n" + "\n".join(community["notes"])
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
            if community.get("command"):
                dialog = QMessageBox(self)
                dialog.setWindowTitle(APP_NAME)
                dialog.setIcon(QMessageBox.Icon.Question)
                source_name = ("Fedora-COPR-Pakete" if community.get("kind") == "fedora_copr"
                               else "AUR-Gemeinschaftspakete")
                dialog.setText("Die fehlenden Erweiterungen sind als " + source_name + " verfügbar:\n\n"
                               + "\n".join(community["packages"]) + "\n\nJetzt im Terminal installieren?")
                dialog.setInformativeText("Im Terminal bestätigst du die Pakete und gibst dein Passwort ein. Danach wird automatisch weitergeprüft.")
                dialog.setDetailedText("Befehl: " + shlex.join(community["command"])
                                       + "\n\nQuellen:\n" + "\n".join(community["urls"])
                                       + "\n\n" + "\n".join(community["notes"]))
                dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                dialog.setDefaultButton(QMessageBox.StandardButton.No)
                if dialog.exec() == QMessageBox.StandardButton.Yes:
                    self._attempted_installs.add(tuple(community["command"]))
                    self._start_terminal_install_and_recheck(community, Path(value))
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
            dialog = QMessageBox(self)
            dialog.setWindowTitle(APP_NAME)
            dialog.setIcon(QMessageBox.Icon.Warning)
            guidance = [*native.get("notes", []), *community.get("notes", [])]
            if community.get("manual_command"):
                guidance.append("Terminal-Befehl: " + community["manual_command"])
            dialog.setText("Einige benötigte Erweiterungen konnten nicht automatisch installiert werden."
                           + (("\n\nSo gehst du weiter:\n" + "\n".join(guidance)) if guidance else ""))
            dialog.setInformativeText("Unter „Details“ stehen die Komponentennamen. Es wurden keine Design-Einstellungen geändert.")
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

    def _start_terminal_install_and_recheck(self, plan: dict, archive: Path):
        self._set_busy(True)
        self.action_process = QProcess(self)
        self.action_process.finished.connect(
            lambda *_: self._start_share(ShareWorker(screen_profile(), dest=archive,
                                      styles=QStyleFactory.keys(), recheck=True), "share_download"))
        self.action_process.errorOccurred.connect(lambda *_: self._terminal_install_failed(plan))
        self.action_process.start(plan["terminal"], ["--separate", "-e", *plan["command"]])

    def _terminal_install_failed(self, plan: dict):
        self._set_busy(False)
        QMessageBox.warning(self, APP_NAME,
                            "Das Installationsterminal konnte nicht geöffnet werden. Führe diesen Befehl aus:\n\n"
                            + shlex.join(plan["command"]))

    def _clean_share_temp(self):
        if self.share_temp is not None:
            self.share_temp.cleanup()
            self.share_temp = None

    def _share_failed(self, error):
        self._set_busy(False)
        self.share_log.append(str(error))
        self._clean_share_temp()
        if 'Export-Prüfung abgeschlossen:' in str(error):
            dialog = QMessageBox(self)
            dialog.setWindowTitle(T('share_error'))
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.setText(str(error).split('\n\n', 1)[0])
            dialog.setInformativeText('Die vollständige Liste steht unter Details. Dein Desktop wurde nicht verändert; es wurde nichts veröffentlicht.')
            dialog.setDetailedText(str(error))
            dialog.exec()
        else:
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
        if QMessageBox.question(self, APP_NAME,
                'Für die Übernahme wird die Plasma-Oberfläche kurz angehalten und wieder gestartet. '
                'Offene Anwendungen bleiben geöffnet. Jetzt anwenden? / Restart the desktop shell and apply?'
                ) != QMessageBox.StandardButton.Yes:
            return
        self._set_busy(True)
        self.restore_progress.setValue(0)
        self.restore_log.clear()
        self._public_restore = public
        self.restore_worker = RestoreWorker(archive, categories, rollback, public,
                                            screen_profile(), styles if styles is not None else QStyleFactory.keys(),
                                            primary_screen_index(), manage_session=True,
                                            preserve_pins=self.share_keep_pins.isChecked() if public else True)
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
        QMessageBox.critical(self, APP_NAME, T("msg_restore_failed") + '\n\n' + err[-2500:])

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
    installed = HOME / ".local/share/savedesktopdesign/saveyourkdedesign.py"
    legacy = HOME / ".local/share/savedesktopdesign/savedesktopdesign.py"
    if app_file.resolve() == legacy.resolve() and not installed.exists():
        shutil.copy2(app_file, installed)
    if app_file.resolve() not in {installed.resolve(), legacy.resolve()}:
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
