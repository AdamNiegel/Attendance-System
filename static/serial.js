let writer = null, port = null;
const sleep = ms => new Promise(r => setTimeout(r, ms));

function setHw(text, ok){
  const el = document.getElementById('hw');
  if(el){ el.textContent = text; el.style.color = ok ? '#1f8a4c' : '#c62828'; }
}

async function openPort(p){
  port = p;
  await p.open({ baudRate: 9600 });
  setHw('Connecting... wait 3 seconds', true);
  await sleep(3000);  // Uno resets when port opens
  writer = p.writable.getWriter();
  setHw('Arduino connected', true);
}

async function connectArduino(){
  if(!('serial' in navigator)){ alert('Web Serial needs Chrome or Edge.'); return; }
  try{
    await openPort(await navigator.serial.requestPort());
  }catch(e){
    writer = null;
    setHw('Hardware not connected', false);
    console.error(e);
  }
}

async function autoConnect(){
  if(!('serial' in navigator)) return;
  const ports = await navigator.serial.getPorts();
  if(!ports.length) return;
  for(let i = 0; i < 6; i++){
    try{ await openPort(ports[0]); return; }
    catch(e){ await sleep(500); }  // old page may still hold port
  }
  setHw('Hardware not connected', false);
}

async function sendToArduino(code, line1, line2){
  if(!writer){ setHw('Hardware not connected', false); return; }
  try{
    await writer.write(new TextEncoder().encode(code + ',' + line1 + ',' + line2 + '\n'));
  }catch(e){
    writer = null;
    setHw('Hardware not connected', false);
  }
}

if('serial' in navigator){
  navigator.serial.addEventListener('disconnect', () => { writer = null; setHw('Hardware not connected', false); });
}

window.addEventListener('pagehide', () => {
  try{ if(writer) writer.releaseLock(); if(port) port.close(); }catch(e){}
});

autoConnect();