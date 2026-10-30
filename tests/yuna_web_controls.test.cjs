const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

// Eventos e respostas de voz simulados: não depende de serviço de áudio ou rede.
function setup({ reduced = false, voice = true } = {}) {
  const events = target => {
    target.listeners = {};
    target.addEventListener = (name, fn) => (target.listeners[name] ??= []).push(fn);
    target.emit = (name, arg = {}) => (target.listeners[name] || []).forEach(fn => fn(arg));
    return target;
  };
  function element(classes = '') {
    const names = new Set(classes.split(' ').filter(Boolean));
    const attrs = {};
    return events({ dataset: {}, style: { setProperty(k, v) { this[k] = v; } },
      textContent: '', naturalWidth: 280, complete: true,
      setAttribute(k, v) { attrs[k] = v; }, getAttribute(k) { return attrs[k]; },
      appendChild() {}, getBoundingClientRect() { return {left: 0, top: 0, width: 600, height: 800}; },
      classList: { contains: k => names.has(k), add: k => names.add(k),
        remove: k => names.delete(k), toggle(k, on) { if (on) names.add(k); else names.delete(k); } }
    });
  }
  const ids = Object.fromEntries(['stage','figure','head','portrait','modeLive','modePortrait',
    'pauseMotion','portraitLabel','motionChip','modeHint','stageFooter','speech','voice',
    'feedback','look','stars'].map(k => [k, element()]));
  const parts = Object.fromEntries(['.float','.back-hair','.front-hair','.side-hair',
    '.arm-left','.arm-wave','.eye.left','.eye.right','.mouth-open'].map(k => [k, element(k.includes('eye') ? 'eye' : k.slice(1))]));
  const irises = [element('gaze'), element('gaze')];
  ids.figure.querySelector = k => parts[k];
  ids.figure.querySelectorAll = () => irises;
  const moods = ['idle','happy','shy','angry','wave','sleep','curious','walk','surprised'].map(k => {
    const button = element(); button.dataset.action = k; return button;
  });
  const document = events({ hidden: false, getElementById: k => ids[k],
    querySelectorAll: () => moods, createElement: () => element(), createDocumentFragment: () => element() });
  const frames = new Map(), timers = new Map();
  let sequence = 0, now = 1000;
  const spoken = [];
  class Utterance { constructor(text) { this.text = text; } }
  const window = events({ matchMedia: () => ({matches: reduced}),
    requestAnimationFrame: fn => { const id = ++sequence; frames.set(id, fn); return id; },
    cancelAnimationFrame: id => frames.delete(id),
    setTimeout: (fn, delay) => { const id = ++sequence; timers.set(id, {fn, delay}); return id; },
    clearTimeout: id => timers.delete(id) });
  if (voice) {
    window.SpeechSynthesisUtterance = Utterance;
    window.speechSynthesis = { getVoices: () => [{lang:'pt-BR', name:'Maria'}],
      cancel() { spoken.at(-1)?.onerror?.({error:'interrupted'}); }, speak: phrase => spoken.push(phrase) };
  }
  const context = vm.createContext({window, document, performance:{now: () => now}, SpeechSynthesisUtterance:Utterance});
  const root = path.resolve(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'docs/yuna-preview.html'), 'utf8');
  for (const [, code] of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
    if (code.trim()) vm.runInContext(code, context);
  }
  vm.runInContext(fs.readFileSync(path.join(root, 'docs/yuna-viva.js'), 'utf8'), context);
  return {ids, parts, moods, document, window, spoken, frames, timers,
    tick() { now += 16; const jobs = [...frames.values()]; frames.clear(); jobs.forEach(fn => fn(now)); } };
}

test('pausa conserva a pose e persiste ao alternar entre avatar e retrato', () => {
  const app = setup(); app.tick(); app.tick();
  const pose = app.parts['.arm-wave'].style.transform;
  app.ids.pauseMotion.emit('click');
  assert.equal(app.frames.size, 0);
  assert.equal(app.ids.stage.dataset.motionSuspended, 'true');
  app.ids.modePortrait.emit('click'); app.ids.modeLive.emit('click'); app.tick();
  assert.equal(app.parts['.arm-wave'].style.transform, pose);
  assert.equal(app.ids.pauseMotion.getAttribute('aria-pressed'), 'true');
  app.ids.pauseMotion.emit('click');
  assert.equal(app.frames.size, 1);
  assert.equal(app.ids.stage.dataset.motionSuspended, 'false');
});

test('aba oculta suspende a animação e não duplica o ciclo ao voltar', () => {
  const app = setup();
  app.document.hidden = true; app.document.emit('visibilitychange');
  assert.equal(app.frames.size, 0);
  assert.equal(app.ids.stage.dataset.motionSuspended, 'true');
  app.document.hidden = false; app.document.emit('visibilitychange');
  app.window.emit('pageshow'); app.window.emit('pageshow');
  assert.equal(app.frames.size, 1);
});

test('modo retrato expõe só a imagem correta ao leitor de tela', () => {
  const app = setup(); app.ids.modePortrait.emit('click');
  assert.equal(app.ids.figure.getAttribute('aria-hidden'), 'true');
  assert.equal(app.ids.portrait.getAttribute('aria-hidden'), 'false');
  assert.match(app.ids.stageFooter.textContent, /REFERÊNCIA/);
  app.ids.modeLive.emit('click');
  assert.equal(app.ids.figure.getAttribute('aria-hidden'), 'false');
  assert.equal(app.ids.portrait.getAttribute('aria-hidden'), 'true');
});

test('trocar a expressão para a fala e ignora eventos atrasados da fala anterior', () => {
  const app = setup(); app.ids.voice.emit('click');
  const first = app.spoken[0]; first.onstart();
  app.moods[1].emit('click');
  assert.equal(app.ids.stage.classList.contains('is-speaking'), false);
  app.ids.voice.emit('click'); const second = app.spoken[1]; second.onstart();
  first.onend();
  assert.equal(app.ids.stage.classList.contains('is-speaking'), true);
  assert.match(app.ids.voice.textContent, /Parar/);
  app.ids.voice.emit('click');
  assert.equal(app.ids.stage.classList.contains('is-speaking'), false);
  assert.equal(app.timers.size, 0);
});

test('erro ou ausência de início da voz mostra aviso sem trocar a fala escrita', () => {
  const app = setup(); app.moods[2].emit('click');
  const caption = app.ids.speech.textContent;
  app.ids.voice.emit('click'); app.spoken[0].onerror({error:'voice-unavailable'});
  assert.match(app.ids.feedback.textContent, /Não consegui/);
  assert.equal(app.ids.speech.textContent, caption);
  app.ids.voice.emit('click');
  [...app.timers.values()].find(timer => timer.delay === 10000).fn();
  assert.match(app.ids.feedback.textContent, /não iniciou/);
  assert.match(app.ids.voice.textContent, /Ouvir/);
});

test('movimento reduzido e navegador sem voz mantêm os controles visuais', () => {
  const app = setup({reduced:true, voice:false});
  assert.equal(app.frames.size, 0);
  assert.equal(app.ids.pauseMotion.getAttribute('aria-pressed'), 'true');
  assert.equal(app.ids.voice.disabled, true);
  app.moods[8].emit('click');
  assert.equal(app.ids.stage.dataset.mood, 'surprised');
});
