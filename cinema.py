#!/usr/bin/env python3
"""chill&flix — bibliothèque vidéo locale, application GTK 3."""
import json
import os
import re
import subprocess
import threading
from pathlib import Path
import audio_settings
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango

EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.wmv'}
DATA = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'chill-flix'
CATEGORIES = ['Film', 'Série', 'Animé']

def clean_title(path):
    path = Path(path)
    name = path.stem.replace('.', ' ').replace('_', ' ')
    year = re.search(r'\b(?:19|20)\d{2}\b', name)
    parent_year = re.search(r'\b(?:19|20)\d{2}\b', path.parent.name)
    release = re.search(r'(?i)\b(?:2160p|1080p|720p|480p|bluray|blu-ray|webrip|web-dl|hdtv|x264|x265)\b', name)
    end = min([m.start() for m in [year, release] if m] or [len(name)])
    title = name[:end].strip(' -[()')
    y = year or parent_year
    return (title or name) + (f' ({y.group()})' if y else '')


def find_subtitle(path):
    path = Path(path)
    candidates = [p for p in path.parent.iterdir()
                  if p.is_file() and p.suffix.lower() in {'.srt', '.ass', '.ssa', '.vtt'}
                  and (p.stem.casefold() == path.stem.casefold()
                       or p.stem.casefold().startswith(path.stem.casefold() + '.'))]
    candidates.sort(key=lambda p: (not bool(re.search(r'(?i)[. _-](fr|fra|fre|french)([. _-]|$)', p.stem)), p.name))
    return str(candidates[0]) if candidates else ''

def scan(root, category):
    results = []
    errors = []
    for folder, _, names in os.walk(root, onerror=lambda e: errors.append(str(e))):
        for name in names:
            p = Path(folder) / name
            if p.suffix.lower() in EXTENSIONS:
                results.append({'title': clean_title(p), 'target': str(p.resolve()), 'category': category, 'source': 'Fichier', 'favorite': False, 'subtitle': find_subtitle(p)})
    return results, errors

CSS = b'''
window {background: #101118; color: #f3f2f7;}
box.sidebar {background: #171923; padding: 26px 18px;}
label.brand {font-size: 25px; font-weight: 800; color: #fb626e;}
label.heading {font-size: 32px; font-weight: 800;}
label.subtle {color: #a3a7b7; font-size: 13px;}
label.hero {font-size: 25px; font-weight: 700;}
box.banner {background: linear-gradient(115deg,#462139,#222844); border-radius: 18px; padding: 28px;}
button {background: #282b39; color: #f5f4fa; border: none; border-radius: 9px; padding: 11px 16px; box-shadow: none; text-shadow: none;}
button:hover {background: #393d50;}
button.accent {background: #e7475b; color: white; font-weight: bold;}
button.nav {background: #222536; padding: 22px 18px; font-size: 22px; font-weight: bold;}
button.nav:checked {background: #373041; color: #ff8591;}
entry, combobox button {background: #20232f; color: #f4f3f8; border: 1px solid #383c4e; border-radius: 9px; padding: 10px;}
box.card {background: #1d202d; border-radius: 13px; padding: 16px;}
label.poster {background: linear-gradient(140deg,#453956,#242f4b); border-radius: 9px; color: #eeacb7; font-size: 42px; font-weight: 800; min-height: 115px;}
flowboxchild {padding: 8px;}
flowboxchild:selected {background: transparent;}
dialog {background: #1b1e29;}
'''

class Cinema(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='fr.local.ChillFlix', flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.items = []
        self.section = 'Films'
        self.load_error = None
        try:
            self.items = json.loads((DATA / 'library.json').read_text())
            if not isinstance(self.items, list) or any(not isinstance(i, dict) or not {'title','target','source','category'} <= i.keys() for i in self.items):
                raise ValueError('Format de bibliothèque invalide')
            self.items = [i for i in self.items if i['source'] == 'Fichier' and not i['target'].startswith(('http:', 'https:'))]
        except FileNotFoundError:
            pass
        except (ValueError, OSError) as e:
            self.items = []
            self.load_error = str(e)

    def save(self):
        if self.load_error:
            self.message('Enregistrement bloqué', 'Le fichier de bibliothèque doit être réparé avant toute modification.\n' + self.load_error)
            return False
        try:
            DATA.mkdir(parents=True, exist_ok=True)
            p = DATA / 'library.tmp'
            p.write_text(json.dumps(self.items, ensure_ascii=False, indent=2))
            p.replace(DATA / 'library.json')
            return True
        except OSError as e:
            self.message('Enregistrement impossible', str(e))
            return False

    def do_activate(self):
        if hasattr(self, 'win'):
            self.win.present()
            return
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win = Gtk.ApplicationWindow(application=self, title='chill&flix — ALPHA TEST')
        self.win.set_default_size(1200, 790)
        self.win.set_size_request(840, 560)
        self.win.set_icon_from_file(str(Path(__file__).with_name('icon.svg')))
        layout = Gtk.Box()
        self.win.add(layout)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        side.set_size_request(206, -1)
        side.get_style_context().add_class('sidebar')
        layout.pack_start(side, False, False, 0)
        self.label(side, 'chill&flix', 'brand')
        self.label(side, 'ALPHA TEST · 0.1.0', 'subtle')
        self.label(side, 'BIBLIOTHÈQUE', 'subtle').set_margin_top(35)
        self.navs = []
        for title in ['Films', 'Séries', 'Animé']:
            b = Gtk.RadioButton.new_with_label_from_widget(self.navs[0] if self.navs else None, title)
            b.set_mode(False)
            b.get_style_context().add_class('nav')
            b.connect('toggled', self.navigate, title)
            self.navs.append(b)
            side.pack_start(b, False, False, 0)
        foot = Gtk.Label(label='Ta vidéothèque locale\n\nChoisis un film,\nune série ou un animé.\n\nLes vidéos restent\nà leur emplacement.')
        foot.get_style_context().add_class('subtle')
        foot.set_justify(Gtk.Justification.LEFT)
        side.pack_end(foot, False, False, 10)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main.set_border_width(28)
        layout.pack_start(main, True, True, 0)
        header = Gtk.Box(spacing=12)
        main.pack_start(header, False, False, 0)
        self.title = self.label(header, 'Films', 'heading')
        self.title.set_hexpand(True)
        self.button(header, 'Son / HDMI', self.audio_dialog)
        self.button(header, '+ Dossier vidéo', self.import_folder, True)
        banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        banner.get_style_context().add_class('banner')
        main.pack_start(banner, False, False, 0)
        self.label(banner, 'Une soirée. Tous tes univers.', 'hero')
        self.label(banner, 'Films, séries et animés réunis dans ta bibliothèque personnelle.', 'subtle')
        self.label(banner, 'Choisis une section, retrouve tes vidéos et lance ta séance avec sous-titres.', 'subtle')
        row = Gtk.Box(spacing=12)
        main.pack_start(row, False, False, 0)
        self.search = Gtk.SearchEntry(placeholder_text='Rechercher un titre…')
        self.search.set_hexpand(True)
        self.search.connect('search-changed', lambda *_: self.render())
        row.pack_start(self.search, True, True, 0)
        self.sort = Gtk.ComboBoxText()
        for text in ['Ajouts récents', 'Titre A → Z']:
            self.sort.append_text(text)
        self.sort.set_active(0)
        self.sort.connect('changed', lambda *_: self.render())
        row.pack_start(self.sort, False, False, 0)
        self.audio_summary = self.label(main, '', 'subtle')
        self.refresh_audio_summary()
        self.count = self.label(main, '', 'subtle')
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main.pack_start(scroll, True, True, 0)
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_min_children_per_line(1)
        self.flow.set_max_children_per_line(5)
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_homogeneous(True)
        scroll.add(self.flow)
        self.status = self.label(main, 'Prêt • Choisis un titre pour commencer ta séance', 'subtle')
        self.navs[0].set_active(True)
        self.render()
        self.win.show_all()
        self.audio_timer = GLib.timeout_add_seconds(5, self.refresh_audio_summary)
        self.win.connect('destroy', lambda *_: GLib.source_remove(self.audio_timer))
        if self.load_error:
            self.message('Bibliothèque illisible', self.load_error + '\nLe fichier existant est conservé. Ferme l’application avant de le réparer.')

    def refresh_audio_summary(self):
        settings = audio_settings.load_settings()
        label = audio_settings.output_label(settings)
        profile = 'Dialogues clairs' if settings['profile']=='dialogue' else 'Son original'
        self.audio_summary.set_text(f"Son : {label} · {settings['volume']} % · {profile}")
        return True

    def audio_dialog(self, *_):
        settings = audio_settings.load_settings()
        dialog = Gtk.Dialog(title='Son / HDMI', transient_for=self.win, modal=True)
        dialog.add_buttons('Annuler', Gtk.ResponseType.CANCEL, 'Appliquer', Gtk.ResponseType.OK)
        dialog.set_default_size(570, 440)
        box = dialog.get_content_area(); box.set_border_width(24); box.set_spacing(16)
        self.label(box, 'Le son de ta séance', 'hero')
        self.label(box, 'Sortie audio')
        output = Gtk.ComboBoxText()
        output.append('auto-hdmi', 'Automatique : TV HDMI si branchée, sinon sortie système')
        output.append('system', 'Suivre la sortie choisie dans les paramètres du PC')
        devices = audio_settings.outputs()
        for device in devices:
            output.append(device['name'], device['description'] + (' (muet)' if device['muted'] else ''))
        output.set_active_id(settings['output'])
        if output.get_active()<0: output.set_active_id('auto-hdmi')
        box.add(output)
        self.label(box, 'Volume du lecteur (0–100 %)')
        volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        volume.set_value(settings['volume']); volume.set_digits(0); box.add(volume)
        balanced = Gtk.CheckButton(label='Dialogues clairs : réduire les écarts entre voix et effets')
        balanced.set_active(settings['profile']=='dialogue'); box.add(balanced)
        self.label(box, 'Décalage audio HDMI (ms) · positif : retarder le son')
        delay = Gtk.SpinButton.new_with_range(-500, 500, 10)
        delay.set_value(settings['delay_ms']); box.add(delay)
        note = self.label(box, 'Son PCM adapté à la sortie sélectionnée. Le volume de la TV reste indépendant.\nSortie et volume : appliqués à la lecture en cours.\nDialogues et décalage : appliqués à la prochaine lecture.', 'subtle')
        note.set_line_wrap(True)
        dialog.show_all()
        if dialog.run()==Gtk.ResponseType.OK:
            selected = {'output':output.get_active_id(), 'volume':int(volume.get_value()),
                        'profile':'dialogue' if balanced.get_active() else 'original',
                        'delay_ms':delay.get_value_as_int()}
            try:
                audio_settings.save_settings(selected)
                self.refresh_audio_summary()
                self.status.set_text('Son enregistré · Sortie et volume actualisés dans le lecteur')
            except OSError as error:
                self.message('Enregistrement impossible', str(error))
        dialog.destroy()

    def label(self, parent, text, style=None):
        w = Gtk.Label(label=text, xalign=0)
        if style: w.get_style_context().add_class(style)
        parent.pack_start(w, False, False, 0)
        return w

    def button(self, parent, text, callback, accent=False):
        b = Gtk.Button(label=text)
        if accent: b.get_style_context().add_class('accent')
        b.connect('clicked', callback)
        parent.pack_start(b, False, False, 0)
        return b

    def navigate(self, button, section):
        if not button.get_active():
            return
        self.section = section
        if hasattr(self, 'flow'):
            self.title.set_text(section)
            self.render()

    def render(self):
        for child in self.flow.get_children(): self.flow.remove(child)
        query = self.search.get_text().casefold()
        mapping = {'Films':'Film', 'Séries':'Série', 'Animé':'Animé'}
        entries = [i for i in reversed(self.items) if query in i['title'].casefold() and
                   i['category'] == mapping[self.section]]
        if self.sort.get_active() == 1: entries.sort(key=lambda i: i['title'].casefold())
        self.count.set_text(f'{len(entries)} titre(s) affiché(s) · {len(self.items)} dans la bibliothèque')
        if not entries:
            empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            empty.set_border_width(30)
            self.label(empty, 'Ta prochaine séance commence ici.', 'hero')
            self.label(empty, 'Ajoute un dossier vidéo dans cette section.' if not self.items else 'Aucun titre ne correspond à ce filtre.', 'subtle').set_line_wrap(True)
            self.flow.add(empty)
        for item in entries:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            card.set_size_request(215, -1)
            card.get_style_context().add_class('card')
            poster = self.label(card, '▶', 'poster')
            poster.set_xalign(0.5)
            title = self.label(card, item['title'])
            title.set_max_width_chars(22)
            title.set_ellipsize(Pango.EllipsizeMode.END)
            title.set_tooltip_text(item['title'] + '\n' + item['target'])
            self.label(card, item['category'] + ' · ' + Path(item['target']).suffix.upper().lstrip('.'), 'subtle')
            subtitle = item.get('subtitle') or (find_subtitle(item['target']) if Path(item['target']).is_file() else '')
            sublabel = self.label(card, 'Sous-titres disponibles' if subtitle else 'Sous-titres : à ajouter', 'subtle')
            sublabel.set_tooltip_text(subtitle or 'Ajoute un fichier SRT, ASS, SSA ou VTT, ou utilise une piste intégrée dans VLC.')
            self.button(card, '▶ Lire la vidéo', lambda _, i=item: self.play(i), True)
            self.button(card, 'Sous-titres…', lambda _, i=item: self.choose_subtitle(i))
            actions = Gtk.Box(spacing=6)
            card.pack_start(actions, False, False, 0)
            self.button(actions, '♥' if item.get('favorite') else '♡', lambda _, i=item: self.favorite(i))
            self.button(actions, 'Modifier', lambda _, i=item: self.edit(i))
            self.flow.add(card)
        self.flow.show_all()

    def message(self, title, detail):
        d = Gtk.MessageDialog(transient_for=self.win, modal=True, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, text=title)
        d.format_secondary_text(detail)
        d.run(); d.destroy()

    def choose_subtitle(self, item):
        dialog = Gtk.FileChooserDialog(title='Ajouter les sous-titres de ' + item['title'], transient_for=self.win, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons('Annuler', Gtk.ResponseType.CANCEL, 'Associer', Gtk.ResponseType.OK)
        dialog.set_current_folder(str(Path(item['target']).parent))
        filt = Gtk.FileFilter(); filt.set_name('Sous-titres (SRT, ASS, SSA, VTT)')
        for ext in ['srt', 'ass', 'ssa', 'vtt']:
            filt.add_pattern('*.' + ext); filt.add_pattern('*.' + ext.upper())
        dialog.add_filter(filt)
        response = dialog.run()
        path = dialog.get_filename(); dialog.destroy()
        if response == Gtk.ResponseType.OK and path:
            item['subtitle'] = path
            self.save(); self.render()
            self.status.set_text('Sous-titres associés à ' + item['title'] + ' • Relance la vidéo pour les afficher')

    def play(self, item):
        if not Path(item['target']).is_file():
            self.message('Fichier introuvable', 'Le fichier a été déplacé ou le disque est débranché.\n' + item['target'])
            return
        subtitle = item.get('subtitle') or find_subtitle(item['target'])
        if subtitle and not Path(subtitle).is_file():
            self.message('Sous-titres introuvables', 'Associe de nouveau le fichier de sous-titres avant de lancer la vidéo.')
            return
        try:
            command = ['/usr/bin/python3', str(Path(__file__).with_name('player.py')), item['target']]
            if subtitle: command.append(subtitle)
            subprocess.Popen(command)
            self.status.set_text('Lecture : ' + item['title'] + ' • Sous-titres : menu Sous-titres dans le lecteur')
        except OSError as e:
            self.message('Lecture impossible', str(e))

    def favorite(self, item):
        item['favorite'] = not item.get('favorite', False)
        self.save(); self.render()

    def form(self, heading, item=None):
        dialog = Gtk.Dialog(title=heading, transient_for=self.win, modal=True)
        dialog.add_buttons('Annuler', Gtk.ResponseType.CANCEL, 'Enregistrer', Gtk.ResponseType.OK)
        dialog.set_default_size(500, 250)
        box = dialog.get_content_area(); box.set_border_width(20); box.set_spacing(12)
        self.label(box, 'Titre')
        name = Gtk.Entry(text=item['title'] if item else '')
        box.add(name)
        self.label(box, 'Catégorie')
        category = Gtk.ComboBoxText()
        for c in CATEGORIES: category.append_text(c)
        category.set_active(CATEGORIES.index(item['category']) if item and item['category'] in CATEGORIES else 0)
        box.add(category)
        if item:
            remove = Gtk.CheckButton(label='Retirer ce titre de la bibliothèque (conserve le fichier)')
            box.add(remove)
        dialog.show_all()
        result = None
        while dialog.run() == Gtk.ResponseType.OK:
            if item and remove.get_active(): result = 'remove'; break
            title = name.get_text().strip()
            target = item['target'] if item else ''
            if not title:
                self.message('Informations à compléter', 'Entre un titre pour cette vidéo.')
                continue
            result = {'title':title, 'target':target, 'category':category.get_active_text(), 'source':'Fichier', 'subtitle':item.get('subtitle', '') if item else '', 'favorite': item.get('favorite',False) if item else False}
            break
        dialog.destroy()
        return result

    def edit(self, item):
        updated = self.form('Modifier le titre', item)
        if updated == 'remove': self.items.remove(item)
        elif updated: item.update(updated)
        else: return
        self.save(); self.render()

    def import_folder(self, *_):
        d = Gtk.FileChooserDialog(title='Choisir le dossier vidéo à importer', transient_for=self.win, action=Gtk.FileChooserAction.SELECT_FOLDER)
        d.add_buttons('Annuler', Gtk.ResponseType.CANCEL, 'Importer', Gtk.ResponseType.OK)
        extra = Gtk.Box(spacing=12)
        self.label(extra, 'Catégorie des vidéos :')
        category = Gtk.ComboBoxText()
        for c in CATEGORIES: category.append_text(c)
        category.set_active({'Films':0, 'Séries':1, 'Animé':2}[self.section]); extra.add(category); extra.show_all(); d.set_extra_widget(extra)
        response = d.run()
        root = d.get_filename(); cat = category.get_active_text(); d.destroy()
        if response != Gtk.ResponseType.OK or not root: return
        self.status.set_text('Recherche de vidéos dans ' + root + '…')
        def worker():
            items, errors = scan(root, cat)
            GLib.idle_add(self.import_done, items, errors)
        threading.Thread(target=worker, daemon=True).start()

    def import_done(self, items, errors):
        known = {i['target'] for i in self.items}
        added = 0
        for item in items:
            if item['target'] not in known:
                self.items.append(item); known.add(item['target']); added += 1
        self.save(); self.render()
        self.status.set_text(f'Import terminé : {added} vidéo(s) ajoutée(s) · {len(errors)} dossier(s) inaccessible(s)')
        return False

if __name__ == '__main__':
    raise SystemExit(Cinema().run())
