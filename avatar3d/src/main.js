import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";
import { frameAt, expressionValues, smooth, clamp, EMOTIONS } from "./motion.mjs";
import { connectionFromFragment, normalizeRemoteState, reactionPose } from "./bridge_state.mjs";
import { createAnimePreview } from "./preview_character.js";
import {
  validateAppearance, readAppearance, writeAppearance,
  appearanceForPreset, applySharedAppearance, PRESETS
} from "./appearance.mjs";
import "./style.css";

// Renderização experimental isolada: nenhum acesso a Ollama, SQLite, shell, câmera ou microfone.
const stage = document.querySelector("#stage");
const message = document.querySelector("#message");
const renderStatus = document.querySelector("#renderStatus");
const powerMonitor = document.querySelector("#powerMonitor");
const powerLabel = document.querySelector("#powerLabel");
const powerFill = document.querySelector("#powerFill");
const powerIcon = document.querySelector("#powerIcon");
const modelInput = document.querySelector("#modelInput");
const fpsSelect = document.querySelector("#fps");
const reducedInput = document.querySelector("#reducedMotion");
const mouthInput = document.querySelector("#mouth");
const poseButtons = [...document.querySelectorAll("[data-pose]")];
const MAX_VRM_BYTES = 80 * 1024 * 1024;
const OS_REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function status(text) {
  message.textContent = text;
}

let renderer;
try {
  renderer = new THREE.WebGLRenderer({
    antialias: true, alpha: true, powerPreference: "high-performance"
  });
} catch {
  status("Este navegador não conseguiu iniciar WebGL. Verifique o driver de vídeo ou use a Yuna 2D.");
  modelInput.disabled = true;
  throw new Error("WebGL indisponível para o avatar experimental");
}
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.7));
stage.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xe7d6ff, 0x49305c, 2.2));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.6);
keyLight.position.set(1.8, 3.8, 3.5);
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0xa771ff, 1.7);
rimLight.position.set(-2, 2, -2);
scene.add(rimLight);

const camera = new THREE.PerspectiveCamera(31, 1, 0.1, 30);
camera.position.set(0, 1.35, 3.4);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.05, 0);
controls.enableDamping = true;
controls.dampingFactor = 0.065;
controls.minDistance = 1.15;
controls.maxDistance = 6;
controls.maxPolarAngle = Math.PI * 0.76;
controls.update();

function resetCamera() {
  camera.position.set(0, 1.35, 3.4);
  controls.target.set(0, 1.05, 0);
  controls.update();
}
document.querySelector("#resetCamera").addEventListener("click", resetCamera);

const lookAtTarget = new THREE.Object3D();
camera.add(lookAtTarget);

// A aparência original é renderizada a partir de geometria local, sem assets externos.
const appearanceFields = Object.freeze({
  hair: document.querySelector("#hairColor"),
  hair_style: document.querySelector("#hairStyle"),
  eyes: document.querySelector("#eyeColor"),
  outfit: document.querySelector("#outfitColor"),
  costume: document.querySelector("#costume"),
  accessory: document.querySelector("#accessory")
});
const presetSelector = document.querySelector("#appearancePreset");
let appearance;
try { appearance = readAppearance(window.localStorage); }
catch { appearance = appearanceForPreset("yuna"); }
let preview = createAnimePreview(appearance);
scene.add(preview.root);

function updateEditor() {
  for (const [key, control] of Object.entries(appearanceFields)) {
    control.value = appearance[key];
  }
  const match = Object.entries(PRESETS).find(([, preset]) =>
    Object.entries(appearance).every(([key, value]) => preset[key] === value));
  presetSelector.value = match ? match[0] : "custom";
}

function updatePreviewStyle(next, {save = true, feedback = true} = {}) {
  const checked = validateAppearance(next);
  const visible = !currentVrm;
  const old = preview;
  appearance = checked;
  preview = createAnimePreview(appearance);
  preview.root.visible = visible;
  scene.add(preview.root);
  old.dispose();
  updateEditor();
  if (save) {
    try { writeAppearance(window.localStorage, appearance); }
    catch { /* localStorage pode não estar disponível em modo privado */ }
  }
  if (feedback) {
    status(currentVrm
      ? "Visual salvo para a Yuna original. Modelos VRM importados não são editados."
      : "Visual atualizado! Este personagem é uma prévia 3D original, não um VRM.");
  }
}

for (const [key, control] of Object.entries(appearanceFields)) {
  control.addEventListener("change", () => {
    updatePreviewStyle({...appearance, [key]: control.value});
  });
}
presetSelector.addEventListener("change", () => {
  if (Object.hasOwn(PRESETS, presetSelector.value)) {
    updatePreviewStyle(appearanceForPreset(presetSelector.value));
  }
});
document.querySelector("#resetAppearance").addEventListener("click", () => {
  updatePreviewStyle(appearanceForPreset("yuna"));
});
document.querySelector("#restorePreview").addEventListener("click", () => {
  ++loadSerial; // invalida eventuais imports em andamento
  if (currentVrm) {
    scene.remove(currentVrm.scene);
    VRMUtils.deepDispose(currentVrm.scene);
    currentVrm = null;
    rig = null;
  }
  preview.root.visible = true;
  updatePose("idle");
  renderStatus.textContent = "Yuna original";
  status("Visualização geométrica original restaurada. Você pode personalizá-la.");
});
updateEditor();

let currentVrm = null;
let rig = null;
let pose = "idle";
let poseDeadline = 0;
let time = 0;
let lastFrame = performance.now();
let lastPaint = 0;
let cursorX = 0;
let cursorY = 0;
let gazeX = 0;
let gazeY = 0;
let loadSerial = 0;

function updatePose(next) {
  if (!EMOTIONS.includes(next)) return;
  pose = next;
  poseDeadline = next === "idle" ? 0 : performance.now() + 4300;
  for (const button of poseButtons) {
    button.classList.toggle("selected", button.dataset.pose === next);
    button.setAttribute("aria-pressed", String(button.dataset.pose === next));
  }
}
for (const button of poseButtons) {
  button.addEventListener("click", () => updatePose(button.dataset.pose));
}
updatePose("idle");

// Ponte opcional somente-leitura: o fragmento possui credencial efêmera, que
// retiramos imediatamente do histórico. Não há nenhum comando de volta à Yuna.
const bridge = connectionFromFragment(window.location.hash);
if (bridge) {
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
  renderStatus.textContent = "Conectando à Yuna Desktop...";
  status("Buscando o estado local da voz e das expressões...");
}
let remoteState = null;
let lastRemoteAt = 0;
let lastGestureSeq = -1;
let lastAppearanceRevision = 0;
let connected = false;
let powerLastKey = "";

function updateBatteryDisplay(battery) {
  if (!battery) {
    powerMonitor.hidden = true;
    powerLastKey = "";
    return;
  }
  const key = battery.mode + ":" + battery.percent + ":" + battery.plugged;
  if (powerLastKey === key) return;
  powerLastKey = key;
  powerMonitor.hidden = false;
  powerMonitor.dataset.mode = battery.mode;
  powerFill.style.width = battery.percent + "%";
  powerLabel.textContent = (
    battery.mode === "charging" ? "Carregando · " :
    battery.mode === "full" ? "Energia completa · " :
    battery.mode === "low" || battery.mode === "critical" ? "Precisa de carga · " :
    battery.mode === "tired" ? "Bateria baixa · " : "Bateria · "
  ) + battery.percent + "%";
  powerIcon.textContent = battery.mode === "full" ? "✦" :
    battery.mode === "charging" ? "⚡" :
    battery.mode === "low" || battery.mode === "critical" ? "☾" : "▰";
}

async function pollBridge() {
  if (!bridge) return;
  if (!document.hidden) {
    try {
      const response = await fetch(
        "http://127.0.0.1:" + bridge.port + "/v1/avatar-state",
        {
          method: "GET",
          headers: {"X-Yuna-Token": bridge.token},
          mode: "cors",
          cache: "no-store",
          signal: AbortSignal.timeout(1800)
        }
      );
      if (!response.ok) throw new Error("Bridge offline");
      const next = normalizeRemoteState(await response.json());
      if (!next) throw new Error("Invalid bridge state");
      if (remoteState === null || next.revision >= remoteState.revision) {
        remoteState = next;
      }
      lastRemoteAt = performance.now();
      updateBatteryDisplay(remoteState.battery);
      mouthInput.disabled = true;
      if (!connected) {
        connected = true;
        renderStatus.textContent = "Voz local conectada";
        status("Yuna Desktop vinculada. A boca acompanha o áudio Windows "
               + "e reage ao início/fim da fala. Voz MP3 usa animação aproximada.");
      }
      if (next.appearanceRevision > lastAppearanceRevision &&
          Object.keys(next.appearance).length > 0) {
        lastAppearanceRevision = next.appearanceRevision;
        updatePreviewStyle(
          applySharedAppearance(appearance, next.appearance),
          {save: false, feedback: false}
        );
      }
      if (next.gestureSeq !== lastGestureSeq) {
        lastGestureSeq = next.gestureSeq;
        if (next.gestureSeq > 0) updatePose(reactionPose(next));
      }
    } catch {
      if (connected) {
        connected = false;
        remoteState = null;
        updateBatteryDisplay(null);
        mouthInput.disabled = false;
        renderStatus.textContent = "Ponte 3D desconectada";
        status("A ligação com Yuna Desktop foi interrompida. A prévia 3D continua disponível.");
        updatePose("idle");
      }
    }
  }
  window.setTimeout(pollBridge, document.hidden ? 450 : 90);
}
if (bridge) pollBridge();

reducedInput.checked = OS_REDUCED_MOTION;
if (OS_REDUCED_MOTION && !bridge) {
  status("O Windows/navegador pediu redução de animações. Desmarque ‘Reduzir animações’ para ver a Yuna se movimentar.");
}
reducedInput.addEventListener("change", () => {
  status(reducedInput.checked
    ? "Animações reduzidas: piscar, olhar e movimentos de corpo ficam pausados. A boca continua funcionando."
    : "Animação viva ativada: Yuna respira, pisca em intervalos variados, olha ao redor e muda a postura.");
});
fpsSelect.value = "30";
renderer.domElement.addEventListener("pointermove", (event) => {
  const bounds = renderer.domElement.getBoundingClientRect();
  if (!bounds.width || !bounds.height) return;
  cursorX = clamp(((event.clientX - bounds.left) / bounds.width - 0.5) * 2, -1, 1);
  cursorY = clamp(((event.clientY - bounds.top) / bounds.height - 0.5) * 2, -1, 1);
});
renderer.domElement.addEventListener("pointerleave", () => {
  cursorX = 0;
  cursorY = 0;
});

function createRig(vrm) {
  const bone = (name) => vrm.humanoid?.getNormalizedBoneNode(name) || null;
  const head = bone("head");
  const upperArm = bone("rightUpperArm");
  const leftArm = bone("leftUpperArm");
  const chest = bone("chest");
  return {
    head, upperArm, leftArm, chest,
    originalHead: head?.quaternion.clone(),
    originalArm: upperArm?.quaternion.clone(),
    originalLeftArm: leftArm?.quaternion.clone(),
    originalChest: chest?.quaternion.clone()
  };
}

const tempRotation = new THREE.Quaternion();
const tempEuler = new THREE.Euler();
function applyRotation(node, original, x, y, z, dt) {
  if (!node || !original) return;
  tempEuler.set(x, y, z, "XYZ");
  tempRotation.setFromEuler(tempEuler).premultiply(original);
  node.quaternion.slerp(tempRotation, Math.min(1, dt * 9));
}

function animateVrm(frame, dt) {
  if (!currentVrm || !rig) return;
  const expr = currentVrm.expressionManager;
  if (expr) {
    for (const [name, value] of Object.entries(expressionValues(frame))) {
      if (expr.getExpression(name)) expr.setValue(name, value);
    }
  }
  applyRotation(rig.head, rig.originalHead, frame.headPitch,
                frame.headYaw, frame.headTilt, dt);
  applyRotation(rig.upperArm, rig.originalArm, frame.breath * 0.5, 0,
                frame.emotion === "wave" ? -1.05 + frame.wave :
                frame.rightArmSwing, dt);
  applyRotation(rig.leftArm, rig.originalLeftArm, -frame.breath * 0.5, 0,
                -frame.leftArmSwing, dt);
  applyRotation(rig.chest, rig.originalChest, frame.breath * 0.65, 0,
                frame.bodySway * 0.5, dt);
  if (currentVrm.lookAt) {
    lookAtTarget.position.set(frame.gazeX * 1.1, -frame.gazeY * 0.65, 0);
  }
  currentVrm.update(dt);
}

// Nenhum modelo é fornecido por padrão: o próprio usuário escolhe um arquivo
// VRM que possui o direito de usar. O blob nunca é enviado a serviço externo.
const loader = new GLTFLoader();
loader.register((parser) => new VRMLoaderPlugin(parser));

async function loadLocalVrm(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".vrm") || !file.size ||
      file.size > MAX_VRM_BYTES) {
    status("Selecione um arquivo .vrm válido de até 80 MB.");
    return;
  }
  const ticket = ++loadSerial;
  const url = URL.createObjectURL(file);
  status("Lendo o modelo local e preparando o personagem...");
  try {
    const gltf = await loader.loadAsync(url);
    const vrm = gltf.userData?.vrm;
    if (!vrm) throw new Error("O arquivo não contém metadados VRM válidos.");
    if (ticket !== loadSerial) {
      VRMUtils.deepDispose(vrm.scene);
      return;
    }
    try {
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      VRMUtils.removeUnnecessaryJoints(gltf.scene);
    } catch {
      // A ausência de uma otimização não deve impedir a visualização.
    }
    vrm.scene.traverse((obj) => { obj.frustumCulled = false; });
    if (currentVrm) {
      scene.remove(currentVrm.scene);
      VRMUtils.deepDispose(currentVrm.scene);
    }
    scene.add(vrm.scene);
    currentVrm = vrm;
    rig = createRig(vrm);
    if (vrm.lookAt) vrm.lookAt.target = lookAtTarget;
    preview.root.visible = false;
    updatePose("idle");
    renderStatus.textContent = "VRM local ativo";
    status("Modelo carregado nesta aba: " + file.name + ". Teste os gestos e o olhar.");
  } catch {
    status("Não consegui carregar este VRM. Verifique o arquivo e tente outro.");
  } finally {
    URL.revokeObjectURL(url);
    modelInput.value = "";
  }
}
modelInput.addEventListener("change", () => loadLocalVrm(modelInput.files?.[0]));
stage.addEventListener("dragover", (event) => {
  if ([...(event.dataTransfer?.types || [])].includes("Files")) event.preventDefault();
});
stage.addEventListener("drop", (event) => {
  event.preventDefault();
  loadLocalVrm(event.dataTransfer?.files?.[0]);
});

function resizeStage() {
  const width = Math.max(1, stage.clientWidth);
  const height = Math.max(1, stage.clientHeight);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
}
new ResizeObserver(resizeStage).observe(stage);
resizeStage();

function animate(now) {
  requestAnimationFrame(animate);
  if (document.hidden) {
    lastFrame = now;
    lastPaint = now;
    return;
  }
  const fresh = remoteState !== null && now - lastRemoteAt < 1800;
  const battery = fresh ? remoteState.battery : null;
  const lowBattery = battery && !battery.plugged &&
    (battery.mode === "critical" || battery.mode === "low");
  const minInterval = 1000 / (lowBattery
    ? Math.min(Number(fpsSelect.value || 30), 12)
    : Number(fpsSelect.value || 30));
  if (now - lastPaint < minInterval) return;
  const dt = clamp((now - lastFrame) / 1000, 0, 0.08);
  lastFrame = now;
  lastPaint = now;
  time += dt;
  if (pose !== "idle" && poseDeadline && now > poseDeadline) updatePose("idle");
  gazeX = smooth(gazeX, cursorX, 5.5, dt);
  gazeY = smooth(gazeY, cursorY, 5.5, dt);
  const isRemoteFresh = remoteState !== null
    && performance.now() - lastRemoteAt < 1800;
  const speechActive = isRemoteFresh && remoteState.speaking;
  // WAV: envelope de amplitude real medido pelo player Python.
  // MP3: pulsação aproximada somente durante a reprodução autorizada.
  const mouthLevel = isRemoteFresh
    ? (speechActive
      ? (remoteState.hasAmplitude
        ? remoteState.mouthLevel
        : 0.12 + 0.25 * (0.5 + 0.5 * Math.sin(time * 20)))
      : 0)
    : Number(mouthInput.value) / 100;
  const batteryPose = battery && pose === "idle" && !speechActive
    ? (lowBattery ? "sleepy" :
       battery.mode === "tired" || battery.mode === "charging" ? "sit" :
       battery.mode === "full" ? "happy" : pose)
    : pose;
  const frame = frameAt(time, {
    pose: batteryPose, pointerX: gazeX, pointerY: gazeY,
    mouthLevel,
    reducedMotion: reducedInput.checked
  });
  if (currentVrm) animateVrm(frame, dt);
  else preview.animate(frame, frame.gazeX, frame.gazeY, dt);
  controls.update();
  renderer.render(scene, camera);
}

requestAnimationFrame(animate);
