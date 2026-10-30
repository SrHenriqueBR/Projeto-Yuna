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

  let isPortrait = false;
  let paused = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let pointerX = 0, pointerY = 0, lastPointer = 0;
  let eyeX = 0, eyeY = 0, lookX = 0, lookY = 0;
  let lastFrame = 0, seconds = 0, lastWidth = 0;
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
      document.getElementById("speech").textContent =
        "O retrato original ainda não carregou. O modo articulado funciona sem ele.";
      return;
    }
    isPortrait = !!requestPortrait;
    stage.classList.toggle("live-mode", !isPortrait);
    stage.classList.toggle("show-portrait", isPortrait);
    liveButton.setAttribute("aria-pressed", String(!isPortrait));
    portraitButton.setAttribute("aria-pressed", String(isPortrait));
    label.textContent = isPortrait ?
      "◈ RETRATO ORIGINAL (ESTÁTICO)" : "✧ AVATAR ARTICULADO 2D";
    modeHint.textContent = isPortrait ?
      "Foto de referência com leve efeito visual" :
      "Olhos, boca, braços, cabeça e cabelo em movimento independente";
  }

  function setPaused(next) {
    paused = !!next;
    pauseButton.setAttribute("aria-pressed", String(paused));
    pauseButton.textContent = paused ? "▶ Retomar movimentos" : "Ⅱ Pausar movimentos";
    motionChip.textContent = paused ? "Ⅱ MOVIMENTOS PAUSADOS" : "● MOVIMENTOS ATIVOS";
  }

  liveButton.addEventListener("click", () => setPortraitMode(false));
  portraitButton.addEventListener("click", () => setPortraitMode(true));
  pauseButton.addEventListener("click", () => setPaused(!paused));
  stage.addEventListener("pointermove", (event) => {
    const rect = stage.getBoundingClientRect();
    pointerX = clamp((event.clientX-rect.left)/rect.width*2-1, -1, 1);
    pointerY = clamp((event.clientY-rect.top)/rect.height*2-1, -1, 1);
    lastPointer = performance.now();
  });
  stage.addEventListener("pointerleave", () => { lastPointer = 0; });
  setPortraitMode(false);
  setPaused(paused);

  function frame(now) {
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
      eyeX = lerp(eyeX, lookX * 7, clamp(dt * 7, 0, 1));
      eyeY = lerp(eyeY, lookY * 5, clamp(dt * 7, 0, 1));

      const t = seconds;
      const breath = Math.sin(t * 1.6 * (sleeping ? .6 : 1));
      const sway = Math.sin(t * .43) * .8 + Math.sin(t * .67 + 1.1) * .2;
      const tilt = sway * 1.25 +
        (mood === "shy" ? -6 : mood === "happy" ? 3 : mood === "wave" ? 4 : 0);
      const nod = lookY * 3 + Math.sin(t * .48) * 1.2;
      motion(root, "translate(" + num(sway * 2.3) + "px," +
        num(breath * 3.4 - 4) + "px) rotate(" + num(sway * .6) + "deg)", "300px 700px");
      motion(head, "translate(" + num(lookX * 4) + "px," +
        num(-nod * .35) + "px) rotate(" + num(tilt) + "deg)", "300px 460px");
      motion(hairBack, "rotate(" + num(Math.sin(t * .9 + 1) * 1.6) + "deg)", "300px 160px");
      motion(hairFront, "rotate(" + num(Math.sin(t * 1.1 + .2) * 1.2) + "deg)", "300px 140px");
      motion(hairSide, "rotate(" + num(Math.sin(t * .82 + 2) * 1.6 - tilt * .18) + "deg)", "300px 200px");
      const right = mood === "wave" ? -116 + Math.sin(t * 8) * 14 :
        mood === "angry" ? -19 : Math.sin(t * .95 + 1.9) * 3.2;
      const left = mood === "shy" ? -22 : mood === "angry" ? 20 :
        Math.sin(t * .92 + .2) * 3.5;
      motion(armRight, "rotate(" + num(right) + "deg)", "408px 540px");
      motion(armLeft, "rotate(" + num(left) + "deg)", "194px 542px");
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
        motion(root, "translate(" + num(Math.sin(t * 3.5) * 10) + "px," +
          num(-Math.abs(Math.sin(t * 6)) * 8) + "px) rotate(" +
          num(sway * .5) + "deg)", "300px 700px");
        motion(armLeft, "rotate(" + num(Math.sin(t * 6) * 19) + "deg)", "194px 542px");
        motion(armRight, "rotate(" + num(Math.sin(t * 6 + Math.PI) * 19) + "deg)", "408px 540px");
      }
    } else if (paused && !isPortrait) {
      motion(root,"translate(0px,0px)");
      motion(head,"rotate(0deg)","300px 460px");
      for (const eye of eyes) motion(eye,"scaleY(1)");
      for (const iris of irises) motion(iris,"translate(0px,0px)");
      for (const node of [armLeft,armRight,hairBack,hairFront,hairSide])
        motion(node,"rotate(0deg)");
      motion(mouth,"scaleY(.1)");
    }
    window.requestAnimationFrame(frame);
  }
  window.requestAnimationFrame(frame);
})();