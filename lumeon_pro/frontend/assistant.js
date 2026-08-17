(() => {
  'use strict';
  const API = '/api/v2/assistant/message';
  const SESSION_KEY = 'lumeon_assistant_session';
  const state = { pending: false };

  function esc(value) {
    return String(value ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
  }

  function mount() {
    if (document.getElementById('lumeon-assistant')) return;
    const fab = document.createElement('button');
    fab.className = 'la-fab'; fab.id = 'lumeon-assistant-fab'; fab.title = 'Abrir asistente'; fab.textContent = '✦';
    const panel = document.createElement('section'); panel.id = 'lumeon-assistant'; panel.setAttribute('aria-label','Asistente Lumeon');
    panel.innerHTML = `<header class="la-header"><div><div class="la-title">Asistente Lumeon</div><div class="la-subtitle">Clientes · productos · inventario · ventas · facturas</div></div><button class="la-close" aria-label="Cerrar">×</button></header><div class="la-messages" id="la-messages"></div><form class="la-composer"><input class="la-input" autocomplete="off" maxlength="500" placeholder="Escribe una acción…" aria-label="Mensaje"><button class="la-send" type="submit">Enviar</button></form>`;
    document.body.append(fab, panel);
    const input = panel.querySelector('.la-input');
    const messages = panel.querySelector('#la-messages');
    fab.onclick = () => { panel.classList.add('open'); fab.classList.add('hidden'); input.focus(); };
    panel.querySelector('.la-close').onclick = () => { panel.classList.remove('open'); fab.classList.remove('hidden'); };
    panel.querySelector('form').onsubmit = async e => { e.preventDefault(); const text=input.value.trim(); if(!text)return; input.value=''; addMessage(text,'user'); await handle(text); };
    addMessage('Hola. Puedo buscar clientes y productos, consultar inventario y preparar operaciones. Las acciones que modifican datos requieren confirmación.','bot');

    function addMessage(text, who='bot', actions=[]) {
      const div=document.createElement('div'); div.className=`la-msg ${who}`; div.innerHTML=esc(text);
      if(actions.length){ const box=document.createElement('div'); box.className='la-actions'; actions.forEach(a=>{const b=document.createElement('button');b.type='button';b.className=`la-action ${a.kind||''}`;b.textContent=a.label;b.onclick=a.onClick;box.appendChild(b)});div.appendChild(box);}
      messages.appendChild(div); messages.scrollTop=messages.scrollHeight;
    }

    async function call(text) {
      const headers={'Content-Type':'application/json'};
      let sid=localStorage.getItem(SESSION_KEY);
      if(!sid){sid=crypto.randomUUID();localStorage.setItem(SESSION_KEY,sid)}
      headers['X-Assistant-Session']=sid;
      const response=await fetch(API,{method:'POST',headers,credentials:'same-origin',body:JSON.stringify({text})});
      let body={}; try{body=await response.json();}catch{}
      if(!response.ok) throw new Error(body.error||`Error HTTP ${response.status}`);
      return body;
    }

    async function handle(text){
      try {
        const result=await call(text);
        if(result.status==='executed') state.pending=false;
        if(result.status==='cancelled') state.pending=false;
        if(result.status==='confirmation_required') state.pending=true;
        renderResult(result, result.status==='confirmation_required' ? [
          {label:'Confirmar',kind:'confirm',onClick:()=>handle('sí')},
          {label:'Cancelar',kind:'cancel',onClick:()=>handle('cancelar')}
        ] : []);
      } catch(e){ addMessage(`No pude completar la acción: ${e.message}`,'bot'); }
    }

    function renderResult(result, actions=[]) {
      let text=result.message||result.error||'Operación procesada.';
      if(Array.isArray(result.results)) {
        if(!result.results.length) text += '\nSin resultados.';
        else text += '\n' + result.results.slice(0,20).map((row,i)=>`${i+1}. ${Object.entries(row).map(([k,v])=>`${k}: ${v ?? ''}`).join(' · ')}`).join('\n');
      }
      if(result.id) text += `\nID: ${result.id}`;
      if(result.whatsapp_status) text += `\nWhatsApp: ${result.whatsapp_status}`;
      addMessage(text,'bot',actions);
    }
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount); else mount();
})();
