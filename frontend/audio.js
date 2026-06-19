/* ── Audio ─────────────────────────────────────────────────── */
/* ── Audio encoding ─────────────────────────────────────────── */

// Declared globals (shared with voice.js)
var calling = false;
var mediaRec = null;
var mediaStream = null;
var _processingAudio = false;
var _currentAudio = null;
var _ttsStartTime = null;
var _audioQueue = [];

function _btoa(buf) {
  let bin = '';
  for (let i = 0; i < buf.byteLength; i += 8192)
    bin += String.fromCharCode.apply(null, new Uint8Array(buf.slice(i, i + 8192)));
  return btoa(bin);
}

function encodeWAV(s, sr) {
  let b = new ArrayBuffer(44 + s.length * 2),
      v = new DataView(b);
  let w = (x, o) => v.setUint16(o, x, true),
      w32 = (x, o) => v.setUint32(o, x, true);
  for (let i = 0; i < 4; i++) {
    v.setUint8(i, 'RIFF'.charCodeAt(i));
    v.setUint8(i + 8, 'WAVE'.charCodeAt(i));
    v.setUint8(i + 12, 'fmt '.charCodeAt(i));
    v.setUint8(i + 36, 'data'.charCodeAt(i));
  }
  w32(36 + s.length * 2, 4);
  w32(16, 16);
  w(1, 20); w(1, 22);
  w32(s, 24); w32(s * 2, 28);
  w(2, 32); w(16, 34);
  w32(s.length * 2, 40);
  let o = 44;
  for (let i = 0; i < s.length; i++) {
    let x = Math.max(-1, Math.min(1, s[i]));
    v.setInt16(o, x < 0 ? x * 32768 : x * 32767, true);
    o += 2;
  }
  return b;
}

/* ── Continuous voice call ──────────────────────────────────── */

async function toggleCall() {
  if (calling) { stopCall(); return; }
  calling = true;
  document.getElementById('call-btn').textContent = 'END';
  document.getElementById('call-btn').className = 'btn r';
  setStatus('listening');
  setDot('on');
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1 }
    });
    let ctx = new AudioContext({ sampleRate: 16000 }),
        src = ctx.createMediaStreamSource(mediaStream),
        proc = ctx.createScriptProcessor(4096, 1, 1),
        buffer = [],
        frameCount = 0;
    proc.onaudioprocess = e => {
      if (!calling) return;
      buffer.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      frameCount++;
      let rms = 0, ch = e.inputBuffer.getChannelData(0);
      for (let i = 0; i < ch.length; i++) rms += ch[i] * ch[i];
      rms = Math.sqrt(rms / ch.length);
      document.getElementById('vol-bar').style.width = Math.min(100, rms * 800) + '%';
      if (!_processingAudio && _currentAudio && _ttsStartTime &&
          Date.now() - _ttsStartTime > 600 && rms > 0.03) {
        _currentAudio.pause(); _currentAudio = null;
        addMsg('sys', '(interrupted)');
      }
      if (frameCount >= 6 && !_processingAudio) {
        let all = new Float32Array(buffer.reduce((s, a) => s + a.length, 0));
        let off = 0;
        for (let b of buffer) { all.set(b, off); off += b.length; }
        buffer = []; frameCount = 0;
        _processingAudio = true;
        sendAudioChunk(all);
      }
    };
    src.connect(proc); proc.connect(ctx.destination);
    mediaRec = { proc, src, ctx };
    addMsg('sys', 'Voice active — speak now');
    setTimeout(() => { if (calling) addMsg('sys', 'No audio? Check mic permissions.'); }, 8000);
    setTimeout(() => { if (calling) stopCall(); }, 300000);
  } catch (e) {
    addMsg('sys', 'Mic error: ' + e.message);
    stopCall();
  }
}

async function sendAudioChunk(samples) {
  setStatus('transcribing');
  setDot('blue');
  try {
    let wav = encodeWAV(samples, 16000),
        b64 = _btoa(wav),
        r = await api('/voice/transcribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ audio: b64 })
        }),
        d = await r.json();
    if (d.error) { setStatus('listening'); setDot('on'); }
    if (d.text) addMsg('user', d.text);
    if (d.reply) {
      addMsg('ai', d.reply);
      setStatus('speaking');
      setDot('warn');
      let chunks = d.audio_chunks || (d.audio ? [d.audio] : []);
      if (chunks.length) enqueueAudio(chunks, true);
      else { let u = new SpeechSynthesisUtterance(d.reply); u.lang = 'zh-CN'; speechSynthesis.speak(u); }
    }
    setStatus('listening');
    setDot('on');
  } catch (e) { setStatus('listening'); setDot('on'); }
  _processingAudio = false;
}

function stopCall() {
  calling = false;
  document.getElementById('call-btn').textContent = 'CALL';
  document.getElementById('call-btn').className = 'btn a';
  setStatus('idle');
  setDot('');
  if (mediaRec) {
    try { mediaRec.proc.disconnect(); mediaRec.ctx.close(); } catch (e) {}
  }
  mediaRec = null;
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); }
  mediaStream = null;
  _processingAudio = false;
}

/* ── Audio playback ─────────────────────────────────────────── */

function enqueueAudio(chunks, allowInterrupt) {
  if (!chunks.length) return;
  _audioQueue = [];
  if (_currentAudio) { _currentAudio.pause(); _currentAudio = null; }
  _audioQueue = chunks.map(c => 'data:audio/mp3;base64,' + c);
  _playNextInQueue(allowInterrupt);
}

function _playNextInQueue(allowInterrupt) {
  if (!_audioQueue.length) return;
  let src = _audioQueue.shift(),
      a = new Audio(src);
  if (allowInterrupt) { _currentAudio = a; _ttsStartTime = Date.now(); }
  a.onended = () => _playNextInQueue(allowInterrupt);
  a.onerror = () => _playNextInQueue(allowInterrupt);
  a.play();
}

