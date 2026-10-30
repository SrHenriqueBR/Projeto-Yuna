const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

async function setup({local = true, failure = false, reply} = {}) {
  function node() {
    const listeners = {}, children = [], classes = new Set(), attrs = {};
    const item = {listeners, children, value:'', textContent:'', checked:false, dataset:{},
      addEventListener: (key, fn) => { (listeners[key] ??= []).push(fn); },
      async emit(key, event = {}) { await Promise.all((listeners[key] || []).map(fn => fn(event))); },
      setAttribute: (k,v) => {attrs[k] = v;}, getAttribute: k => attrs[k],
      classList: {add: c => classes.add(c), remove: c => classes.delete(c)},
      querySelector: () => null, appendChild(child) { children.push(child); child.parent = item; },
      remove() { const i = item.parent?.children.indexOf(item); if (i >= 0) item.parent.children.splice(i,1); },
      focus() { this.focused = true; }};
    return item;
  }
  const ids = Object.fromEntries(['chatForm','chatInput','sendChat','connectChat','chatConnection',
    'chatMessages','chatSetup','chatDetail','chatError','readReplies','stage','chatActivity','stopChatVoice',
    'chatConversation','conversationHint','chatEmptyTitle','chatEmptyNote'].map(id => [id,node()]));
  const prompts = [node()]; prompts[0].dataset.chatPrompt = 'Olá, Yuna!';
  const modes = ['companhia','desabafo','conselho'].map(mode => {
    const button = node(); button.dataset.conversationMode=mode; button.id='mode-'+mode; return button;
  });
  const calls = [], timers = new Map(); let sequence = 0;
  const document = {getElementById: id => ids[id], querySelectorAll: selector => selector === '[data-conversation-mode]' ? modes : prompts, createElement: () => node()};
  const window = {addEventListener() {}, setTimeout(fn) { const id=++sequence; timers.set(id,fn); return id; }, clearTimeout: id => timers.delete(id)};
  const fetch = async (url, options) => {
    calls.push({url, options});
    let data;
    if (url === '/api/status') data = {ready:true,model:'modelo-de-teste',token:'session-token',detail:'Pronta.'};
    else if (url === '/api/history') data = {messages:[]};
    else {
      if (reply) return reply(url,options);
      data = failure ? {error:'Abra o Ollama.'} : {answer:'Olá! <img src=x onerror=alert(1)>'};
    }
    return {ok: !(failure && url === '/api/chat'), json:async () => data};
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../docs/yuna-chat.js'),'utf8'),
    {window, document, fetch, AbortController, location:{protocol:local?'http:':'https:',hostname:local?'127.0.0.1':'raw.githack.com'}});
  await new Promise(resolve => setImmediate(resolve));
  return {ids, prompts, modes, calls, submit: () => ids.chatForm.emit('submit',{preventDefault(){}})};
}

test('página pública explica como conectar e não procura serviços no computador', async () => {
  const app = await setup({local:false});
  assert.equal(app.calls.length,0);
  assert.equal(app.ids.chatInput.disabled,true);
  assert.equal(app.ids.sendChat.disabled,true);
  assert.equal(app.ids.chatSetup.hidden,false);
  assert.match(app.ids.chatDetail.textContent,/iniciar_yuna_web.bat/);
});

test('conversa envia mensagem e sessão local e trata a resposta apenas como texto', async () => {
  const app = await setup();
  app.ids.chatInput.value = 'Oi!'; await app.ids.chatInput.emit('input'); await app.submit();
  const request = app.calls.find(call => call.url === '/api/chat');
  assert.equal(JSON.parse(request.options.body).message,'Oi!');
  assert.equal(JSON.parse(request.options.body).mode,'companhia');
  assert.equal(request.options.headers['X-Yuna-Token'],'session-token');
  assert.equal(app.ids.chatMessages.children.length,2);
  assert.equal(app.ids.chatMessages.children[1].children[1].textContent,'Olá! <img src=x onerror=alert(1)>');
  assert.equal(app.ids.chatMessages.children[1].children[1].children.length,0);
  assert.equal(app.ids.stage.dataset.chatState,'replying');
});

test('erro do modelo mantém o pedido para tentar de novo sem inventar resposta', async () => {
  const app = await setup({failure:true});
  app.ids.chatInput.value = 'Vamos conversar?'; await app.submit();
  assert.equal(app.ids.chatMessages.children.length,0);
  assert.equal(app.ids.chatInput.value,'Vamos conversar?');
  assert.equal(app.ids.chatError.textContent,'Abra o Ollama.');
  assert.equal(app.ids.chatInput.disabled,false);
});

test('envio duplo é bloqueado enquanto a personagem pensa', async () => {
  let complete;
  const app = await setup({reply: () => new Promise(resolve => {complete=resolve;})});
  app.ids.chatInput.value = 'Um pedido'; const first = app.submit();
  await app.submit();
  assert.equal(app.calls.filter(call => call.url === '/api/chat').length,1);
  assert.equal(app.ids.stage.dataset.chatState,'thinking');
  assert.equal(app.ids.chatInput.disabled,true);
  complete({ok:true,json:async()=>({answer:'Aqui está.'})}); await first;
  assert.equal(app.ids.chatInput.disabled,false);
});

test('modo conselho vai ao servidor e alternar o modo preserva a conversa', async () => {
  const app = await setup();
  await app.modes[2].emit('click');
  assert.equal(app.modes[2].getAttribute('aria-selected'),'true');
  assert.match(app.ids.chatInput.placeholder,/situação/);
  assert.equal(app.calls.filter(call=>call.url==='/api/chat').length,0);
  app.ids.chatInput.value='Estou pensando numa escolha.'; await app.submit();
  assert.equal(JSON.parse(app.calls.find(call=>call.url==='/api/chat').options.body).mode,'conselho');
  await app.modes[1].emit('click');
  assert.equal(app.ids.chatMessages.children.length,2);
  assert.equal(app.modes[1].getAttribute('aria-selected'),'true');
});

test('abas respondem ao teclado e não enviam mensagens ao selecionar um modo', async () => {
  const app = await setup({local:false});
  await app.modes[0].emit('keydown',{key:'ArrowRight',preventDefault(){}});
  assert.equal(app.modes[1].getAttribute('aria-selected'),'true');
  assert.equal(app.modes[1].focused,true);
  assert.equal(app.ids.chatConversation.getAttribute('aria-labelledby'),'mode-desabafo');
  assert.match(app.ids.chatInput.placeholder,/pesando/);
  assert.equal(app.calls.length,0);
});
