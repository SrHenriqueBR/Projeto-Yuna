/** Prévia pública WebGL original: sem VRM, Vite, Ollama ou dados do usuário.
 * A biblioteca Three.js é carregada do CDN explicitado no importmap HTML.
 */
import * as THREE from "three";
import { createAnimePreview } from "../avatar3d/src/preview_character.js";
import { appearanceForPreset } from "../avatar3d/src/appearance.mjs";
import { PerformanceDirector } from "../avatar3d/src/performance.mjs";
import { smooth, clamp } from "../avatar3d/src/motion.mjs";

const stage = document.querySelector("#stage");
const message = document.querySelector("#message");
const hairStyle = document.querySelector("#hairStyle");
const eyeColor = document.querySelector("#eyeColor");
const intensity = document.querySelector("#intensity");
const buttons = [...document.querySelectorAll("[data-pose]")];
const pauseButton = document.querySelector("#pause");

let renderer;
try {
  renderer = new THREE.WebGLRenderer({
    antialias: true, alpha: true, powerPreference: "default"
  });
} catch {
  message.textContent = "Seu navegador não conseguiu ativar WebGL. Tente Chrome ou Edge com aceleração de hardware habilitada.";
}
if (renderer) {
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.6));
  stage.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xf3e6ff, 0x392947, 2.4));
  const key = new THREE.DirectionalLight(0xfff9ff, 2.8);
  key.position.set(2.4, 4.1, 3.4);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x956aff, 1.8);
  rim.position.set(-2.7, 2.8, -2.3);
  scene.add(rim);

  const camera = new THREE.PerspectiveCamera(31, 1, 0.1, 25);
  camera.position.set(0, 1.16, 3.35);
  camera.lookAt(0, 0.97, 0);
  let style = appearanceForPreset("yuna");
  let preview = createAnimePreview(style);
  scene.add(preview.root);

  const director = new PerformanceDirector();
  const shouldReduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let paused = shouldReduce;
  let pose = "idle";
  let poseUntil = 0, elapsed = 0, previous = 0;
  let pointerX = 0, pointerY = 0, gazeX = 0, gazeY = 0;
  let drag = false, dragX = 0, modelYaw = 0;
  let speaking = false;
  let speakingTimeout = 0;

  function setPose(next) {
    if (!buttons.some(button => button.dataset.pose === next)) return;
    pose = next;
    poseUntil = next === "idle" ? 0 : performance.now() +
      (next === "sit" ? 9000 : next === "walk" ? 6000 : 4400);
    for (const button of buttons) {
      const pressed = button.dataset.pose === next;
      button.setAttribute("aria-pressed", String(pressed));
    }
    const names = {
      idle: "Yuna está observando o ambiente e respirando.",
      happy: "Ela sorri e movimenta a postura suavemente.",
      wave: "Ela ergue e movimenta o braço para acenar.",
      walk: "Movimentos alternados de pernas e braços, simulando uma caminhada no lugar.",
      curious: "A Yuna inclina a cabeça e olha ao redor.",
      shy: "Ela recolhe os braços e inclina o rosto.",
      angry: "Ela muda a postura e os braços, simulando irritação.",
      wink: "Uma piscadinha expressiva.",
      sit: "Modo de repouso, com pernas dobradas."
    };
    message.textContent = names[next];
  }
  buttons.forEach(button =>
    button.addEventListener("click", () => setPose(button.dataset.pose)));
  setPose("idle");

  function refreshStyle() {
    const replacement = createAnimePreview({
      ...style, hair_style: hairStyle.value, eyes: eyeColor.value
    });
    const previousPreview = preview;
    preview = replacement;
    preview.root.rotation.y = modelYaw;
    scene.add(preview.root);
    previousPreview.dispose();
    director.reset();
    style = replacement.appearance;
  }
  hairStyle.addEventListener("change", refreshStyle);
  eyeColor.addEventListener("change", refreshStyle);

  function togglePaused(next) {
    paused = !!next;
    pauseButton.setAttribute("aria-pressed", String(paused));
    pauseButton.textContent = paused ? "▶ Retomar animação" : "Ⅱ Pausar animação";
    if (paused) message.textContent = "Animação pausada. Você ainda pode girar a câmera.";
    else setPose(pose);
  }
  pauseButton.addEventListener("click", () => togglePaused(!paused));
  togglePaused(paused);

  document.querySelector("#cameraReset").addEventListener("click", () => {
    modelYaw = 0;
    camera.position.set(0, 1.16, 3.35);
    camera.lookAt(0, 0.97, 0);
    preview.root.rotation.y = 0;
  });

  renderer.domElement.addEventListener("pointerdown", event => {
    if (event.button !== 0) return;
    drag = true;
    dragX = event.clientX;
    renderer.domElement.setPointerCapture(event.pointerId);
  });
  renderer.domElement.addEventListener("pointermove", event => {
    const bounds = renderer.domElement.getBoundingClientRect();
    if (bounds.width && bounds.height) {
      pointerX = clamp((event.clientX - bounds.left) / bounds.width * 2 - 1, -1, 1);
      pointerY = clamp((event.clientY - bounds.top) / bounds.height * 2 - 1, -1, 1);
    }
    if (drag) {
      modelYaw = clamp(modelYaw + (event.clientX - dragX) * 0.006, -2.5, 2.5);
      dragX = event.clientX;
    }
  });
  renderer.domElement.addEventListener("pointerup", () => { drag = false; });
  renderer.domElement.addEventListener("pointercancel", () => { drag = false; });
  renderer.domElement.addEventListener("pointerleave", () => {
    if (!drag) { pointerX = 0; pointerY = 0; }
  });
  renderer.domElement.addEventListener("wheel", event => {
    event.preventDefault();
    camera.position.z = clamp(camera.position.z + event.deltaY * .0045, 2.0, 5.2);
  }, {passive: false});

  document.querySelector("#speak").addEventListener("click", () => {
    if (!("speechSynthesis" in window)) {
      message.textContent = "Seu navegador não possui fala sintetizada disponível.";
      return;
    }
    speechSynthesis.cancel();
    speaking = false;
    clearTimeout(speakingTimeout);
    const utterance = new SpeechSynthesisUtterance(
      "Oi, Kaizen! Agora eu tenho corpo em três dimensões. Olha só como consigo me movimentar!"
    );
    utterance.lang = "pt-BR";
    utterance.rate = 1.03;
    utterance.pitch = 1.15;
    const voices = speechSynthesis.getVoices();
    const voice = voices.find(v=>/^pt-BR/i.test(v.lang) &&
      /female|maria|francisca|camila|luciana/i.test(v.name))
      || voices.find(v=>/^pt-BR/i.test(v.lang));
    if (voice) utterance.voice = voice;
    utterance.onstart = () => {
      speaking = true;
      message.textContent = "Voz demonstrativa ativa: a boca acompanha o ritmo aproximado da fala.";
      speakingTimeout = setTimeout(()=>{ speaking = false; }, 15000);
    };
    utterance.onend = () => { speaking = false; clearTimeout(speakingTimeout); };
    utterance.onerror = () => { speaking = false; clearTimeout(speakingTimeout); };
    speechSynthesis.speak(utterance);
  });

  function resize() {
    const width = Math.max(1, stage.clientWidth);
    const height = Math.max(1, stage.clientHeight);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
  }
  new ResizeObserver(resize).observe(stage);
  resize();

  function animate(now) {
    requestAnimationFrame(animate);
    if (document.hidden) { previous = now; return; }
    const dt = previous ? clamp((now - previous)/1000, 0, 0.08) : 0;
    previous = now;
    if (!paused) {
      elapsed += dt;
      if (poseUntil && now > poseUntil) setPose("idle");
      gazeX = smooth(gazeX, pointerX, 5.5, dt);
      gazeY = smooth(gazeY, pointerY, 5.5, dt);
      const mouth = speaking ?
        clamp(.16 + .28 * (Math.sin(elapsed * 15) + 1) * .5, 0, 1) : 0;
      const frame = director.step(elapsed, {
        pose, pointerX:gazeX, pointerY:gazeY,
        mouthLevel:mouth, talking:speaking,
        intensity:Number(intensity.value)/100
      }, dt);
      preview.animate(frame, frame.gazeX, frame.gazeY, dt);
      preview.root.rotation.y = modelYaw;
    }
    renderer.render(scene, camera);
  }
  requestAnimationFrame(animate);
  addEventListener("pagehide", () => {
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    clearTimeout(speakingTimeout);
    preview.dispose();
    renderer.dispose();
  }, {once:true});
}
