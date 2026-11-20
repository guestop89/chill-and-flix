# chill&flix — ALPHA TEST

**Version 0.1.0-alpha.1 · Linux uniquement**

Une vidéothèque locale pour retrouver ses films, séries et animés, puis les regarder avec ses sous-titres dans VLC.

> Version de test : l’interface et les réglages peuvent évoluer. Aucun film, sous-titre ou catalogue personnel n’est fourni.

## Fonctionnalités

- Trois sections : **Films**, **Séries**, **Animé**.
- Import de dossiers et sous-dossiers, nettoyage des noms et détection des doublons.
- Recherche, tri, favoris et modification des titres et catégories.
- Lecture locale avec VLC ; association de sous-titres SRT, ASS, SSA et VTT.
- Choix de sortie audio, HDMI automatique si une TV est branchée, sinon sortie système.
- Son original par défaut, volume initial de 85 %, limite d’amplification à 100 %.
- Compression des écarts voix/effets facultative, désactivée par défaut.
- Raccourcis dans le menu des applications et sur le bureau.

Les fichiers vidéo restent à leur emplacement. Retirer un titre de la bibliothèque ne supprime pas sa vidéo.

## Installation

Télécharger l’archive de la release **ALPHA TEST**, l’extraire puis ouvrir un terminal dans le dossier extrait.

Prérequis : Python 3.10+, PyGObject, GTK 3, Flatpak, VLC via Flathub et `pactl` (PulseAudio ou compatibilité PipeWire).

### Arch Linux / CachyOS

```sh
sudo pacman -S --needed python python-gobject gtk3 flatpak libpulse xdg-user-dirs
```

### Debian / Ubuntu

```sh
sudo apt install python3 python3-gi gir1.2-gtk-3.0 flatpak pulseaudio-utils xdg-user-dirs
```

### VLC et installation de chill&flix

```sh
flatpak --user remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak --user install flathub org.videolan.VLC
python3 install.py
```

L’installateur vérifie les dépendances puis installe l’application pour le compte courant, sans privilèges administrateur. Il n’installe pas les dépendances automatiquement.

Pour vérifier les dépendances sans installer :

```sh
python3 install.py --check
```

Pour lancer depuis le dossier source :

```sh
python3 cinema.py
```

## Utilisation

1. Choisir Films, Séries ou Animé.
2. Cliquer sur **+ Dossier vidéo** et sélectionner le dossier et sa catégorie.
3. Cliquer sur **Lire la vidéo** pour ouvrir VLC.
4. Utiliser **Sous-titres…** sur une carte pour associer un fichier externe, puis relancer la vidéo.

Les sous-titres voisins du fichier vidéo sont détectés automatiquement lorsqu’ils portent le même nom, avec éventuellement un suffixe de langue, par exemple `Mon film.fr.srt`. Une piste française est préférée lorsqu’elle existe. Les pistes intégrées restent accessibles depuis le menu Sous-titres de VLC.

Dans VLC : Espace = pause ; F = plein écran ; Échap = quitter le plein écran ; V = changer de piste de sous-titres.

### Son / HDMI

La sortie et le volume peuvent être modifiés pendant une lecture lancée depuis l’application. Le profil sonore et le décalage prennent effet à la prochaine lecture. Le volume matériel de la TV ou du casque reste indépendant.

Le mode automatique choisit une sortie HDMI détectée comme branchée. Sans HDMI disponible, il suit la sortie système. Le son original est recommandé pour commencer ; le profil Dialogues clairs est facultatif. La limite à 100 % évite la suramplification logicielle mais ne garantit pas l’absence de défaut dans le fichier source ou le matériel.

## Données locales

- Application installée : `${XDG_DATA_HOME:-~/.local/share}/chill-flix/app`.
- Bibliothèque et préférences : `${XDG_DATA_HOME:-~/.local/share}/chill-flix`.
- La bibliothèque commence vide et n’est pas synchronisée avec un service externe.

## Limites de l’alpha

- Testée sur CachyOS avec PipeWire/PulseAudio et VLC Flatpak.
- Aucun support Windows ou macOS dans cette version.
- Import manuel des nouveaux fichiers, pas de surveillance automatique des dossiers.
- Pas de regroupement automatique des saisons ni de téléchargement de sous-titres.
- La synchronisation des sous-titres dépend du fichier choisi et de la version vidéo.
- Un disque débranché ou un fichier déplacé peut nécessiter un nouvel import.
- Les réglages audio peuvent nécessiter des ajustements selon la TV ou le casque.

## Signaler un problème

Ouvrir une issue avec la distribution Linux, la version de VLC, les étapes pour reproduire le problème et le résultat attendu. Éviter d’inclure sa bibliothèque ou des chemins personnels dans les captures et les journaux.

## Vérifications de développement

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile cinema.py player.py audio_settings.py install.py
```
