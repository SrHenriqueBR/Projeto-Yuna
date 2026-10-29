/** Deterministic animation signals, independent from Three.js and DOM. */
export const EMOTIONS = Object.freeze(["idle", "happy", "curious", "surprised", "shy", "wave", "sit", "sleepy"]);

export function clamp(value, minimum, maximum) {
  if (!Number.isFinite(value)) return minimum;
  return Math.min(maximum, Math.max(minimum, value));
}

export function smooth(current, target, speed, dt) {
  const t = 1 - Math.exp(-clamp(speed, 0, 60) * clamp(dt, 0, 0.25));
  return current + (target - current) * t;
}

/** A quick, symmetric blink every 4.8 seconds. */
export function blinkAt(seconds, reducedMotion = false) {
  if (reducedMotion) return 0;
  const phase = ((Number(seconds) || 0) % 4.8 + 4.8) % 4.8;
  if (phase < 4.52) return 0;
  return clamp(1 - Math.abs(phase - 4.66) / 0.14, 0, 1);
}

export function frameAt(seconds, {
  pose = "idle", pointerX = 0, pointerY = 0, mouthLevel = 0,
  reducedMotion = false
} = {}) {
  const time = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const activePose = EMOTIONS.includes(pose) ? pose : "idle";
  const movement = reducedMotion ? 0 : 1;
  return {
    blink: activePose === "sleepy" ? 1 : blinkAt(time, reducedMotion),
    headYaw: movement ? clamp(pointerX, -1, 1) * 0.16 : 0,
    headPitch: movement ? -clamp(pointerY, -1, 1) * 0.10 : 0,
    bodySway: movement && activePose !== "sleepy" ? Math.sin(time * 0.9) * 0.018 : 0,
    breath: movement ? Math.sin(time * (activePose === "sleepy" ? 0.8 : 1.65)) * 0.012 : 0,
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
