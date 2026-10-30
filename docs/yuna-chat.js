/* Chat real pela aplicação local. A página pública não procura serviços no PC. */
(function () {
  'use strict';
  const form = document.getElementById('chatForm');
  if (!form) return;
  const input = document.getElementById('chatInput');
  const send = document.getElementById('sendChat');
  const connect = document.getElementById('connectChat');
  const connection = document.getElementById('chatConnection');
  const messages = document.getElementById('chatMessages');
  const setup = document.getElementById('chatSetup');
  const detail = document.getElementById('chatDetail');
  const error = document.getElementById('chatError');
  const read = document.getElementById('readReplies');
  const stage = document.getElementById('stage');
  const activity = document.getElementById('chatActivity');
  const prompts = Array.from(document.querySelectorAll('[data-chat-prompt]'));
  const local = location.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(location.hostname);
  const voiceAvailable = 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance === 'function';
  let token = '', ready = false, busy = false, connected = false, generation = 0;
  let reactionTimer = 0;

  function caption(text, label) {
    const speech = document.getElementById('speech');
    if (!speech) return;
    speech.textContent = text.length > 180 ? text.slice(0, 177) + '…' : text;
    const bubble = speech.closest('.bubble');
    if (bubble) {
      bubble.setAttribute('aria-live', 'off');
      const type = bubble.querySelector('.bubble-type');
      if (type) type.textContent = label;
    }
  }

  function controls() {
    input.disabled = !ready || busy;
    send.disabled = !ready || busy || !input.value.trim();
    connect.disabled = busy || !local;
    read.disabled = !voiceAvailable || !ready;
    for (const button of prompts) button.disabled = !ready || busy;
    form.setAttribute('aria-busy', String(busy));
    send.textContent = busy ? 'Pensando…' : 'Enviar ↗';
  }

  function reaction(state) {
    window.clearTimeout(reactionTimer);
    stage.dataset.chatState = state;
    activity.textContent = ({typing: 'Atenta à sua mensagem', thinking: 'Pensando na resposta…',
      replying: 'Sua vez, estou por aqui ♡', idle: 'Pronta para interagir'})[state];
    if (state === 'replying' || state === 'typing')
      reactionTimer = window.setTimeout(() => reaction('idle'), state === 'typing' ? 3500 : 5000);
  }

  function addMessage(role, content) {
    messages.querySelector('.chat-empty')?.remove();
    const item = document.createElement('div');
    item.className = 'chat-message ' + (role === 'user' ? 'from-user' : 'from-yuna');
    const name = document.createElement('strong');
    name.textContent = role === 'user' ? 'Você' : 'Yuna';
    const body = document.createElement('p');
    body.textContent = content;
    item.appendChild(name); item.appendChild(body); messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
    return item;
  }

  async function request(path, options = {}, timeout = 10000) {
    const abort = new AbortController();
    const timer = window.setTimeout(() => abort.abort(), timeout);
    try {
      const response = await fetch(path, {...options, signal: abort.signal, cache: 'no-store',
        headers: {'Content-Type': 'application/json', 'X-Yuna-Token': token, ...options.headers}});
      let data;
      try { data = await response.json(); } catch (_) { throw new Error('A conexão local não retornou uma resposta válida. Reabra iniciar_yuna_web.bat.'); }
      if (!response.ok) throw new Error(data.error || 'Não consegui concluir o pedido. Tente novamente.');
      return data;
    } catch (failure) {
      if (failure.name === 'AbortError') throw new Error('A resposta demorou demais. Verifique o Ollama antes de tentar novamente.');
      throw failure;
    } finally { window.clearTimeout(timer); }
  }

  async function start() {
    if (busy) return;
    error.textContent = '';
    ready = false; controls();
    if (!local) {
      connection.textContent = 'Prévia online · chat no notebook';
      detail.textContent = 'Para conversar com a IA, baixe o projeto e abra iniciar_yuna_web.bat no computador com Ollama. Depois clique em Abrir chat local.';
      setup.hidden = false;
      return;
    }
    connection.textContent = 'Conectando…';
    connect.disabled = true;
    try {
      const status = await request('/api/status');
      if (typeof status.token !== 'string') throw new Error('Abra esta página pelo iniciar_yuna_web.bat.');
      token = status.token;
      ready = status.ready === true;
      connection.textContent = ready ? '● Conectada · ' + status.model : 'Ollama precisa de atenção';
      detail.textContent = status.detail;
      setup.hidden = ready;
      if (!connected) {
        const history = await request('/api/history');
        if (!Array.isArray(history.messages)) throw new Error('Não consegui carregar o histórico. Clique em Reconectar.');
        messages.setAttribute('aria-live', 'off');
        for (const item of history.messages) {
          if (['user', 'assistant'].includes(item.role) && typeof item.content === 'string')
            addMessage(item.role, item.content);
        }
        messages.setAttribute('aria-live', 'polite');
        connected = true;
      }
    } catch (failure) {
      ready = false;
      connection.textContent = 'Chat desconectado';
      detail.textContent = 'Mantenha iniciar_yuna_web.bat aberto e tente Reconectar.';
      error.textContent = failure.message || 'Não consegui me conectar à Yuna local.';
      setup.hidden = false;
    }
    controls();
  }

  function stopVoice() {
    generation++;
    if (voiceAvailable) window.speechSynthesis.cancel();
    stage.classList.remove('is-speaking');
  }

  function speak(text) {
    if (!read.checked || !voiceAvailable) return;
    stopVoice();
    window.yunaVoiceOwner = "chat";
    const current = generation;
    try {
      const phrase = new window.SpeechSynthesisUtterance(text);
      phrase.lang = 'pt-BR'; phrase.rate = 1.04; phrase.pitch = 1.08;
      const voices = window.speechSynthesis.getVoices();
      phrase.voice = voices.find(v => /^pt-BR/i.test(v.lang) && /maria|francisca|raquel|camila|luciana|female/i.test(v.name)) ||
        voices.find(v => /^pt/i.test(v.lang)) || null;
      phrase.onstart = () => { if (current === generation && window.yunaVoiceOwner === "chat") stage.classList.add('is-speaking'); };
      phrase.onend = () => { if (current === generation && window.yunaVoiceOwner === "chat") stage.classList.remove('is-speaking'); };
      phrase.onerror = event => {
        if (current !== generation || window.yunaVoiceOwner !== "chat") return;
        stage.classList.remove('is-speaking');
        if (!['canceled', 'interrupted'].includes(event.error))
          error.textContent = 'A voz não pôde ser reproduzida. A resposta está disponível por escrito.';
      };
      window.speechSynthesis.speak(phrase);
    } catch (_) { error.textContent = 'Não consegui reproduzir a voz neste navegador.'; }
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message || !ready || busy) return;
    stopVoice(); busy = true; error.textContent = ''; controls(); reaction('thinking');
    caption('Estou pensando na sua pergunta…', 'CONVERSA LOCAL');
    const row = addMessage('user', message);
    input.value = '';
    try {
      const response = await request('/api/chat', {method: 'POST', body: JSON.stringify({message})}, 370000);
      if (typeof response.answer !== 'string' || !response.answer.trim()) throw new Error('A Yuna retornou uma resposta vazia. Tente novamente.');
      addMessage('assistant', response.answer); caption(response.answer, 'RESPOSTA DO CHAT');
      reaction('replying'); speak(response.answer);
    } catch (failure) {
      row.remove(); input.value = message; reaction('idle');
      caption('Não consegui concluir a resposta. Confira o aviso no chat e tente novamente.', 'CONVERSA LOCAL');
      error.textContent = failure.message || 'Não consegui obter a resposta. Verifique o Ollama e tente novamente.';
    } finally { busy = false; controls(); input.focus(); }
  });
  input.addEventListener('input', () => { controls(); reaction(input.value.trim() ? 'typing' : 'idle'); });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault(); if (!send.disabled) form.requestSubmit();
    }
  });
  for (const button of prompts) button.addEventListener('click', () => {
    if (!ready || busy) return;
    input.value = button.dataset.chatPrompt; controls(); reaction('typing'); input.focus();
  });
  connect.addEventListener('click', start);
  read.addEventListener('change', () => { if (!read.checked) stopVoice(); });
  document.getElementById('stopChatVoice').addEventListener('click', stopVoice);
  window.addEventListener('pagehide', () => { stopVoice(); window.clearTimeout(reactionTimer); });
  reaction('idle'); controls(); start();
})();
