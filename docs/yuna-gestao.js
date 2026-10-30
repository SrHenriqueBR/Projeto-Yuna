(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const form = $('ownerForm'), password = $('ownerPassword'), message = $('managerMessage');
  if (!form) return;
  const local = location.protocol === 'http:' && ['127.0.0.1','localhost'].includes(location.hostname);
  let token = '', busy = false;
  const labels = {pending:'Aguardando revisão',approved:'Aprovado',rejected:'Rejeitado',withdrawn:'Retirado pelo remetente'};
  const events = {proposal_shared_with_consent:'Sugestão compartilhada com autorização',learning_approved:'Aprendizado aprovado',learning_rejected:'Aprendizado rejeitado ou retirado',proposal_withdrawn_by_sender:'Remetente retirou o texto'};
  async function api(path, data) {
    const response = await fetch(path, {method:data === undefined ? 'GET':'POST',credentials:'same-origin',cache:'no-store',
      headers:{'Content-Type':'application/json','X-Yuna-Token':token},body:data === undefined ? undefined:JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok) { const error = new Error(result.error || 'Não consegui concluir o pedido.'); error.status=response.status; throw error; }
    return result;
  }
  function signedOut() { $('managerLogin').hidden=false; $('managerDashboard').hidden=true; password.value=''; }
  async function refresh() {
    const result = await api('/api/admin/state');
    $('managerLogin').hidden=true; $('managerDashboard').hidden=false;
    $('ownerName').textContent='Revisões de ' + result.owner.name;
    $('proposalList').replaceChildren(); $('auditList').replaceChildren();
    if (!result.proposals.length) $('proposalList').textContent='Nenhum texto foi compartilhado para revisão.';
    for (const item of result.proposals) {
      const card=document.createElement('article');card.className='proposal';
      const status=document.createElement('span');status.className='status';status.textContent=labels[item.status] || item.status;
      const text=document.createElement('p');text.textContent=item.content || 'Texto retirado por quem compartilhou.';
      const date=document.createElement('small');date.textContent='Compartilhado em ' + new Date(item.created).toLocaleString('pt-BR');
      card.append(status,text,date);
      if (item.status !== 'withdrawn') {
        const row=document.createElement('div');
        for (const [decision,label] of [['approved',item.status==='rejected'?'Aprovar novamente':'Aprovar'],['rejected',item.status==='approved'?'Retirar da base':'Rejeitar']]) {
          if (decision===item.status) continue;
          const button=document.createElement('button');button.type='button';button.textContent=label;
          button.addEventListener('click',async()=>{
            if (busy) return; busy=true;button.disabled=true;message.textContent='Salvando revisão…';
            try { await api('/api/admin/review',{id:item.id,decision});await refresh();message.textContent='Revisão salva.'; }
            catch(error) {message.textContent=error.message;if(error.status===401)signedOut();}
            finally {busy=false;button.disabled=false;}
          });row.appendChild(button);
        }
        card.appendChild(row);
      }
      $('proposalList').appendChild(card);
    }
    if (!result.audit.length) $('auditList').textContent='Nenhuma revisão registrada.';
    for (const event of result.audit) {
      const row=document.createElement('div');row.className='audit';
      row.textContent=new Date(event.created).toLocaleString('pt-BR')+' · '+(events[event.event]||event.event);
      $('auditList').appendChild(row);
    }
  }
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!local)return;
    busy=true;$('ownerLogin').disabled=true;message.textContent='Verificando acesso…';
    const secret=password.value;password.value='';
    try {await api('/api/admin/login',{password:secret});await refresh();message.textContent='Acesso autorizado nesta instalação.';}
    catch(error){message.textContent=error.message;}
    finally{busy=false;$('ownerLogin').disabled=false;}
  });
  $('refreshManager').addEventListener('click',async()=>{if(busy)return;try{await refresh();message.textContent='Painel atualizado.';}catch(error){message.textContent=error.message;if(error.status===401)signedOut();}});
  $('ownerLogout').addEventListener('click',async()=>{if(busy)return;try{await api('/api/admin/logout',{});signedOut();message.textContent='Sessão encerrada.';}catch(error){message.textContent=error.message;}});
  async function start() {
    if(!local){$('managerSetup').textContent='Prévia do painel. Para gerenciar, abra iniciar_yuna_web.bat e entre pelo endereço local.';return;}
    try {
      const state=await api('/api/governance');token=state.token;
      $('managerSetup').textContent=state.owner?'Responsável configurado: '+state.owner.name:'Configure primeiro o responsável pelo configurar_gestao_yuna.bat.';
      password.disabled=!state.owner;$('ownerLogin').disabled=!state.owner;
      if(state.owner)try{await refresh();}catch(error){if(error.status!==401)throw error;}
    }catch(error){message.textContent='Não consegui abrir a gestão local. Mantenha iniciar_yuna_web.bat aberto.';}
  }
  start();
})();
