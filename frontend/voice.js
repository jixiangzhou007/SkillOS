/* SkillOS — Voice Input (Alpine.js)
 * Phase 5 migration. Recording UI is now reactive.
 * Audio processing (encodeWAV, _btoa, etc.) stays in audio.js.
 */

// ── Alpine component ───────────────────────────────────

function voiceControl() {
  return {
    recording: false,
    calling: false,

    get micText() { return this.recording ? '🔴' : '🎤'; },
    get micStyle() {
      return this.recording
        ? 'border-color:var(--err);color:var(--err);animation:pulse 0.8s infinite'
        : '';
    },
    get callText() { return this.calling ? 'END' : 'CALL'; },
    get callClass() { return this.calling ? 'btn r' : 'btn a'; },

    toggleMic() {
      if (this.recording) {
        this._stopRecording();
      } else {
        this._startRecording();
      }
    },

    _startRecording() {
      // Sync global state for audio.js compatibility
      window._recording = true;
      this.recording = true;
      setStatus('聆听中…');

      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        this._browserMic(SpeechRecognition);
      } else {
        this._serverMic();
      }
    },

    _stopRecording() {
      window._recording = false;
      this.recording = false;
      if (window._speechRecognition) {
        window._speechRecognition.stop();
        window._speechRecognition = null;
      }
      if (window._micRecorder) {
        stopServerMic();  // old function handles cleanup
      }
      setStatus('空闲');
    },

    _browserMic(SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.lang = 'zh-CN';
      recognition.interimResults = false;
      recognition.continuous = false;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        const text = event.results[0][0].transcript.trim();
        if (text) {
          document.getElementById('input').value = text;
          document.getElementById('input').focus();
          this._stopRecording();
        }
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        this._stopRecording();
        if (event.error === 'not-allowed') {
          addMsg('sys', '🎤 麦克风权限被拒绝 — 请在浏览器设置中允许访问');
        } else if (event.error !== 'aborted') {
          addMsg('sys', '🎤 语音识别错误：' + event.error);
        }
      };

      recognition.onend = () => this._stopRecording();

      recognition.start();
      window._speechRecognition = recognition;

      setTimeout(() => {
        if (this.recording && window._speechRecognition) {
          window._speechRecognition.stop();
        }
      }, 10000);
    },

    _serverMic() {
      setStatus('录音中…');
      navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        window._micStream = stream;
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus' : 'audio/webm';
        const recorder = new MediaRecorder(stream, { mimeType });
        const chunks = [];
        recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
        recorder.onstop = () => processServerMicChunks(chunks);
        recorder.start(100);
        window._micRecorder = { recorder, chunks };
        setTimeout(() => { if (this.recording) stopServerMic(); }, 15000);
      }).catch(e => {
        this._stopRecording();
        addMsg('sys', '🎤 麦克风错误：' + e.message);
      });
    },

    toggleCall() {
      if (this.calling) {
        stopCall();  // old function handles cleanup
        this.calling = false;
      } else {
        this.calling = true;
        toggleCall();  // old function starts the call
        // toggleCall sets window.calling = true, we sync back
      }
    }
  };
}

// ── Legacy globals (used by audio.js) ─────────────────

let _speechRecognition = null;

// _recording, _micStream, _micRecorder are set by voiceControl()
// and used by stopServerMic() / processServerMicChunks() below

// ── Backward-compatible wrappers ─────────────────────

function toggleMic() {
  const el = document.querySelector('[x-data="voiceControl()"]');
  if (el && el.__x) {
    el.__x.$data.toggleMic();
  }
}

function resetMicButton() {
  // No-op: Alpine bindings handle button appearance reactively.
  // Kept as compatibility stub for old code that calls this.
}

// ── Server-side ASR (unchanged, used by voiceControl) ──

function toggleServerMic() {
  const el = document.querySelector('[x-data="voiceControl()"]');
  if (el && el.__x) {
    el.__x.$data._startRecording();
    return;
  }
  // Legacy fallback
  if (window._recording) { stopServerMic(); return; }
  window._recording = true;
  const btn = document.getElementById('mic-btn');
  if (btn) { btn.textContent = '🔴'; btn.style.borderColor = 'var(--err)'; btn.style.color = 'var(--err)'; btn.style.animation = 'pulse 0.8s infinite'; }
  setStatus('录音中…');
  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    window._micStream = stream;
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
    const recorder = new MediaRecorder(stream, { mimeType });
    const chunks = [];
    recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
    recorder.onstop = () => processServerMicChunks(chunks);
    recorder.start(100);
    window._micRecorder = { recorder, chunks };
    setTimeout(() => { if (window._recording) stopServerMic(); }, 15000);
  }).catch(e => {
    window._recording = false; resetMicButton(); setStatus('空闲');
    addMsg('sys', '🎤 麦克风错误：' + e.message);
  });
}

function stopServerMic() {
  if (!window._recording) return;
  window._recording = false;
  // Also sync Alpine state
  const el = document.querySelector('[x-data="voiceControl()"]');
  if (el && el.__x) el.__x.$data.recording = false;
  resetMicButton();
  setStatus('转写中…');
  if (window._micRecorder && window._micRecorder.recorder && window._micRecorder.recorder.state === 'recording') {
    const chunks = window._micRecorder.chunks || [];
    let resolved = false;
    window._micRecorder.recorder.onstop = () => { if (!resolved) { resolved = true; processServerMicChunks(chunks); } };
    window._micRecorder.recorder.requestData();
    window._micRecorder.recorder.stop();
    setTimeout(() => { if (!resolved) { resolved = true; processServerMicChunks(chunks); } }, 1000);
  } else {
    if (window._micStream) { window._micStream.getTracks().forEach(t => t.stop()); window._micStream = null; }
    window._micRecorder = null;
    setStatus('空闲');
  }
}

async function processServerMicChunks(chunks) {
  if (window._micStream) { window._micStream.getTracks().forEach(t => t.stop()); window._micStream = null; }
  if (!chunks || !chunks.length) {
    setStatus('空闲'); window._micRecorder = null;
    addMsg('sys', '🎤 未捕获到音频');
    return;
  }
  try {
    const blob = new Blob(chunks, { type: 'audio/webm' });
    const arrayBuf = await blob.arrayBuffer();
    const audioCtx = new AudioContext();
    const audioBuffer = await audioCtx.decodeAudioData(arrayBuf);
    const channelData = audioBuffer.getChannelData(0);
    const origSr = audioBuffer.sampleRate;
    let samples;
    if (origSr !== 16000) {
      const ratio = 16000 / origSr;
      const newLen = Math.floor(channelData.length * ratio);
      samples = new Float32Array(newLen);
      for (let i = 0; i < newLen; i++) {
        const frac = i / ratio;
        const lo = Math.floor(frac), hi = Math.min(lo + 1, channelData.length - 1);
        samples[i] = channelData[lo] * (1 - (frac - lo)) + channelData[hi] * (frac - lo);
      }
    } else { samples = channelData; }
    audioCtx.close();
    const wav = encodeWAV(samples, 16000), b64 = _btoa(wav);
    setStatus('转写中…');
    const r = await api('/voice/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio: b64 })
    });
    if (!r.ok) {
      if (r.status === 404) throw new Error('服务端语音识别未配置，请使用 Chrome/Edge 浏览器麦克风');
      throw new Error('服务端错误 ' + r.status);
    }
    const d = await r.json();
    if (d.text) { document.getElementById('input').value = d.text; sendText(); }
    else { setStatus('空闲'); addMsg('sys', '🎤 未检测到语音'); }
  } catch (e) {
    console.error('Mic error:', e);
    addMsg('sys', '🎤 错误: ' + e.message);
    setStatus('空闲');
  }
  window._micRecorder = null;
}
