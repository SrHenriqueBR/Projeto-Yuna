/** Direcao de cena 3D da Yuna: canais de corpo inteiro e transicoes suaves.
 * Calculadora pura; sem DOM, rede, microfone nem acesso a dados da assistente.
 */
import { frameAt, smooth, clamp } from "./motion.mjs";

const CHANNELS = Object.freeze([
  "headYaw","headPitch","headTilt","neckYaw","spineTwist",
  "bodySway","bodyBob","breath","hipShift","hipDrop",
  "leftArmSwing","rightArmSwing","leftElbow","rightElbow",
  "leftWrist","rightWrist","leftLeg","rightLeg",
  "leftKnee","rightKnee","hairSwing","wave","smile"
]);

/** Adiciona camada de interpretacao fisica ao movimento-base, sem assets. */
export function performanceFrame(seconds, {
  pose = "idle", pointerX = 0, pointerY = 0, mouthLevel = 0,
  talking = false, reducedMotion = false, intensity = 1
} = {}) {
  const base = frameAt(seconds, {pose, pointerX, pointerY, mouthLevel, reducedMotion});
  const time = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const strength = reducedMotion ? 0 : clamp(intensity, 0, 1);
  const active = base.emotion;
  const resting = active === "sit" || active === "sleepy";
  const stride = active === "walk" ? Math.sin(time * 5.1) * strength : 0;
  const wave = active === "wave" ? Math.sin(time * 8.2) * 0.22 * strength : 0;
  const w = strength * (Math.sin(time * 0.44) * 0.65 +
    Math.sin(time * 0.73 + 1.1) * 0.35);
  const elbow = 0.13 * strength;
  return {
    ...base,
    motionStrength: strength,
    gazeX: base.gazeX * strength,
    gazeY: base.gazeY * strength,
    headYaw: base.headYaw * strength,
    headPitch: base.headPitch * strength,
    headTilt: base.headTilt * strength,
    bodySway: base.bodySway * strength,
    breath: base.breath * strength,
    leftArmSwing: base.leftArmSwing * strength,
    rightArmSwing: base.rightArmSwing * strength,
    blinkLeft: base.blink,
    blinkRight: active === "wink" && strength ? 1 : base.blink,
    headPitch: base.headPitch * strength +
      (talking ? Math.sin(time * 2.3) * 0.027 * strength : 0),
    headTilt: base.headTilt * strength + (active === "shy" ? -0.055 * strength :
      active === "wave" ? 0.055 * strength : 0),
    neckYaw: base.headYaw * 0.34,
    spineTwist: w * 0.024 + (active === "curious" ? -0.034 * strength : 0),
    bodyBob: active === "walk" && strength ?
      Math.abs(stride) * 0.035 : base.bodyBob * strength,
    hipShift: active === "walk" ? stride * 0.03 : w * 0.010,
    hipDrop: resting ? -0.095 * strength : 0,
    leftArmSwing: active === "walk" ? -stride * 0.38 : base.leftArmSwing,
    rightArmSwing: active === "walk" ? stride * 0.38 : base.rightArmSwing,
    leftElbow: active === "shy" ? 0.55 * strength :
      active === "angry" ? 0.68 * strength : elbow,
    rightElbow: active === "wave" ? 1.02 * strength :
      active === "shy" ? 0.55 * strength :
      active === "angry" ? 0.68 * strength : elbow,
    leftWrist: Math.sin(time * 0.82) * 0.06 * strength,
    rightWrist: active === "wave" ? Math.sin(time * 8.5) * 0.34 * strength :
      Math.sin(time * 0.74 + 1) * 0.05 * strength,
    leftLeg: resting ? 0 : stride * 0.45,
    rightLeg: resting ? 0 : -stride * 0.45,
    leftKnee: resting ? 0.70 * strength : Math.max(0, -stride) * 0.64,
    rightKnee: resting ? 0.70 * strength : Math.max(0, stride) * 0.64,
    hairSwing: base.hairSwing * strength + stride * 0.026,
    wave: wave,
    smile: active === "happy" || active === "laugh" ? 0.85 :
      active === "shy" ? 0.26 : talking ? 0.1 : 0,
    // O pulso da boca vem exclusivamente da fonte de audio/demonstracao.
    mouth: clamp(mouthLevel, 0, 1)
  };
}

/** Interpola movimentos secundarios, para evitar teletransporte de membros.
 * Blink e mouth nao sao suavizados aqui (latencia perceptivel na fala).
 */
export class PerformanceDirector {
  constructor() { this.previous = null; }
  reset() { this.previous = null; }
  step(seconds, options = {}, delta = 1 / 30) {
    const target = performanceFrame(seconds, options);
    if (options.reducedMotion || !this.previous) {
      this.previous = target;
      return target;
    }
    const frame = {...target};
    for (const key of CHANNELS) {
      frame[key] = smooth(this.previous[key] ?? 0, target[key],
        key === "smile" ? 7.5 : 6.5, delta);
    }
    this.previous = frame;
    return frame;
  }
}
