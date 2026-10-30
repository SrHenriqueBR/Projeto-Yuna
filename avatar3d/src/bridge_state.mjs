/** Consumo somente-leitura do AvatarController, sem ações ou dados privados. */
import { OPTIONS } from "./appearance.mjs";

export function connectionFromFragment(fragment) {
  if (typeof fragment !== "string" || !fragment.startsWith("#")) return null;
  const params = new URLSearchParams(fragment.slice(1));
  if (params.getAll("bridgePort").length !== 1 ||
      params.getAll("bridgeToken").length !== 1) return null;
  const rawPort = params.get("bridgePort") || "";
  const token = params.get("bridgeToken") || "";
  if (!/^[0-9]{4,5}$/.test(rawPort) || !/^[A-Za-z0-9_-]{32,128}$/.test(token)) {
    return null;
  }
  const port = Number(rawPort);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) return null;
  return { port, token };
}

const ALLOWED_POSES = new Set([
  "idle", "happy", "curious", "surprised", "shy", "wave",
  "talk", "wink", "laugh", "sit", "walk", "sleepy", "angry", "pose"
]);
const ALLOWED_EMOTIONS = new Set([
  "neutral", "happy", "shy", "sad", "surprised", "annoyed"
]);

const BATTERY_MODES = new Set([
  "critical", "low", "tired", "normal", "charging", "full"
]);

export function normalizeBattery(raw) {
  if (!raw || typeof raw !== "object" ||
      !Number.isInteger(raw.percent) || raw.percent < 0 ||
      raw.percent > 100 || typeof raw.plugged !== "boolean" ||
      !BATTERY_MODES.has(raw.mode)) return null;
  return {
    percent: raw.percent, plugged: raw.plugged, mode: raw.mode
  };
}

export function normalizeRemoteState(raw) {
  if (!raw || typeof raw !== "object" ||
      !Number.isSafeInteger(raw.revision) || raw.revision < 0 ||
      !Number.isSafeInteger(raw.gesture_seq) || raw.gesture_seq < 0) {
    return null;
  }
  return {
    revision: raw.revision,
    gestureSeq: raw.gesture_seq,
    pose: ALLOWED_POSES.has(raw.pose) ? raw.pose : "idle",
    emotion: ALLOWED_EMOTIONS.has(raw.emotion) ? raw.emotion : "neutral",
    speaking: raw.speaking === true,
    mouthLevel: Number.isFinite(raw.mouth_level)
      ? Math.max(0, Math.min(1, raw.mouth_level)) : 0,
    hasAmplitude: raw.has_amplitude === true,
    battery: normalizeBattery(raw.battery),
    appearanceRevision: Number.isSafeInteger(raw.appearance_revision) &&
      raw.appearance_revision >= 0 ? raw.appearance_revision : 0,
    appearance: raw.appearance && typeof raw.appearance === "object" &&
      !Array.isArray(raw.appearance)
      ? Object.fromEntries(Object.entries(raw.appearance).filter(([key, value]) =>
          Object.hasOwn(OPTIONS, key) && typeof value === "string" &&
          OPTIONS[key].includes(value)))
      : {}
  };
}

export function reactionPose(state) {
  if (!state) return "idle";
  if (["happy", "curious", "surprised", "shy", "wave", "walk", "sit",
       "sleepy", "angry", "laugh", "wink", "pose"].includes(state.pose)) {
    return state.pose;
  }
  if (state.pose === "talk" && state.speaking) return "talk";
  if (state.emotion === "happy") return "happy";
  if (state.emotion === "surprised") return "surprised";
  if (state.emotion === "shy") return "shy";
  return "idle";
}
