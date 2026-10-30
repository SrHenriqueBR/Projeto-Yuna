import test from "node:test";
import assert from "node:assert/strict";
import * as THREE from "three";
import { performanceFrame, PerformanceDirector } from "../src/performance.mjs";
import { VrmPerformer } from "../src/vrm_performer.mjs";

test("full body walk has alternating legs, wrists, knees and chest", () => {
  const frame = performanceFrame(1.5, {pose:"walk"});
  assert.ok(frame.leftLeg * frame.rightLeg <= 0);
  assert.ok(Math.abs(frame.leftLeg) > 0.1);
  assert.ok(Math.abs(frame.leftArmSwing) > 0.05);
  assert.ok(frame.leftKnee >= 0 && frame.rightKnee >= 0);
  assert.ok(Number.isFinite(frame.spineTwist));
  assert.ok(Number.isFinite(frame.hipShift));
});

test("wave, shy, sleep, wink and angry have distinct poses", () => {
  const wave = performanceFrame(1.6, {pose:"wave"});
  assert.ok(wave.rightElbow > 0.9);
  assert.ok(Math.abs(wave.rightWrist) > 0.01);
  assert.equal(performanceFrame(1.6,{pose:"shy"}).leftElbow, 0.55);
  assert.equal(performanceFrame(1.6,{pose:"angry"}).rightElbow, 0.68);
  assert.ok(performanceFrame(1.6,{pose:"sit"}).hipDrop < 0);
  assert.equal(performanceFrame(1.6,{pose:"wink"}).blinkRight, 1);
  assert.equal(performanceFrame(1.6,{pose:"sleepy"}).blinkLeft, 1);
});

test("spoken nods and intensity are strictly gated", () => {
  const normal = performanceFrame(1.5,{pose:"idle"});
  const talk = performanceFrame(1.5,{pose:"idle",talking:true});
  assert.notEqual(normal.headPitch, talk.headPitch);
  const reduced = performanceFrame(1.5,{pose:"wave",talking:true,reducedMotion:true});
  for (const key of ["headYaw","headPitch","headTilt","hipDrop","bodyBob",
                     "rightElbow","leftElbow","rightWrist","leftLeg","wave"]) {
    assert.equal(reduced[key], 0, key);
  }
  const idle = performanceFrame(1.5,{pose:"wave",intensity:0});
  assert.equal(idle.rightElbow, 0);
  assert.equal(idle.wave, 0);
  assert.equal(idle.headYaw, 0);
  assert.equal(idle.bodySway, 0);
  assert.equal(idle.breath, 0);
  assert.equal(idle.gazeX, 0);
  assert.equal(idle.motionStrength, 0);
  assert.equal(performanceFrame(1.5,{mouthLevel:42}).mouth,1);
  assert.equal(performanceFrame(1.5,{mouthLevel:NaN}).mouth,0);
});

test("director blends gestural changes smoothly and supports reset", () => {
  const director = new PerformanceDirector();
  const idle = director.step(1,{pose:"idle"},1/60);
  const firstWave = director.step(1.016,{pose:"wave"},1/60);
  const targetWave = performanceFrame(1.016,{pose:"wave"});
  assert.ok(firstWave.rightElbow > idle.rightElbow);
  assert.ok(firstWave.rightElbow < targetWave.rightElbow);
  for(let i=0;i<120;i++) director.step(1.032+i/60,{pose:"wave"},1/60);
  const state = director.step(3.05,{pose:"wave"},1/60);
  assert.ok(state.rightElbow > 0.95);
  const fade = director.step(3.067,{pose:"idle"},1/60);
  assert.ok(fade.rightElbow < state.rightElbow);
  assert.ok(fade.rightElbow > performanceFrame(3.067).rightElbow);
  director.reset();
  assert.equal(director.step(3.1,{pose:"idle"}).rightElbow,
               performanceFrame(3.1).rightElbow);
});

function mockVrm(names) {
  const bones = new Map(names.map(name=>[name,new THREE.Object3D()]));
  const used = new Map();
  const expressions = new Set(["blink","aa","happy","angry","relaxed","surprised"]);
  let updates = 0;
  return {
    bones,used,
    humanoid:{getNormalizedBoneNode:name=>bones.get(name)||null},
    expressionManager:{
      getExpression(name){return expressions.has(name)?{expressionName:name}:null;},
      setValue(name,val){used.set(name,val);}
    },
    update(dt){assert.ok(dt>0); updates++},
    get updates(){return updates}
  };
}
const allBones=["hips","spine","chest","upperChest","neck","head",
 "leftShoulder","rightShoulder","leftUpperArm","rightUpperArm",
 "leftLowerArm","rightLowerArm","leftHand","rightHand",
 "leftUpperLeg","rightUpperLeg","leftLowerLeg","rightLowerLeg","leftFoot","rightFoot"];

test("VRM performer lowers T-pose arms and animates wrist, legs and facial channels", () => {
  const vrm=mockVrm(allBones);
  const performer=new VrmPerformer(vrm);
  const idle=performanceFrame(1,{pose:"idle"});
  for(let i=0;i<70;i++)performer.update(idle,1/60);
  assert.ok(vrm.bones.get("rightUpperArm").rotation.z < -0.7);
  assert.ok(vrm.bones.get("leftUpperArm").rotation.z > 0.7);
  assert.ok(vrm.updates>50);
  const hand=vrm.bones.get("rightHand").quaternion.clone();
  for(let i=0;i<70;i++)performer.update(performanceFrame(2,{pose:"wave",mouthLevel:.9}),1/60);
  assert.ok(vrm.bones.get("rightUpperArm").rotation.z > 0);
  assert.ok(vrm.bones.get("rightHand").quaternion.angleTo(hand) > 0.1);
  assert.equal(vrm.used.get("aa"),0.9);
  for(let i=0;i<70;i++)performer.update(performanceFrame(2.2,{pose:"walk"}),1/60);
  assert.ok(Math.abs(vrm.bones.get("leftUpperLeg").rotation.x)>0.05);
  assert.ok(Math.abs(vrm.bones.get("rightUpperLeg").rotation.x)>0.05);
});

test("VRM performer gracefully skips optional missing bones or expressions",()=>{
  const vrm=mockVrm(["head"]);
  const p=new VrmPerformer(vrm);
  p.update(performanceFrame(1,{pose:"surprised"}),1/30);
  assert.ok(vrm.used.get("surprised")>=0);
  assert.doesNotThrow(()=>p.update(performanceFrame(2,{pose:"sleepy"}),1/30));
  assert.throws(()=>new VrmPerformer(null),TypeError);
});
