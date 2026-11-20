#!/usr/bin/env python3
"""Installe chill&flix pour le compte courant, sans copier de données privées."""
import argparse
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_ID = 'fr.local.ChillFlix'
APP_FILES = ('cinema.py', 'player.py', 'audio_settings.py', 'icon.svg', 'VERSION')

def check_dependencies():
    missing = []
    if sys.version_info < (3, 10): missing.append('Python 3.10 ou plus récent')
    try:
        gi = importlib.import_module('gi'); gi.require_version('Gtk', '3.0')
        importlib.import_module('gi.repository.Gtk')
    except (ImportError, ValueError): missing.append('PyGObject et GTK 3')
    if not shutil.which('pactl'): missing.append('pactl (libpulse ou pulseaudio-utils)')
    if not shutil.which('flatpak'):
        missing.append('Flatpak et VLC (org.videolan.VLC)')
    else:
        result = subprocess.run(['flatpak', 'info', 'org.videolan.VLC'], capture_output=True)
        if result.returncode: missing.append('VLC via Flatpak (org.videolan.VLC)')
    return missing

def desktop_quote(value):
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'): value = value.replace(char, '\\' + char)
    return '"' + value + '"'

def desktop_entry(prefix):
    icon = str(prefix / 'icon.svg').replace('\\', '\\\\')
    return '\n'.join([
        '[Desktop Entry]', 'Version=1.0', 'Type=Application', 'Name=chill&flix',
        'Comment=Vidéothèque locale — ALPHA TEST',
        'Exec=' + desktop_quote(sys.executable) + ' ' + desktop_quote(prefix / 'cinema.py'),
        'Icon=' + icon, 'Terminal=false', 'Categories=AudioVideo;Video;',
        'StartupNotify=true', 'StartupWMClass=fr.local.ChillFlix', '',
    ])

def install(prefix, data_home, desktop=None):
    source = Path(__file__).resolve().parent
    prefix = Path(prefix).expanduser().resolve()
    if any('\n' in str(path) or '\r' in str(path) for path in (prefix, data_home)):
        raise ValueError('Le chemin d’installation contient un retour à la ligne.')
    prefix.mkdir(parents=True, exist_ok=True)
    for name in APP_FILES:
        destination = prefix / name
        if (source / name).resolve() != destination.resolve():
            shutil.copy2(source / name, destination)
    applications = Path(data_home) / 'applications'; applications.mkdir(parents=True, exist_ok=True)
    entry = desktop_entry(prefix)
    (applications / (APP_ID + '.desktop')).write_text(entry, encoding='utf-8')
    if desktop:
        desktop = Path(desktop); desktop.mkdir(parents=True, exist_ok=True)
        shortcut = desktop / (APP_ID + '.desktop')
        shortcut.write_text(entry, encoding='utf-8'); shortcut.chmod(0o755)
    return prefix

def main():
    parser = argparse.ArgumentParser(description='Installer chill&flix — ALPHA TEST')
    parser.add_argument('--check', action='store_true', help='Vérifier seulement les dépendances')
    parser.add_argument('--prefix', type=Path, help='Dossier d’installation personnalisé')
    parser.add_argument('--no-desktop', action='store_true', help='Ne pas créer de raccourci sur le bureau')
    args = parser.parse_args()
    missing = check_dependencies()
    if missing:
        print('Dépendances manquantes :\n- ' + '\n- '.join(missing), file=sys.stderr)
        print('Consulte README.md pour les commandes d’installation.', file=sys.stderr)
        return 1
    if args.check:
        print('Toutes les dépendances sont disponibles.'); return 0
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))).expanduser()
    prefix = args.prefix or data_home / 'chill-flix/app'
    desktop = None
    if not args.no_desktop and shutil.which('xdg-user-dir'):
        result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            candidate = Path(result.stdout.strip()).expanduser()
            if candidate.resolve() != Path.home().resolve(): desktop = candidate
    installed = install(prefix, data_home, desktop)
    print('chill&flix — ALPHA TEST installé dans ' + str(installed))
    print('Lance chill&flix depuis le menu des applications' + (' ou le bureau.' if desktop else '.'))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
