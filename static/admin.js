async function api(method, url, body){
  try{
    const r = await fetch(url,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
    const d = await r.json().catch(()=>({}));
    if(!r.ok||d.ok===false){alert(d.message||'Error '+r.status);return d;}
    location.reload();
    return d;
  }catch(e){alert('Network error');}
}
