import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import audio_settings as audio
import cinema
import player
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)

class AlphaTests(unittest.TestCase):
    def test_recursive_import_and_french_subtitles(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'nested'; directory.mkdir()
            video = directory / 'Example.2024.1080p.BluRay.x264.mp4'; video.touch()
            subtitle = video.with_suffix('.fr.srt'); subtitle.write_text('')
            video.with_suffix('.en.srt').write_text('')
            (directory / 'notes.txt').write_text('')
            found, errors = cinema.scan(tmp, 'Film')
            self.assertEqual(errors, [])
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]['title'], 'Example (2024)')
            self.assertEqual(found[0]['subtitle'], str(subtitle))

    def test_disconnected_hdmi_and_missing_device(self):
        devices = [{'name':'off','hdmi':True,'connected':False},
                   {'name':'tv','hdmi':True,'connected':True}]
        settings = dict(audio.DEFAULTS)
        self.assertEqual(audio.select_output(settings, devices), 'tv')
        self.assertEqual(audio.select_output(settings, devices[:1]), '')
        self.assertEqual(audio.select_output(dict(settings,output='absent'), devices), '')
        self.assertEqual(audio.select_output(dict(settings,output='system'), devices), '')

    def test_settings_are_bounded_and_original_by_default(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(audio, 'DATA', Path(tmp)):
            self.assertEqual(audio.load_settings()['profile'], 'original')
            audio.save_settings(dict(audio.DEFAULTS,volume=200,delay_ms=-900,profile='invalid'))
            settings = audio.load_settings()
            self.assertEqual(settings['volume'],100)
            self.assertEqual(settings['delay_ms'],-500)
            self.assertEqual(settings['profile'],'original')
            (Path(tmp) / 'audio.json').write_text('broken')
            self.assertEqual(audio.load_settings(),audio.DEFAULTS)

    def test_launch_uses_original_audio_and_correct_subtitle(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / 'film with spaces.mp4'; video.touch()
            subtitle = video.with_suffix('.fr.srt'); subtitle.touch()
            with patch.object(player,'select_output',return_value='test_sink'):
                command=player.player_command(video,subtitle,dict(audio.DEFAULTS),instance='test')
            self.assertIn('--env=PULSE_SINK=test_sink',command)
            self.assertIn('--audio-filter=',command)
            self.assertIn('--qt-max-volume=100',command)
            self.assertNotIn('--audio-filter=compressor',command)
            self.assertEqual(command[command.index('--sub-file')+1],str(subtitle))
            self.assertEqual(command[-1],str(video))
            with self.assertRaises(FileNotFoundError):player.player_command(Path(tmp)/'missing.mp4')

    def test_volume_limit_does_not_touch_normal_levels(self):
        with patch.object(audio.subprocess,'run') as run:
            self.assertFalse(audio.limit_stream_volume({'index':1,'volume':{'left':{'value':65536}}}))
            run.assert_not_called()
            self.assertTrue(audio.limit_stream_volume({'index':1,'volume':{'left':{'value':128000}}}))
            self.assertEqual(run.call_args.args[0],['pactl','set-sink-input-volume','1','100%'])

    def test_installer_copies_only_application_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data'; prefix = data / 'chill-flix/app'; desktop=Path(tmp)/'desktop'
            installer.install(prefix,data,desktop)
            self.assertEqual(set(p.name for p in prefix.iterdir()),set(installer.APP_FILES))
            shortcut=desktop/(installer.APP_ID+'.desktop')
            self.assertTrue(shortcut.stat().st_mode & 0o111)
            self.assertIn('Name=chill&flix',shortcut.read_text())
            self.assertNotIn('library.json',[p.name for p in prefix.iterdir()])
            if __import__('shutil').which('desktop-file-validate'):
                result=subprocess.run(['desktop-file-validate',str(shortcut)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            installer.install(prefix,data,desktop)
            self.assertTrue((prefix/'cinema.py').is_file())

if __name__=='__main__':unittest.main()
