const API_BASE = 'http://192.168.0.49:5000';
const socket = io('http://192.168.0.49:5000');

function setStatus(msg, error = false) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.style.color = error ? '#f88' : '#8f8';
}

async function fetchVoicesAndSounds() {
  const [voices, sounds] = await Promise.all([
    fetch(`${API_BASE}/effect/cauldron/voices`).then(r => r.json()),
    fetch(`${API_BASE}/effect/cauldron/sounds`).then(r => r.json()),
  ]);
  const voiceSel = document.getElementById('voice-select');
  voiceSel.innerHTML = '';
  voices.voices.forEach(v => {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    voiceSel.appendChild(opt);
  });
  const soundSel = document.getElementById('sound-select');
  soundSel.innerHTML = '';
  sounds.sounds.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s;
    soundSel.appendChild(opt);
  });
}

function post(endpoint, data = {}) {
  return fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(r => r.json());
}

document.getElementById('start').onclick = () => post('/effect/cauldron/play').then(() => setStatus('Started'));
document.getElementById('stop').onclick = () => post('/effect/cauldron/stop').then(() => setStatus('Stopped'));
document.getElementById('explode').onclick = () => post('/effect/cauldron/explode').then(() => setStatus('Explosion!'));
document.getElementById('random-voice').onclick = () => post('/effect/cauldron/play_random_voice').then(() => setStatus('Random voice'));
document.getElementById('play-sound').onclick = () => {
  const sound = document.getElementById('sound-select').value;
  post('/effect/cauldron/play_sound', { sound }).then(() => setStatus(`Played sound: ${sound}`));
};
document.getElementById('start-voice').onclick = () => {
  const voice_name = document.getElementById('voice-select').value;
  post('/effect/cauldron/start_voice', { voice_name }).then(() => setStatus(`Started voice: ${voice_name}`));
};
document.getElementById('stop-voice').onclick = () => post('/effect/cauldron/stop_voice').then(() => setStatus('Stopped voice'));

fetchVoicesAndSounds();

// --- Voice streaming ---
let micActive = false;
let mediaStream = null;
let audioContext = null;
let processor = null;
const micBtn = document.getElementById('mic-toggle');
const micStatus = document.getElementById('mic-status');

micBtn.onclick = async () => {
  if (!micActive) {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
      const source = audioContext.createMediaStreamSource(mediaStream);
      processor = audioContext.createScriptProcessor(4096, 1, 1);
      source.connect(processor);
      processor.connect(audioContext.destination);
      processor.onaudioprocess = e => {
        if (!micActive) return;
        const input = e.inputBuffer.getChannelData(0);
        // Convert Float32 to Int16 PCM
        const buf = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
          let s = Math.max(-1, Math.min(1, input[i]));
          buf[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        socket.emit('voice_stream', buf.buffer);
      };
      micActive = true;
      micBtn.classList.add('active');
      micBtn.textContent = '🛑 Stop Streaming Voice';
      micStatus.textContent = 'Streaming...';
      setStatus('Microphone streaming started');
    } catch (e) {
      setStatus('Microphone error: ' + e, true);
    }
  } else {
    if (processor) processor.disconnect();
    if (audioContext) audioContext.close();
    if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
    micActive = false;
    micBtn.classList.remove('active');
    micBtn.textContent = '🎤 Start Streaming Voice';
    micStatus.textContent = '';
    setStatus('Microphone streaming stopped');
  }
};

socket.on('connect', () => setStatus('WebSocket connected'));
socket.on('disconnect', () => setStatus('WebSocket disconnected', true));
socket.on('error', data => setStatus('Error: ' + (data.error || data), true));
