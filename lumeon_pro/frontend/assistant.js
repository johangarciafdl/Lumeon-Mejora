(() => {
  'use strict';
  const API = '/api/v2/assistant/action';
  const state = { pending: false };

  function esc(value) {
    return String(value ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
  }

  function mount() {
    if (document.getElementById('lumeon-assistant')) return;
    const fab = document.createElement('button');
    fab.className = 'la-fab'; fab.id = 'lumeon-assistant-fab'; fab.title = 'Abrir asistente'; fab.textContent = '✦';
    fab.onclick = () => { panel.classList.add('open'); fab.classList.add('hidden'); input.focus(); };
    const panel = document.createElement('section'); panel.id = 'lumeon-assistant'; panel.setAttribute('aria-label','Asistente Lumeon');
    panel.innerHTML = `<header class="la-header"><div><div class="la-title">Asistente Lumeon</div><div class="la-subtitle">Clientes · productos · ventas · facturas</div></div><button class="la-close" aria-label="Cerrar">×</button></header><div class="la-messages" id="la-messages"></div><form class="la-composer"><input class="la-input" autocomplete="off" placeholder="Escribe una acción…" aria-label="Mensaje"><button class="la-send" type="submit">Enviar</button></form>`;
    document.body.append(fab, panel);
    const input = panel.querySelector('.la-input');
    const messages = panel.querySelector('#la-messages');
    panel.querySelector('.la-close').onclick = () => { panel.classList.remove('open'); fab.classList.remove('hidden'); };
    panel.querySelector('form').onsubmit = async e => { e.preventDefault(); const text=input.value.trim(); if(!text)return; input.value=''; addMessage(text,'user'); await handle(text); };
    addMessage('Hola. Puedo buscar clientes y productos, consultar inventario y preparar ventas. Las operaciones que modifican datos requieren confirmación.', 'bot');

    function addMessage(text, who='bot', actions=[]) {
      const div=document.createElement('div'); div.className=`la-msg ${who}`; div.innerHTML=esc(text);
      if(actions.length){ const box=document.createElement('div'); box.className='la-actions'; actions.forEach(a=>{const b=document.createElement('button');b.type='button';b.className=`la-action ${a.kind||''}`;b.textContent=a.label;b.onclick=a.onClick;box.appendChild(b)});div.appendChild(box);}
      messages.appendChild(div); messages.scrollTop=messages.scrollHeight;
    }

    async function call(mode, payload={}) {
      const response=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({mode,...payload})});
      let body={}; try{body=await response.json();}catch{}
      if(!response.ok) throw new Error(body.error||`Error HTTP ${response.status}`);
      return body;
    }

    async function handle(text){
      try {
        if(/^\s*(si|sí|confirmo|confirmar|ok|acepto)\s*$/i.test(text) && state.pending){
          const result=await call('confirm',{confirmation_token:state.pending}); state.pending=null; renderResult(result); return;
        }
        if(/^\s*(no|cancelar|cancela)\s*$/i.test(text) && state.pending){
          await call('cancel',{confirmation_token:state.pending}); state.pending=null; addMessage('Operación cancelada.','bot'); return;
        }
        const result=await call('propose',{text});
        if(result.status==='confirmation_required'){
          state.pending=result.confirmation_token||result.token||null;
          renderResult(result,[{label:'Confirmar',kind:'confirm',onClick:async()=>{if(!state.pending)return;try{const r=await call('confirm',{confirmation_token:state.pending});state.pending=null;renderResult(r)}catch(e){addMessage(e.message,'bot')}}},{label:'Cancelar',kind:'cancel',onClick:async()=>{try{await call('cancel',{confirmation_token:state.pending});state.pending=null;addMessage('Operación cancelada.','bot')}catch(e){addMessage(e.message,'bot')}}}]);
        } else renderResult(result);
      } catch(e){ addMessage(`No pude completar la acción: ${e.message}`,'bot'); }
    }

    function renderResult(result, actions=[]){
      let text=result.message||result.error||'Operación procesada.';
      if(result.data) text += `\n${JSON.stringify(result.data,null,2)}`;
      if(result.whatsapp_status) text += `\nWhatsApp: ${result.whatsapp_status}`;
      addMessage(text,'bot',actions);
    }
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount); else mount();
})();
