/** Performer VRM: anima ossos humanoides completos sem depender de clips externos.
 * Usa bones normalizados @pixiv/three-vrm e devolve controles de lookAt ao VRM.
 * Cada instance é isolada; nenhum upload e nenhuma chamada ao cérebro Python.
 */
import * as THREE from "three";
import { clamp, smooth, expressionValues } from "./motion.mjs";

const BONE_NAMES = Object.freeze([
  "hips","spine","chest","upperChest","neck","head",
  "leftShoulder","rightShoulder","leftUpperArm","rightUpperArm",
  "leftLowerArm","rightLowerArm","leftHand","rightHand",
  "leftUpperLeg","rightUpperLeg","leftLowerLeg","rightLowerLeg",
  "leftFoot","rightFoot"
]);
const FACIAL_CHANNELS = new Set(["blink","blinkLeft","blinkRight","aa"]);
const EPS = 1e-6;

export class VrmPerformer {
  constructor(vrm) {
    if (!vrm?.humanoid) throw new TypeError("Um modelo VRM com humanoid é necessário");
    this.vrm = vrm;
    this.bones = new Map();
    this.original = new Map();
    this.poses = new Map();
    this.expressionLevels = new Map();
    this.deltaQ = new THREE.Quaternion();
    this.targetQ = new THREE.Quaternion();
    this.euler = new THREE.Euler(0, 0, 0, "XYZ");
    for (const name of BONE_NAMES) {
      const node = vrm.humanoid.getNormalizedBoneNode(name);
      if (!node) continue;
      this.bones.set(name, node);
      this.original.set(name, {
        quaternion: node.quaternion.clone(),
        position: node.position.clone()
      });
    }
    this.appliedFrames = 0;
  }

  bone(name, x, y, z, delta) {
    const node = this.bones.get(name);
    if (!node) return;
    const rest = this.original.get(name);
    this.euler.set(x, y, z);
    this.deltaQ.setFromEuler(this.euler);
    this.targetQ.copy(rest.quaternion).multiply(this.deltaQ);
    node.quaternion.slerp(this.targetQ, 1 - Math.exp(-delta * 9));
  }

  /** frame contém apenas os sinais já filtrados pela MotionDirector. */
  update(frame, delta) {
    const dt = clamp(delta, 0, 0.08);
    if (!dt || !frame) return;
    const pose = frame.emotion;
    const walk = pose === "walk";
    const wave = pose === "wave";
    const shy = pose === "shy";
    const angry = pose === "angry";
    const sitting = pose === "sit" || pose === "sleepy";
    const breath = frame.breath || 0;
    const sway = frame.bodySway || 0;
    const twist = frame.spineTwist || 0;
    const headYaw = frame.headYaw || 0;
    const headPitch = frame.headPitch || 0;
    const headTilt = frame.headTilt || 0;
    const armL = frame.leftArmSwing || 0;
    const armR = frame.rightArmSwing || 0;
    const legL = frame.leftLeg || 0;
    const legR = frame.rightLeg || 0;

    // A pose padrão baixa os braços ao lado do corpo. Uma T-pose rígida
    // é inadequada para um personagem que fica conversando na tela.
    this.bone("hips", 0, twist * 0.20, sway * 0.25, dt);
    this.bone("spine", breath * 0.45, twist * 0.72, sway * 0.28, dt);
    this.bone("chest", breath * 0.7, -twist * 0.30, -sway * 0.35, dt);
    this.bone("upperChest", breath * 0.35, twist * 0.20, -sway * 0.15, dt);
    this.bone("neck", headPitch * 0.20, headYaw * 0.30, headTilt * 0.20, dt);
    this.bone("head", headPitch * 0.80, headYaw * 0.70, headTilt * 0.80, dt);
    this.bone("leftShoulder", 0, 0, 0.09 - armL * 0.12, dt);
    this.bone("rightShoulder", 0, 0, -0.09 + armR * 0.12, dt);

    // Movimento em três articulações: ombro, cotovelo e punho.
    // A acenação levanta somente o braço direito.
    const liftR = wave ? 1.42 : 0;
    this.bone("rightUpperArm",
      shy ? -0.30 : angry ? 0.16 : -armR * 0.24,
      wave ? -0.12 : 0,
      -0.96 + liftR - armR * 0.55, dt);
    this.bone("leftUpperArm",
      shy ? -0.30 : angry ? -0.16 : -armL * 0.24,
      0, 0.96 + armL * 0.55, dt);
    this.bone("rightLowerArm", -0.12,
      wave ? -0.22 : 0, -clamp(frame.rightElbow || 0, 0, 1.3), dt);
    this.bone("leftLowerArm", -0.12,
      0, clamp(frame.leftElbow || 0, 0, 1.3), dt);
    this.bone("rightHand", 0, 0, frame.rightWrist || 0, dt);
    this.bone("leftHand", 0, 0, frame.leftWrist || 0, dt);

    // A caminhada é em lugar: move membros alternados sem tirar o avatar
    // da cena. Não é navegação pelo mundo nem IK de pés.
    this.bone("leftUpperLeg", legL, 0, sitting ? -0.10 : 0, dt);
    this.bone("rightUpperLeg", legR, 0, sitting ? 0.10 : 0, dt);
    this.bone("leftLowerLeg", -clamp(frame.leftKnee || 0, 0, 1.2), 0, 0, dt);
    this.bone("rightLowerLeg", -clamp(frame.rightKnee || 0, 0, 1.2), 0, 0, dt);
    this.bone("leftFoot", -legL * 0.25, 0, 0, dt);
    this.bone("rightFoot", -legR * 0.25, 0, 0, dt);
    const hips = this.bones.get("hips");
    if (hips) {
      const rest = this.original.get("hips");
      hips.position.y = smooth(hips.position.y,
        rest.position.y + (frame.hipDrop || 0) +
        (frame.bodyBob || 0) + breath * .25, 5.2, dt);
      hips.position.x = smooth(hips.position.x,
        rest.position.x + (frame.hipShift || 0), 5.2, dt);
    }

    // Somente expressões realmente existentes no VRM são aplicadas.
    const manager = this.vrm.expressionManager;
    if (manager) {
      const hasSeparateBlink = !!(manager.getExpression("blinkLeft") &&
        manager.getExpression("blinkRight"));
      for (const [name, value] of Object.entries(expressionValues(frame))) {
        if (name === "blink" && hasSeparateBlink) continue;
        if ((name === "blinkLeft" || name === "blinkRight") && !hasSeparateBlink) continue;
        if (!manager.getExpression(name)) continue;
        const previous = this.expressionLevels.get(name) ?? 0;
        // Piscar e fala devem ser rápidos, reações emocionais suaves.
        const next = FACIAL_CHANNELS.has(name) ?
          clamp(value, 0, 1) : smooth(previous, clamp(value, 0, 1), 7, dt);
        if (Math.abs(next - previous) >= EPS || this.appliedFrames === 0) {
          manager.setValue(name, next);
        }
        this.expressionLevels.set(name, next);
      }
    }
    this.vrm.update(dt);
    this.appliedFrames++;
  }
}
