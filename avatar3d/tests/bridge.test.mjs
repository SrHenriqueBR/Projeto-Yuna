import test from "node:test";
import assert from "node:assert/strict";
import { connectionFromFragment, normalizeRemoteState, reactionPose, normalizeBattery } from "../src/bridge_state.mjs";

const token = "s".repeat(43);
const state = {
  revision: 9, gesture_seq: 4, pose: "wave",
  emotion: "happy", speaking: true, mouth_level: 0.72,
  has_amplitude: true, user_message: "NÃO DEVE SER RECEBIDO"
};

test("reads token only from a validated location fragment", () => {
  assert.deepEqual(
    connectionFromFragment("#bridgePort=43210&bridgeToken=" + token),
    {port:43210, token}
  );
  assert.equal(connectionFromFragment("#bridgePort=999&bridgeToken=" + token), null);
  assert.equal(connectionFromFragment("#bridgePort=43210&bridgeToken=abc"), null);
  assert.equal(connectionFromFragment("#bridgePort=43210&bridgeToken=" +
                                     token + "&bridgeToken=duplicate"), null);
});

test("strips private/unexpected fields and bounds amplitude", () => {
  const result = normalizeRemoteState(state);
  assert.equal(result.mouthLevel, 0.72);
  assert.equal(result.gestureSeq, 4);
  assert.equal(result.user_message, undefined);
  assert.equal(reactionPose(result), "wave");
  assert.equal(normalizeRemoteState({...state, mouth_level: 99}).mouthLevel, 1);
  assert.equal(normalizeRemoteState({...state, gesture_seq: -1}), null);
});

test("maps reactions conservatively", () => {
  assert.equal(reactionPose(normalizeRemoteState({...state, pose:"talk", emotion:"surprised"})), "surprised");
  assert.equal(reactionPose(normalizeRemoteState({...state, pose:"angry", emotion:"neutral"})), "angry");
  assert.equal(reactionPose(normalizeRemoteState({...state, pose:"walk", emotion:"neutral"})), "walk");
  assert.equal(reactionPose(normalizeRemoteState({...state, pose:"sit", emotion:"neutral"})), "sit");
  assert.equal(reactionPose(normalizeRemoteState({...state, pose:"wink", emotion:"neutral"})), "wink");
  assert.equal(reactionPose(normalizeRemoteState({...state, pose:"talk", speaking:true})), "talk");
  assert.equal(normalizeRemoteState(null), null);
});

test("accepts only whitelisted style changes from the Python bridge", () => {
  const next = normalizeRemoteState({
    ...state, appearance_revision: 3,
    appearance: {
      hair: "branco", eyes: "roxos", hair_style: "rabo",
      costume: "casaco", api_key: "never-expose", accessory: "<script>"
    }
  });
  assert.equal(next.appearanceRevision, 3);
  assert.equal(next.appearance.hair, "branco");
  assert.equal(next.appearance.hair_style, "rabo");
  assert.equal(next.appearance.api_key, undefined);
  assert.equal(next.appearance.accessory, undefined);
  assert.deepEqual(normalizeRemoteState({...state, appearance: null}).appearance, {});
});

test("battery state is strict and excludes privileged or identifying fields", () => {
  assert.deepEqual(normalizeBattery({
    percent: 18, plugged: false, mode: "low",
    executable: "run", serial_number: "secret"
  }), {percent: 18, plugged: false, mode: "low"});
  assert.equal(normalizeBattery({percent: -1, plugged: false, mode: "low"}), null);
  assert.equal(normalizeBattery({percent: 12, plugged: 0, mode: "low"}), null);
  assert.equal(normalizeBattery({percent: 12, plugged: false, mode: "unsupported"}), null);
  assert.equal(normalizeRemoteState({...state, battery: undefined}).battery, null);
  assert.equal(normalizeRemoteState({
    ...state, battery: {percent: 100, plugged: true, mode: "full"}
  }).battery.percent, 100);
});
