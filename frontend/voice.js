/* ── Voice ────────────────────────────────────────────────── */
/* ── Voice (push-to-talk mic) ───────────────────────────────── */

let _speechRecognition = null;

function toggleMic() {
  // Use browser's built-in SpeechRecognition for instant results
  let SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    toggleBrowserMic(SpeechRecognition);
  } else {
    // Fallback: server-side ASR via MediaRecorder
    toggleServerMic();
  }
}

/* ── Browser Speech Recognition (instant, no server needed) ──── */

function toggleBrowserMic(SpeechRecognition) {
  if (_recording) {
    _speechRecognition && _speechRecognition.stop();
    return;
  }
  _recording = true;
  let btn = document.getElementById('mic-btn');
  btn.textContent = '🔴';
  btn.style.borderColor = 'var(--err)';
  btn.style.color = 'var(--err)';
  btn.style.animation = 'pulse 0.8s infinite';
  setStatus('聆听中…');

  let recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.interimResults = false;
  recognition.continuous = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    let text = event.results[0][0].transcript.trim();
    if (text) {
      document.getElementById('input').value = text;
      document.getElementById('input').focus();
      resetMicButton();
      setStatus('空闲');
      _recording = false;
    }
  };

  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    resetMicButton();
    setStatus('空闲');
    _recording = false;
    if (event.error === 'not-allowed') {
      addMsg('sys', '🎤 麦克风权限被拒绝 — 请在浏览器设置中允许访问');
    } else if (event.error !== 'aborted') {
      addMsg('sys', '🎤 语音识别错误：' + event.error);
    }
  };

  recognition.onend = () => {
    resetMicButton();
    setStatus('空闲');
    _recording = false;
  };

  recognition.start();
  _speechRecognition = recognition;

  // Auto-stop after 10s of silence
  setTimeout(() => {
    if (_recording && _speechRecognition) {
      _speechRecognition.stop();
    }
  }, 10000);
}

/* ── Server-side ASR fallback ────────────────────────────────── */

function toggleServerMic() {
  if (_recording) { stopServerMic(); return; }
  _recording = true;
  let btn = document.getElementById('mic-btn');
  btn.textContent = '🔴';
  btn.style.borderColor = 'var(--err)';
  btn.style.color = 'var(--err)';
  btn.style.animation = 'pulse 0.8s infinite';
  setStatus('录音中…');
  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    _micStream = stream;
    let mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus' : 'audio/webm';
    let recorder = new MediaRecorder(_micStream, { mimeType: mimeType });
    let chunks = [];
    recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
    recorder.onstop = () => processServerMicChunks(chunks);
    recorder.start(100);
    _micRecorder = { recorder, chunks };
    setTimeout(() => { if (_recording) stopServerMic(); }, 15000);
  }).catch(e => {
    _recording = false; resetMicButton(); setStatus('空闲');
    addMsg('sys', '🎤 麦克风错误：' + e.message);
  });
}

function stopServerMic() {
  if (!_recording) return;
  _recording = false;
  resetMicButton();
  setStatus('转写中…');
  if (_micRecorder && _micRecorder.recorder && _micRecorder.recorder.state === 'recording') {
    let chunks = _micRecorder.chunks || [];
    let resolved = false;
    _micRecorder.recorder.onstop = () => { if (!resolved) { resolved = true; processServerMicChunks(chunks); } };
    _micRecorder.recorder.requestData();
    _micRecorder.recorder.stop();
    setTimeout(() => { if (!resolved) { resolved = true; processServerMicChunks(chunks); } }, 1000);
  } else {
    if (_micStream) { _micStream.getTracks().forEach(t => t.stop()); _micStream = null; }
    _micRecorder = null;
    setStatus('空闲');
  }
}

async function processServerMicChunks(chunks) {
  if (_micStream) { _micStream.getTracks().forEach(t => t.stop()); _micStream = null; }
  if (!chunks || !chunks.length) {
    setStatus('空闲'); _micRecorder = null;
    addMsg('sys', '🎤 未捕获到音频');
    return;
  }
  try {
    let blob = new Blob(chunks, { type: 'audio/webm' });
    let arrayBuf = await blob.arrayBuffer();
    let audioCtx = new AudioContext();
    let audioBuffer = await audioCtx.decodeAudioData(arrayBuf);
    let channelData = audioBuffer.getChannelData(0);
    let origSr = audioBuffer.sampleRate;
    let samples;
    if (origSr !== 16000) {
      let ratio = 16000 / origSr;
      let newLen = Math.floor(channelData.length * ratio);
      samples = new Float32Array(newLen);
      for (let i = 0; i < newLen; i++) {
        let frac = i / ratio;
        let lo = Math.floor(frac), hi = Math.min(lo + 1, channelData.length - 1);
        samples[i] = channelData[lo] * (1 - (frac - lo)) + channelData[hi] * (frac - lo);
      }
    } else { samples = channelData; }
    audioCtx.close();
    let wav = encodeWAV(samples, 16000), b64 = _btoa(wav);
    setStatus('转写中…');
    let r = await api('/voice/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio: b64 })
    });
    if (!r.ok) {
      if (r.status === 404) throw new Error('服务端语音识别未配置，请使用 Chrome/Edge 浏览器麦克风');
      throw new Error('服务端错误 ' + r.status);
    }
    let d = await r.json();
    if (d.text) { document.getElementById('input').value = d.text; sendText(); }
    else { setStatus('空闲'); addMsg('sys', '🎤 未检测到语音'); }
  } catch (e) {
    console.error('Mic error:', e);
    addMsg('sys', '🎤 错误: ' + e.message);
    setStatus('空闲');
  }
  _micRecorder = null;
}

function resetMicButton() {
  let btn = document.getElementById('mic-btn');
  if (!btn) return;
  btn.textContent = '🎤';
  btn.style.borderColor = '#222';
  btn.style.color = 'var(--text)';
  btn.style.animation = '';
}
