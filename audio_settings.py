"""Réglages audio et sélection des sorties PipeWire/PulseAudio."""
import json
import os
import subprocess
from pathlib import Path

DATA = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'chill-flix'
DEFAULTS = {'output':'auto-hdmi', 'volume':85, 'profile':'original', 'delay_ms':0}

def load_settings():
    settings = DEFAULTS.copy()
    try:
        saved = json.loads((DATA / 'audio.json').read_text())
        if isinstance(saved, dict): settings.update(saved)
    except (OSError, ValueError): pass
    if not isinstance(settings['output'], str): settings['output'] = DEFAULTS['output']
    if settings['profile'] not in {'dialogue','original'}: settings['profile']='original'
    for key, low, high in [('volume',0,100),('delay_ms',-500,500)]:
        try: settings[key]=max(low,min(high,int(settings[key])))
        except (TypeError,ValueError): settings[key]=DEFAULTS[key]
    return settings

def save_settings(settings):
    DATA.mkdir(parents=True,exist_ok=True)
    temporary = DATA / 'audio.tmp'
    temporary.write_text(json.dumps(settings,ensure_ascii=False,indent=2))
    temporary.replace(DATA / 'audio.json')

def pulse_list(kind):
    try:
        result=subprocess.run(['pactl','-f','json','list',kind],capture_output=True,text=True,timeout=2,check=True)
        value=json.loads(result.stdout)
        return value if isinstance(value,list) else []
    except (OSError,subprocess.SubprocessError,ValueError): return []

def outputs():
    devices=[]
    cards={c['index']:c for c in pulse_list('cards')}
    for sink in pulse_list('sinks'):
        ports=sink.get('ports',[])
        active=next((p for p in ports if p.get('name')==sink.get('active_port')),None)
        if active and active.get('availability')=='not available': continue
        hdmi=bool(active and active.get('type') in {'HDMI','DisplayPort'})
        # Une sortie HDMI non branchée ne doit jamais être choisie en automatique.
        available=bool(active and active.get('availability')=='available')
        description=sink.get('description',sink['name'])
        if hdmi:
            for c in cards.values():
                port=c.get('ports',{}).get(sink.get('active_port'),{})
                product=port.get('properties',{}).get('device.product.name')
                if product:
                    description=product+' · HDMI';break
        devices.append({'name':sink['name'],'description':description,'hdmi':hdmi,'connected':available,'muted':sink.get('mute',False),'index':sink['index']})
    return devices

def select_output(settings, devices=None):
    devices=outputs() if devices is None else devices
    choice=settings['output']
    if choice=='auto-hdmi':
        hdmi=next((d for d in devices if d['hdmi'] and d['connected']),None)
        if hdmi:return hdmi['name']
    elif choice!='system':
        selected=next((d for d in devices if d['name']==choice),None)
        if selected:return selected['name']
    return ''

def output_label(settings):
    devices=outputs();selected=select_output(settings,devices)
    device=next((d for d in devices if d['name']==selected),None)
    if device:return device['description'] + (' · sortie muette' if device['muted'] else '')
    return 'Sortie du système' + (' · aucun HDMI branché' if settings['output']=='auto-hdmi' else '')

def apply_stream(index, sink, volume):
    commands=[['pactl','set-sink-input-volume',str(index),str(volume)+'%'],
              ['pactl','set-sink-input-mute',str(index),'0']]
    if sink:commands.append(['pactl','move-sink-input',str(index),sink])
    for command in commands:
        try:subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2,check=True)
        except (OSError,subprocess.SubprocessError):return False
    return True


def limit_stream_volume(stream):
    """Empêche une amplification supérieure à 100 % dans nos lectures."""
    if any(channel.get('value', 0) > 65536 for channel in stream.get('volume', {}).values()):
        try:
            subprocess.run(['pactl', 'set-sink-input-volume', str(stream['index']), '100%'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, check=True)
            return True
        except (OSError, subprocess.SubprocessError):
            pass
    return False
