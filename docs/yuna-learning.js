(function () {
  'use strict';
  const $=id=>document.getElementById(id);
  const form=$('learningForm');if(!form)return;
  const local=location.protocol==='http:'&&['127.0.0.1','localhost'].includes(location.hostname);
  let token='',owner=null,proof=null,busy=false;
  const labels={pending:'Aguardando revisão',approved:'Aprovado para referência geral',rejected:'Não incorporado à base',withdrawn:'Retirado por você'};
  async function api(path,data){
    const response=await fetch(path,{method:data===undefined?'GET':'POST',cache:'no-store',headers:{'Content-Type':'application/json','X-Yuna-Token':token},body:data===undefined?undefined:JSON.stringify(data)});
    const result=await response.json();if(!response.ok)throw new Error(result.error||'Não consegui concluir o pedido.');return result;
  }
  function controls(){
    $('learningText').disabled=!owner||busy;$('learningConsent').disabled=!owner||busy;
    $('sendLearning').disabled=!owner||busy||!$('learningConsent').checked||!$('learningText').value.trim();
    $('withdrawLearning').disabled=busy||!proof;$('checkLearning').disabled=busy||!proof;
  }
  form.addEventListener('input',controls);
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(!owner||busy||!$('learningConsent').checked)return;
    busy=true;controls();$('learningMessage').textContent='Enviando somente o texto que você revisou…';
    try{
      proof=await api('/api/learning/propose',{text:$('learningText').value,consent:true,owner_id:owner.id});
      $('learningMessage').textContent='Aguardando revisão de '+owner.name+'. Suas outras mensagens não foram enviadas.';
      $('learningConsent').checked=false;$('learningText').value='';$('learningReceipt').hidden=false;$('learningReceipt').open=true;
      $('receiptText').value=JSON.stringify({id:proof.id,receipt:proof.receipt});
    }catch(error){$('learningMessage').textContent=error.message;}
    finally{busy=false;controls();}
  });
  $('withdrawLearning').addEventListener('click',async()=>{
    if(!proof||busy)return;busy=true;controls();
    try{await api('/api/learning/withdraw',proof);$('learningMessage').textContent='Texto retirado da fila e fora da base comum.';}
    catch(error){$('learningMessage').textContent=error.message;}finally{busy=false;controls();}
  });
  $('checkLearning').addEventListener('click',async()=>{
    if(!proof||busy)return;busy=true;controls();
    try{const result=await api('/api/learning/status',proof);$('learningMessage').textContent=labels[result.status]||result.status;}
    catch(error){$('learningMessage').textContent=error.message;}finally{busy=false;controls();}
  });
  $('restoreReceipt').addEventListener('click',()=>{
    if(!local||busy)return;
    try{const value=JSON.parse($('receiptText').value);if(typeof value.id!=='string'||typeof value.receipt!=='string')throw new Error();proof={id:value.id,receipt:value.receipt};$('learningMessage').textContent='Comprovante carregado. Você pode consultar ou retirar o texto.';controls();}
    catch(error){$('learningMessage').textContent='Cole o comprovante completo, com id e receipt.';}
  });
  async function start(){
    $('restoreReceipt').disabled=!local;$('receiptText').disabled=!local;
    controls();
    if(!local){$('learningOwner').textContent='O compartilhamento de aprendizados é configurado na versão local. Nenhum texto é enviado nesta prévia.';return;}
    try{
      const state=await api('/api/governance');token=state.token;owner=state.owner;
      $('learningOwner').textContent=owner?'Responsável desta instalação: '+owner.name+'. Ele poderá revisar apenas o texto que você compartilhar abaixo.':'Nenhum responsável configurado. Seus aprendizados pessoais continuam locais.';
      $('learningConsentLabel').textContent=owner?'Autorizo compartilhar este texto com '+owner.name+' para revisão e possível uso como referência geral nesta instalação.':'Configure o responsável antes de compartilhar.';
      controls();
    }catch(error){$('learningOwner').textContent='Gestão local indisponível. Mantenha iniciar_yuna_web.bat aberto.';}
  }
  start();
})();
