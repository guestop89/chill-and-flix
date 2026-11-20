#!/usr/bin/env python3
"""Lecteur local VLC, sous-titres et sortie HDMI propre à chill&flix."""
import subprocess
import sys
import time
import uuid
from pathlib import Path
from audio_settings import load_settings, select_output, pulse_list, apply_stream, limit_stream_volume

def player_command(video, subtitle=None, settings=None, instance=None):
    video=Path(video).resolve()
    if not video.is_file():raise FileNotFoundError('Vidéo introuvable : '+str(video))
    settings=load_settings() if settings is None else settings
    sink=select_output(settings)
    if not sink:
        try: sink=subprocess.check_output(['pactl','get-default-sink'],text=True,timeout=2).strip()
        except (OSError,subprocess.SubprocessError): pass
    command=['flatpak','run']
    if sink:command.append('--env=PULSE_SINK='+sink)
    if instance:command.append('--env=PULSE_PROP=application.name=ChillFlix application.id=fr.local.ChillFlix.Player chill-flix.instance='+instance)
    command += ['org.videolan.VLC','--no-one-instance','--play-and-exit',
                '--no-video-title-show','--no-metadata-network-access','--no-qt-privacy-ask',
                '--sub-autodetect-file','--sub-language=fr,fra,fre,français',
                '--aout=pulse','--no-spdif','--stereo-mode=0','--gain=0.614125','--no-volume-save','--qt-max-volume=100',
                '--audio-replay-gain-mode=none',
                '--audio-desync='+str(settings['delay_ms'])]
    if settings['profile']=='dialogue':
        command += ['--audio-filter=compressor','--compressor-threshold=-18',
                    '--compressor-ratio=2.5','--compressor-attack=25','--compressor-release=250',
                    '--compressor-knee=4','--compressor-makeup-gain=2']
    else:command.append('--audio-filter=')
    if subtitle:
        sub=Path(subtitle).resolve()
        if not sub.is_file():raise FileNotFoundError('Sous-titres introuvables : '+str(sub))
        command.extend(['--sub-file',str(sub)])
    command.append(str(video))
    return command

def follow_audio(process, instance):
    applied={}
    while process.poll() is None:
        settings=load_settings();sink=select_output(settings)
        if not sink:
            # Retour à la sortie système si le câble a été débranché.
            try:sink=subprocess.check_output(['pactl','get-default-sink'],text=True,timeout=2).strip()
            except (OSError,subprocess.SubprocessError):pass
        desired=(sink,settings['volume'])
        active=set()
        for stream in pulse_list('sink-inputs'):
            if stream.get('properties',{}).get('chill-flix.instance')!=instance:continue
            index=stream['index'];active.add(index)
            limit_stream_volume(stream)
            if applied.get(index)!=desired and apply_stream(index,*desired):applied[index]=desired
        applied={index:value for index,value in applied.items() if index in active}
        time.sleep(1)
    return process.returncode

if __name__=='__main__':
    if len(sys.argv) not in (2,3):raise SystemExit('Utilisation : player.py vidéo [sous-titres]')
    try:
        instance=uuid.uuid4().hex
        process=subprocess.Popen(player_command(*sys.argv[1:],instance=instance))
        raise SystemExit(follow_audio(process,instance))
    except (OSError,ValueError) as error:
        print(error,file=sys.stderr);raise SystemExit(1)
