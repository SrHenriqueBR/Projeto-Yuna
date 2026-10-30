/* Yuna Viva: movimentos articulares reais no SVG. Sem rede, webcam ou microfone. */
(function () {
  "use strict";
  const stage = document.getElementById("stage");
  const figure = document.getElementById("figure");
  if (!stage || !figure) return;

  const $ = (selector) => figure.querySelector(selector);
  const head = document.getElementById("head");
  const root = $(".float");
  const hairBack = $(".back-hair");
  const hairFront = $(".front-hair");
  const hairSide = $(".side-hair");
  const armLeft = $(".arm-left");
  const armRight = $(".arm-wave");
  const forearmLeft = $(".forearm-left");
  const forearmRight = $(".forearm-right");
  const handRight = $(".hand-right");
  const legLeft = $(".leg-left"), legRight = $(".leg-right");
  const shinLeft = $(".shin-left"), shinRight = $(".shin-right");
  const eyes = [$(".eye.left"), $(".eye.right")];
  const irises = Array.from(figure.querySelectorAll(".gaze"));
  const mouth = $(".mouth-open");
  const image = document.getElementById("portrait");
  const liveButton = document.getElementById("modeLive");
  const portraitButton = document.getElementById("modePortrait");
  const pauseButton = document.getElementById("pauseMotion");
  const label = document.getElementById("portraitLabel");
  const motionChip = document.getElementById("motionChip");
  const modeHint = document.getElementById("modeHint");
  const zoomButton = document.getElementById("zoomCharacter");

  let isPortrait = false;
  let closeUp = false;
  let paused = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let pointerX = 0, pointerY = 0, lastPointer = 0;
  let eyeX = 0, eyeY = 0, lookX = 0, lookY = 0;
  let lastFrame = 0, seconds = 0, frameId = null;
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, t) => a + (b - a) * t;
  const smoothstep = (x) => { x = clamp(x, 0, 1); return x*x*(3 - 2*x); };
  const num = (x) => x.toFixed(2);
  const motion = (element, value, origin) => {
    if (!element) return;
    element.style.transformBox = (element.classList.contains("eye") || element.classList.contains("mouth-open")) ? "fill-box" : "view-box";
    if (origin) element.style.transformOrigin = origin;
    element.style.transform = value;
  };

  function idleLook(t) {
    const phase = t % 20;
    const stops = [
      [0, 0, 0], [2.1, 0, 0], [3, -1, .2],
      [5, -1, .2], [5.8, .2, -.15], [8, .2, -.15],
      [8.8, 0, 0], [12, 0, 0], [13, .7, .1],
      [16, .7, .1], [17, 0, 0], [20, 0, 0]
    ];
    for (let i = 1; i < stops.length; i++) {
      const first = stops[i - 1], next = stops[i];
      if (phase <= next[0]) {
        const x = smoothstep((phase - first[0]) / (next[0] - first[0]));
        return [lerp(first[1], next[1], x), lerp(first[2], next[2], x)];
      }
    }
    return [0, 0];
  }

  function blink(t) {
    const phase = t % 21.6;
    return [3.12, 7.03, 10.45, 10.75, 15.28, 19.1].reduce(
      (peak, center) => Math.max(peak, clamp(1 - Math.abs(phase-center)/.13, 0, 1)), 0
    );
  }

  function setPortraitMode(requestPortrait) {
    const available = image && image.naturalWidth > 0;
    if (requestPortrait && !available) {
      document.getElementById("feedback").textContent =
        "O retrato original ainda não carregou. O modo articulado funciona sem ele.";
      return;
    }
    isPortrait = !!requestPortrait;
    image.setAttribute("aria-hidden", String(!isPortrait));
    figure.setAttribute("aria-hidden", String(isPortrait));
    stage.classList.toggle("live-mode", !isPortrait);
    stage.classList.toggle("show-portrait", isPortrait);
    liveButton.setAttribute("aria-pressed", String(!isPortrait));
    portraitButton.setAttribute("aria-pressed", String(isPortrait));
    if (zoomButton) zoomButton.disabled = isPortrait;
    label.textContent = isPortrait ?
      "◈ RETRATO ORIGINAL (ESTÁTICO)" : "✧ AVATAR ARTICULADO 2D";
    modeHint.textContent = isPortrait ?
      "Foto de referência com leve efeito visual" :
      "Rosto, braços, mãos e pernas articulados";
    document.getElementById("stageFooter").textContent = isPortrait ?
      "◈ IMAGEM DE REFERÊNCIA" : "✧ ROSTO · MÃOS · PERNAS · CABELO";
    refreshLoop();
  }

  function setPaused(next) {
    paused = !!next;
    stage.dataset.motionPaused = String(paused);
    pauseButton.setAttribute("aria-pressed", String(paused));
    pauseButton.textContent = paused ? "▶ Retomar movimentos" : "Ⅱ Pausar movimentos";
    motionChip.textContent = paused ? "Ⅱ MOVIMENTOS PAUSADOS" : "● MOVIMENTOS ATIVOS";
    refreshLoop();
  }

  function refreshLoop() {
    if (frameId !== null) window.cancelAnimationFrame(frameId);
    frameId = null;
    lastFrame = 0;
    stage.dataset.motionSuspended = String(paused || document.hidden);
    if (!paused && !isPortrait && !document.hidden)
      frameId = window.requestAnimationFrame(frame);
  }
  document.addEventListener("visibilitychange", refreshLoop);
  window.addEventListener("pagehide", () => {
    if (frameId !== null) window.cancelAnimationFrame(frameId);
    frameId = null;
  });
  window.addEventListener("pageshow", refreshLoop);

  liveButton.addEventListener("click", () => setPortraitMode(false));
  portraitButton.addEventListener("click", () => setPortraitMode(true));
  pauseButton.addEventListener("click", () => setPaused(!paused));
  if (zoomButton) zoomButton.addEventListener("click", () => {
    closeUp = !closeUp;
    figure.setAttribute("viewBox", closeUp ? "190 65 220 350" : "0 0 600 1000");
    zoomButton.setAttribute("aria-pressed", String(closeUp));
    zoomButton.textContent = closeUp ? "⌕ Ver corpo inteiro" : "⌕ Ver rosto";
  });
  stage.addEventListener("pointermove", (event) => {
    if (paused) return;
    const rect = stage.getBoundingClientRect();
    pointerX = clamp((event.clientX-rect.left)/rect.width*2-1, -1, 1);
    pointerY = clamp((event.clientY-rect.top)/rect.height*2-1, -1, 1);
    lastPointer = performance.now();
  });
  stage.addEventListener("pointerleave", () => { lastPointer = 0; });
  setPortraitMode(false);
  setPaused(paused);

  function frame(now) {
    frameId = null;
    const dt = lastFrame ? clamp((now - lastFrame) / 1000, 0, .05) : 0;
    lastFrame = now;

    if (!paused && !isPortrait && !document.hidden) {
      seconds += dt;
      const mood = stage.dataset.mood || "idle";
      const sleeping = mood === "sleep";
      const pointerIsActive = lastPointer > 0 && now - lastPointer < 1600;
      const target = pointerIsActive ? [pointerX, pointerY] : idleLook(seconds);
      lookX = lerp(lookX, target[0], clamp(dt * 5, 0, 1));
      lookY = lerp(lookY, target[1], clamp(dt * 5, 0, 1));
      eyeX = lerp(eyeX, lookX * 1.8, clamp(dt * 7, 0, 1));
      eyeY = lerp(eyeY, lookY * 1.4, clamp(dt * 7, 0, 1));

      const t = seconds;
      const breath = Math.sin(t * 1.6 * (sleeping ? .6 : 1));
      const sway = Math.sin(t * .43) * .8 + Math.sin(t * .67 + 1.1) * .2;
      const tilt = sway * .255 +
        (mood === "shy" ? -3 : mood === "happy" ? 1.5 : mood === "wave" ? 2 : 0);
      const nod = lookY * 3 + Math.sin(t * .48) * 1.2;
      motion(root, "translate(" + num(sway * .8) + "px," +
        num(breath * 1.5 - 1) + "px) rotate(" + num(sway * .25) + "deg)", "300px 800px");
      motion(head, "translate(" + num(lookX * 1.1) + "px," +
        num(-nod * .18) + "px) rotate(" + num(tilt) + "deg)", "300px 232px");
      motion(hairBack, "rotate(" + num(Math.sin(t * .9 + 1) * 1.6) + "deg)", "300px 105px");
      motion(hairFront, "rotate(" + num(Math.sin(t * 1.1 + .2) * 1.2) + "deg)", "300px 100px");
      motion(hairSide, "rotate(" + num(Math.sin(t * .82 + 2) * 1.6 - tilt * .18) + "deg)", "300px 155px");
      const right = mood === "wave" ? -55 + Math.sin(t * 2) * 2 :
        mood === "angry" ? -19 : Math.sin(t * .95 + 1.9) * 1.4;
      const left = mood === "shy" ? -22 : mood === "angry" ? 20 :
        Math.sin(t * .92 + .2) * 1.6;
      motion(armRight, "rotate(" + num(right) + "deg)", "362px 278px");
      motion(armLeft, "rotate(" + num(left) + "deg)", "238px 278px");
      motion(forearmRight, "rotate(" + num(mood === "wave" ? -116 + Math.sin(t * 6) * 7 : 0) + "deg)", "390px 384px");
      motion(forearmLeft, "rotate(" + num(mood === "shy" ? -12 : 0) + "deg)", "214px 386px");
      motion(handRight, "rotate(" + num(mood === "wave" ? Math.sin(t * 8) * 9 : 0) + "deg)", "384px 470px");
      motion(legLeft, "rotate(0deg)", "274px 529px");
      motion(legRight, "rotate(0deg)", "327px 529px");
      motion(shinLeft, "rotate(0deg)", "275px 687px");
      motion(shinRight, "rotate(0deg)", "326px 687px");
      const blinkValue = sleeping ? 1 : blink(t);
      const eyeScale = clamp(1 - blinkValue * .96, .04, 1);
      for (const eye of eyes) motion(eye, "scaleY(" + num(eyeScale) + ")");
      for (const iris of irises) motion(iris,
        "translate(" + num(eyeX) + "px," + num(eyeY) + "px)");

      const talking = stage.classList.contains("is-speaking");
      const level = talking ?
        clamp(.5 + Math.sin(t * 17) * .27 + Math.sin(t * 11) * .2, .1, 1) :
        mood === "surprised" ? 1 : .1;
      motion(mouth, "scaleY(" + num(level) + ")");

      if (mood === "walk") {
        motion(root, "translate(" + num(Math.sin(t * 1.5) * 6) + "px," +
          num(-Math.abs(Math.sin(t * 4)) * 2) + "px) rotate(" +
          num(sway * .5) + "deg)", "300px 800px");
        motion(legLeft, "rotate(" + num(Math.sin(t * 4) * 7) + "deg)", "274px 529px");
        motion(legRight, "rotate(" + num(-Math.sin(t * 4) * 7) + "deg)", "327px 529px");
        motion(shinLeft, "rotate(" + num(Math.max(0, Math.sin(t * 4)) * 10) + "deg)", "275px 687px");
        motion(shinRight, "rotate(" + num(Math.max(0, -Math.sin(t * 4)) * 10) + "deg)", "326px 687px");
        motion(armLeft, "rotate(" + num(Math.sin(t * 4) * 7) + "deg)", "238px 278px");
        motion(armRight, "rotate(" + num(Math.sin(t * 4 + Math.PI) * 7) + "deg)", "362px 278px");
      }
    }
    if (!paused && !isPortrait && !document.hidden)
      frameId = window.requestAnimationFrame(frame);
  }
})();
