from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
backup=ROOT/'archive/pitch_base_1024'
backup.mkdir(exist_ok=True)
source=ROOT/'web-editor/source.html'
if not (backup/'source.html').exists():shutil.copy2(source,backup/'source.html')
s=(backup/'source.html').read_text(encoding='utf-8')
def replace(a,b):
    global s
    assert a in s,a[:100]
    s=s.replace(a,b)
def function(name,new):
    global s
    lines=s.splitlines(True)
    idx=next(i for i,l in enumerate(lines) if l.strip().startswith(('function '+name+'(', 'async function '+name+'(')))
    lines[idx]='            '+new+'\n';s=''.join(lines)
replace('        (() => {','        '+(ROOT/'web-editor/pitch-audio.js').read_text(encoding='utf-8')+'\n        (() => {')
replace('musicSource = null, startAudio','musicSource = null, preparedMusic = null, startAudio')
function('togglePlay',"async function togglePlay() { cancelHold(); if (playing || starting) { pause(); return; } if (meta.music && !audioReady) { toast('请先重新选择这首音乐，再进行试听。'); $('musicFile').click(); return; } if (cursor >= meta.duration - 1) seek(0); const token = ++playToken; starting = true; $('playButton').textContent = '…'; try { const a = context(); if (!a) throw Error('此浏览器不支持音频试听'); await a.resume(); if (token !== playToken) return; if (a.state !== 'running') throw Error('音频未能启动'); const rate=Number($('speed').value); const prepared=musicBuffer ? await PitchAudio.prepare(a,musicBuffer,rate,p=>{if(token===playToken)$('musicInfo').textContent='正在准备保调试听 '+p+'%（可点击播放键取消）';}) : null; if(token!==playToken)return; preparedMusic=prepared; startTime = cursor; startAudio = a.currentTime + .06; playRate = rate; startMusic(); starting = false; playing = true; $('musicInfo').textContent=musicBuffer?'保调试听 · '+rate+'×':''; $('playButton').textContent = 'Ⅱ'; $('playButton').setAttribute('aria-label', '暂停预览'); resetSchedule(cursor); selectionUI(); document.querySelectorAll('.sidebar input,.sidebar select').forEach(x => x.disabled = true); } catch(e) { if (token !== playToken) return; pause(); toast(e.message || '音频无法启动，请重新选择音乐。'); } }")
function('startMusic',"function startMusic() { stopMusic(); if (musicBuffer && startTime < musicBuffer.duration * 1000) { if(!preparedMusic&&playRate!==1)throw Error('保调音频尚未准备完成'); musicSource = audioContext.createBufferSource(); musicSource.buffer = preparedMusic || musicBuffer; musicSource.playbackRate.value = 1; musicSource.connect(audioContext.destination); musicSource.start(startAudio, startTime / 1000 / playRate); } }")
function('changeSpeed',"async function changeSpeed() { if (playing || starting) { pause(); await togglePlay(); } }")
replace('function pause() { playToken++;','function pause() { PitchAudio.cancel(); playToken++;')
replace('stopMusic(); audio.pause();','stopMusic(); preparedMusic=null; audio.pause();')
replace("speed = Number($('speed').value), end",'speed = playRate, end')
replace('musicBuffer = null;','musicBuffer = null; PitchAudio.clear(); preparedMusic=null;')
source.write_text(s,encoding='utf-8')
(ROOT/'web-editor/hold-app.js').write_text(s[s.index('        (() => {'):s.rindex('</script>')],encoding='utf-8')
print('Pitch-preserving editor ready')
