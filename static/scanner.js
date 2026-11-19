let mode = 'attendance';
const ID_RE = /^TUPM-[0-9]{2}-[0-9]{4}$/;
const COOLDOWN = 4000;
const recent = new Map();
const CODE = {present:'OK', late:'LATE', enrolled:'OK', duplicate:'ERR', not_enrolled:'ERR', no_session:'ERR', invalid:'ERR'};

function setMode(m){
  mode = m;
  document.getElementById('m_att').classList.toggle('on', m === 'attendance');
  document.getElementById('m_enr').classList.toggle('on', m === 'enroll');
}

function show(cls, big, small){
  const el = document.getElementById('result');
  el.className = cls;
  el.innerHTML = '';
  el.append(document.createTextNode(big));
  const s = document.createElement('small');
  s.textContent = small || '';
  el.append(s);
}

function logLine(text){
  const li = document.createElement('li');
  li.textContent = new Date().toLocaleTimeString() + '  ' + text;
  const ul = document.getElementById('log');
  ul.prepend(li);
  while(ul.children.length > 30) ul.removeChild(ul.lastChild);
}

async function handleId(raw, manual){
  raw = (raw || '').trim();
  if(!raw) return;
  const now = Date.now();
  if(!manual && recent.has(raw) && now - recent.get(raw) < COOLDOWN) return;
  recent.set(raw, now);
  const id = raw.toUpperCase();
  if(!ID_RE.test(id)){
    show('err', 'Invalid QR', raw.slice(0, 40));
    sendToArduino('ERR', 'Invalid QR', '');
    logLine('Invalid QR');
    return;
  }
  try{
    const r = await fetch('/api/scan', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({tupm_id:id, mode})});
    if(r.status === 403 || r.redirected){ show('err', 'Login required', ''); return; }
    const d = await r.json();
    const code = CODE[d.result] || 'ERR';
    const cls = code === 'OK' ? 'ok' : code === 'LATE' ? 'late' : 'err';
    show(cls, d.message, id + (d.name ? ' - ' + d.name : ''));
    sendToArduino(code, d.message, id);
    logLine(id + ' ' + d.message);
    if(manual) document.getElementById('manual').value = '';
  }catch(e){
    show('err', 'Server error', '');
  }
}

async function startCamera(){
  const status = document.getElementById('camStatus');
  const sel = document.getElementById('cams');
  try{
    const cams = await Html5Qrcode.getCameras();
    if(!cams.length){ status.textContent = 'No camera found. Use manual entry.'; return; }
    cams.forEach((c, i) => { const o = document.createElement('option'); o.value = c.id; o.textContent = c.label || ('Camera ' + (i+1)); sel.append(o); });
    const scanner = new Html5Qrcode('reader');
    async function begin(id){
      try{ if(scanner.isScanning) await scanner.stop(); }catch(e){}
      await scanner.start(id, {fps:10, qrbox:{width:240, height:240}}, txt => handleId(txt, false), () => {});
      status.textContent = 'Camera running. Hold ID flat in view.';
    }
    sel.onchange = () => begin(sel.value);
    await begin(cams[0].id);
  }catch(e){
    status.textContent = 'Camera blocked or unavailable. Allow camera, or use manual entry.';
    console.error(e);
  }
}
startCamera();
document.getElementById('manual').addEventListener('keydown', e => { if(e.key === 'Enter') handleId(e.target.value, true); });
