import test from "node:test";
import assert from "node:assert/strict";
import { EMOTIONS, clamp, smooth, blinkAt, ambientGazeAt, frameAt, expressionValues } from "../src/motion.mjs";

test("animation signals are bounded", () => {
  const f = frameAt(12, { pointerX: 999, pointerY: -999, mouthLevel: 44 });
  assert.equal(f.headYaw, 0.16);
  assert.equal(f.headPitch, 0.1);
  assert.equal(f.mouth, 1);
  assert.ok(EMOTIONS.includes(f.emotion));
  assert.equal(clamp(Number.NaN, 0, 1), 0);
});

test("blink closes briefly and reopens", () => {
  assert.equal(blinkAt(1), 0);
  assert.ok(blinkAt(4.66) > 0.98);
  assert.ok(blinkAt(4.79) > 0);
  assert.ok(blinkAt(4.79) < 0.1);
  assert.equal(blinkAt(0, true), 0);
});

test("reduced motion disables body and head motion but not speech state", () => {
  const f = frameAt(4.66, {
    pose: "wave", pointerX: 1, pointerY: 1,
    mouthLevel: 0.6, reducedMotion: true
  });
  assert.equal(f.headYaw, 0);
  assert.equal(f.bodySway, 0);
  assert.equal(f.breath, 0);
  assert.equal(f.wave, 0);
  assert.equal(f.blink, 0);
  assert.equal(f.mouth, 0.6);
});

test("happy and surprised never appear at same time", () => {
  const happy = expressionValues(frameAt(1, { pose: "happy" }));
  const surprise = expressionValues(frameAt(1, { pose: "surprised" }));
  assert.ok(happy.happy > 0);
  assert.equal(happy.surprised, 0);
  assert.ok(surprise.surprised > 0);
  assert.equal(surprise.happy, 0);
});

test("smoothing is gradual; unknown pose falls back safely", () => {
  assert.ok(smooth(0, 1, 6, 0.016) > 0);
  assert.ok(smooth(0, 1, 6, 0.016) < 1);
  assert.equal(frameAt(0, { pose: "unsupported" }).emotion, "idle");
  assert.equal(frameAt(NaN).mouth, 0);
});

test("idle shifts its gaze without cursor input and remains bounded", () => {
  const left = frameAt(4, {pose: "idle"});
  const right = frameAt(15, {pose: "idle"});
  assert.ok(left.gazeX < -0.1);
  assert.ok(right.gazeX > 0.1);
  assert.ok(Math.abs(left.headYaw) <= 0.16);
  assert.ok(Math.abs(right.headYaw) <= 0.16);
  assert.notEqual(ambientGazeAt(4).x, ambientGazeAt(15).x);
});

test("small idle gestures remain safe, and pointer has priority", () => {
  const f = frameAt(6, {pointerX: 1, pointerY: -1});
  assert.equal(f.gazeX, 1);
  assert.equal(f.gazeY, -1);
  assert.ok(Math.abs(f.leftArmSwing) < 0.08);
  assert.ok(Math.abs(f.rightArmSwing) < 0.08);
  assert.ok(Math.abs(f.hairSwing) < 0.026);
  assert.ok(Math.abs(f.bodyBob) < 0.01);
  assert.ok(Math.abs(f.bodySway) < 0.036);
});

test("blinks vary in timing, including a gentle double blink", () => {
  assert.ok(blinkAt(9.53) > 0.99);
  assert.ok(blinkAt(13.62) > 0.99);
  assert.ok(blinkAt(13.94) > 0.99);
  assert.equal(blinkAt(7), 0);
  assert.equal(blinkAt(13.62, true), 0);
});

test("accessibility reduced motion suppresses all automatic idle motion", () => {
  const f = frameAt(15, {reducedMotion: true});
  for (const key of ["blink", "gazeX", "gazeY", "headYaw", "headPitch",
                    "headTilt", "bodySway", "bodyBob", "breath",
                    "leftArmSwing", "rightArmSwing", "hairSwing"]) {
    assert.equal(f[key], 0, key);
  }
});
