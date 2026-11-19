let writer = null;
function setHw(text, ok){
  const el = document.getElementById('hw');
  if(el){ el.textContent = text; el.style.color = ok ? '#1f8a4c' : '#c62828'; }
}
async function connectArduino(){
  if(!('serial' in navigator)){ alert('Web Serial needs Chrome or Edge.'); return; }
  try{
    const port = await navigator.serial.requestPort();
    await port.open({ baudRate: 9600 });
    writer = port.writable.getWriter();
    setHw('Connecting... wait 2 seconds', true);
    await new Promise(r => setTimeout(r, 2000));  // Uno resets when port opens
    setHw('Arduino connected', true);
    port.addEventListener('disconnect', () => { writer = null; setHw('Hardware not connected', false); });
  }catch(e){
    writer = null;
    setHw('Hardware not connected', false);
    console.error(e);
  }
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
