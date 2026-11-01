"""Generate narration with the owner's ElevenLabs voice clone, one paragraph per file, then join them.
Needs ELEVENLABS_API_KEY (environment secret) and api.elevenlabs.io allowed in the network settings.
  python tts.py voices                      list voices (find the clone's voice_id)
  python tts.py credits                     show credits left this month
  python tts.py make ep01 <voice_id> [part] [--only long-03,long-07]   generate (skips files that exist)
Delete a paragraph's mp3 and re-run to redo just that line."""
import json, os, subprocess, sys, urllib.request

API = 'https://api.elevenlabs.io/v1'
KEY = os.environ.get('ELEVENLABS_API_KEY', 'proxy-injected')
MODEL = 'eleven_multilingual_v2'
SETTINGS = {'stability': 0.5, 'similarity_boost': 0.85, 'style': 0.0, 'use_speaker_boost': True}

def call(path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None,
                                 headers={'xi-api-key': KEY, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def main():
    cmd = sys.argv[1]
    if cmd == 'voices':
        for v in json.loads(call('/voices'))['voices']:
            print(v['voice_id'], '|', v['name'], '|', v.get('category'))
    elif cmd == 'credits':
        s = json.loads(call('/user/subscription'))
        print(s.get('tier'), 'used', s.get('character_count'), 'of', s.get('character_limit'))
    elif cmd == 'make':
        ep, voice = sys.argv[2], sys.argv[3]
        want = sys.argv[4] if len(sys.argv) > 4 and not sys.argv[4].startswith('--') else None
        only = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
        data = json.load(open(f'{ep}/narration.json'))
        for part, paras in data.items():
            if want and part != want: continue
            files = []
            for i, p in enumerate(paras, 1):
                tag = f'{part}-{i:02d}'; f = f'{ep}/audio/{tag}.mp3'; files.append(f)
                if os.path.exists(f) or (only and tag not in only): continue
                os.makedirs(f'{ep}/audio', exist_ok=True)
                audio = call(f'/text-to-speech/{voice}?output_format=mp3_44100_128',
                             {'text': p, 'model_id': MODEL, 'voice_settings': SETTINGS})
                open(f, 'wb').write(audio); print('made', tag, len(p), 'chars')
            have = [f for f in files if os.path.exists(f)]
            if len(have) == len(files):   # join with a short pause between paragraphs
                lst = f'{ep}/audio/{part}.txt'
                gap = f'{ep}/audio/_gap.mp3'
                if not os.path.exists(gap):
                    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono',
                                    '-t', '0.45', '-q:a', '2', gap], check=True)
                open(lst, 'w').write(''.join(f"file '{os.path.abspath(x)}'\nfile '{os.path.abspath(gap)}'\n" for x in have))
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                                '-c:a', 'libmp3lame', '-q:a', '2', f'{ep}/{part}.mp3'], check=True)
                print('joined', f'{ep}/{part}.mp3')

if __name__ == '__main__':
    main()
