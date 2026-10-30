/** Sinais de animação calculados localmente, sem depender de Three.js ou DOM. */
export const EMOTIONS = Object.freeze(["idle", "happy", "curious", "surprised", "shy", "wave", "sit", "sleepy"]);

export function clamp(value, minimum, maximum) {
  if (!Number.isFinite(value)) return minimum;
  return Math.min(maximum, Math.max(minimum, value));
}

export function smooth(current, target, speed, dt) {
  const t = 1 - Math.exp(-clamp(speed, 0, 60) * clamp(dt, 0, 0.25));
  return current + (target - current) * t;
}

function ease(value) {
  const t = clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

/** Piscar variado e ocasionalmente duplo, mas determinístico e sem timers. */
export function blinkAt(seconds, reducedMotion = false) {
  if (reducedMotion) return 0;
  const phase = ((Number(seconds) || 0) % 24 + 24) % 24;
  const centers = [4.66, 9.53, 13.62, 13.94, 19.25];
  let blink = 0;
  for (const center of centers) {
    blink = Math.max(blink, clamp(1 - Math.abs(phase - center) / 0.14, 0, 1));
  }
  return blink;
}

/** A personagem observa o ambiente mesmo com o cursor parado, sem movimentos bruscos. */
export function ambientGazeAt(seconds) {
  const time = Math.max(0, Number.isFinite(seconds) ? seconds : 0);
  const phase = time % 20;
  const stops = [
    [0, 0, 0], [2.2, 0, 0], [3.1, -0.35, 0.10],
    [5.2, -0.35, 0.10], [6.0, 0.16, -0.12],
    [9.1, 0.16, -0.12], [10.3, 0, 0],
    [13.2, 0, 0], [14.1, 0.34, 0.08],
    [16.9, 0.34, 0.08], [18.2, 0, 0], [20, 0, 0]
  ];
  for (let i = 1; i < stops.length; i++) {
    const before = stops[i - 1];
    const after = stops[i];
    if (phase <= after[0]) {
      const progress = ease((phase - before[0]) / (after[0] - before[0]));
      return {
        x: before[1] + (after[1] - before[1]) * progress,
        y: before[2] + (after[2] - before[2]) * progress
      };
    }
  }
  return {x: 0, y: 0};
}

export function frameAt(seconds, {
  pose = "idle", pointerX = 0, pointerY = 0, mouthLevel = 0,
  reducedMotion = false
} = {}) {
  const time = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const activePose = EMOTIONS.includes(pose) ? pose : "idle";
  const movement = reducedMotion ? 0 : 1;
  const x = clamp(pointerX, -1, 1);
  const y = clamp(pointerY, -1, 1);
  const weight = clamp(1 - Math.max(Math.abs(x), Math.abs(y)), 0, 1);
  const glance = ambientGazeAt(time);
  const gazeX = movement ? clamp(x + glance.x * weight, -1, 1) : 0;
  const gazeY = movement ? clamp(y + glance.y * weight, -1, 1) : 0;
  const resting = activePose === "sit" || activePose === "sleepy";
  const sleepy = activePose === "sleepy";
  const pace = sleepy ? 0.58 : resting ? 0.8 : 1;
  const idleBreath = Math.sin(time * 1.65 * pace);
  const smallShift = Math.sin(time * 0.44) * 0.65 + Math.sin(time * 0.73 + 1.1) * 0.35;

  return {
    blink: sleepy ? 1 : blinkAt(time, reducedMotion),
    gazeX, gazeY,
    headYaw: movement ? gazeX * 0.16 : 0,
    headPitch: movement ? -gazeY * 0.10 + weight * Math.sin(time * 0.42) * 0.018 : 0,
    headTilt: movement ? smallShift * 0.035 + (activePose === "curious" ? -0.09 : 0) : 0,
    bodySway: movement && !sleepy ? smallShift * (resting ? 0.013 : 0.035) : 0,
    bodyBob: movement && !resting ? Math.sin(time * 1.35) * 0.009 : 0,
    breath: movement ? idleBreath * (sleepy ? 0.016 : 0.024) : 0,
    leftArmSwing: movement ? Math.sin(time * 0.95 + 0.5) * 0.07 : 0,
    rightArmSwing: movement ? Math.sin(time * 0.89 + 2.2) * 0.07 : 0,
    hairSwing: movement ? Math.sin(time * 0.79 + 0.2) * 0.025 : 0,
    wave: activePose === "wave" && movement ? Math.sin(time * 8) * 0.22 : 0,
    mouth: clamp(mouthLevel, 0, 1),
    emotion: activePose
  };
}

export function expressionValues(frame) {
  return {
    blink: frame.blink,
    aa: frame.mouth,
    happy: frame.emotion === "happy" ? 0.85 : 0,
    relaxed: frame.emotion === "shy" ? 0.6 : 0,
    surprised: frame.emotion === "surprised" ? 0.9 : 0
  };
}
