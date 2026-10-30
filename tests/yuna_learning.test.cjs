const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');

async function setup(local=true){
 const node=()=>({value:'',textContent:'',checked:false,listeners:{},
   addEventListener(k,fn){(this.listeners[k]??=[]).push(fn);},
   async emit(k,e={}){await Promise.all((this.listeners[k]||[]).map(fn=>fn(e)));}});
 const names=['learningForm','learningOwner','learningText','learningConsent','sendLearning','withdrawLearning',
  'checkLearning','learningMessage','learningReceipt','receiptText','restoreReceipt','learningConsentLabel'];
 const ids=Object.fromEntries(names.map(id=>[id,node()]));const calls=[];
 const fetch=async(url,options)=>{calls.push({url,options});const data=url==='/api/governance'?
   {owner:{id:'owner-test',name:'Responsável de teste'},token:'csrf-test'}:
   url==='/api/learning/propose'?{id:'proposal-test',receipt:'receipt-test'}:{status:'withdrawn'};
   return {ok:true,json:async()=>data};};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../docs/yuna-learning.js'),'utf8'),
  {document:{getElementById:id=>ids[id]},fetch,location:{protocol:local?'http:':'https:',hostname:local?'127.0.0.1':'raw.githack.com'}});
 await new Promise(resolve=>setImmediate(resolve));return {ids,calls};
}

test('prévia pública não faz conexões nem aceita comprovantes privados',async()=>{
 const app=await setup(false);assert.equal(app.calls.length,0);
 assert.equal(app.ids.learningText.disabled,true);assert.equal(app.ids.receiptText.disabled,true);
});

test('carregar a página ou enviar sem autorização não compartilha textos',async()=>{
 const app=await setup();app.ids.learningText.value='Uma dica geral de organização para estudar.';
 await app.ids.learningForm.emit('submit',{preventDefault(){}});
 assert.equal(app.calls.length,1);assert.equal(app.calls[0].url,'/api/governance');
});

test('compartilha só o texto revisado com o destinatário indicado e permite retirada',async()=>{
 const app=await setup();const text='Uma dica geral de organização para estudar.';
 app.ids.learningText.value=text;app.ids.learningConsent.checked=true;
 await app.ids.learningForm.emit('submit',{preventDefault(){}});
 const sent=app.calls.find(call=>call.url==='/api/learning/propose');
 assert.deepEqual(JSON.parse(sent.options.body),{text,consent:true,owner_id:'owner-test'});
 assert.equal(app.ids.learningConsent.checked,false);
 assert.equal(app.ids.learningText.value,'');
 assert.equal(JSON.parse(app.ids.receiptText.value).receipt,'receipt-test');
 await app.ids.withdrawLearning.emit('click');
 const withdrawal=app.calls.find(call=>call.url==='/api/learning/withdraw');
 assert.equal(JSON.parse(withdrawal.options.body).receipt,'receipt-test');
 assert.match(app.ids.learningMessage.textContent,/retirado/);
});
