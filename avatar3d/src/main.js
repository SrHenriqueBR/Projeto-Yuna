import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";
import { frameAt, expressionValues, smooth, clamp, EMOTIONS } from "./motion.mjs";
import { connectionFromFragment, normalizeRemoteState, reactionPose } from "./bridge_state.mjs";
import "./style.css";

// Renderização experimental isolada: nenhum acesso a Ollama, SQLite, shell, câmera ou microfone.
const stage = document.querySelector("#stage");
const message = document.querySelector("#message");
const renderStatus = document.querySelector("#renderStatus");
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

function addEllipsoid(parent, material, location, size, segments = 28) {
  const object = new THREE.Mesh(
    new THREE.SphereGeometry(1, segments, 20), material
  );
  object.position.set(...location);
  object.scale.set(...size);
  parent.add(object);
  return object;
}

// Um personagem geométrico ORIGINAL permite testar a cena sem distribuir modelos de terceiros.
// Não é um arquivo VRM, não substitui o futuro modelo artístico da Yuna.
function createPreviewCharacter() {
  const root = new THREE.Group();
  const skin = new THREE.MeshToonMaterial({ color: 0xf5d7da });
  const hair = new THREE.MeshToonMaterial({ color: 0x24132f });
  const hairHighlight = new THREE.MeshToonMaterial({ color: 0x563670 });
  const outfit = new THREE.MeshToonMaterial({ color: 0x33234a });
  const lilac = new THREE.MeshToonMaterial({ color: 0xa884f7 });
  const white = new THREE.MeshToonMaterial({ color: 0xfffafb });
  const iris = new THREE.MeshToonMaterial({ color: 0x9356e1 });
  const pupils = new THREE.MeshToonMaterial({ color: 0x251335 });
  const blush = new THREE.MeshToonMaterial({ color: 0xe99bba, transparent: true, opacity: 0.52 });

  addEllipsoid(root, outfit, [0, 0.73, 0], [0.23, 0.36, 0.16]);
  addEllipsoid(root, lilac, [0, 0.95, 0.155], [0.16, 0.05, 0.028]);
  const skirt = new THREE.Mesh(new THREE.ConeGeometry(0.36, 0.48, 32), outfit);
  skirt.rotation.z = Math.PI;
  skirt.position.set(0, 0.45, 0);
  root.add(skirt);
  for (const side of [-1, 1]) {
    addEllipsoid(root, skin, [side * 0.125, 0.18, 0], [0.07, 0.21, 0.08]);
    addEllipsoid(root, outfit, [side * 0.125, 0.065, 0.045], [0.105, 0.06, 0.14]);
  }

  const leftArm = new THREE.Group();
  leftArm.position.set(-0.23, 0.94, 0);
  addEllipsoid(leftArm, outfit, [-0.08, -0.17, 0], [0.11, 0.20, 0.11]);
  addEllipsoid(leftArm, skin, [-0.10, -0.35, 0.04], [0.064, 0.085, 0.065]);
  root.add(leftArm);
  const rightArm = new THREE.Group();
  rightArm.position.set(0.23, 0.94, 0);
  addEllipsoid(rightArm, outfit, [0.08, -0.17, 0], [0.11, 0.20, 0.11]);
  addEllipsoid(rightArm, skin, [0.10, -0.35, 0.04], [0.064, 0.085, 0.065]);
  root.add(rightArm);

  const headPivot = new THREE.Group();
  headPivot.position.y = 1.25;
  addEllipsoid(headPivot, hair, [0, -0.015, -0.13], [0.38, 0.43, 0.26]);
  addEllipsoid(headPivot, skin, [0, 0, 0.025], [0.305, 0.325, 0.28]);
  addEllipsoid(headPivot, hair, [0, 0.255, -0.01], [0.34, 0.17, 0.30]);
  for (const side of [-1, 1]) {
    addEllipsoid(headPivot, hair, [side * 0.29, -0.15, -0.065], [0.115, 0.30, 0.185]);
    addEllipsoid(headPivot, blush, [side * 0.185, -0.115, 0.288], [0.062, 0.035, 0.014]);
  }
  for (const x of [-0.19, -0.075, 0.07, 0.19]) {
    const strand = addEllipsoid(
      headPivot, x === 0.07 ? hairHighlight : hair,
      [x, 0.185 - Math.abs(x) * 0.13, 0.232], [0.10, 0.18, 0.10]
    );
    strand.rotation.z = x * 0.8;
  }

  const eyes = [];
  for (const side of [-1, 1]) {
    const eye = new THREE.Group();
    eye.position.set(side * 0.138, 0.016, 0.286);
    addEllipsoid(eye, white, [0, 0, 0], [0.087, 0.113, 0.028]);
    const pupil = new THREE.Group();
    addEllipsoid(pupil, iris, [0, -0.005, 0.026], [0.054, 0.076, 0.015]);
    addEllipsoid(pupil, pupils, [0, -0.005, 0.04], [0.03, 0.053, 0.01]);
    addEllipsoid(pupil, white, [-0.018, 0.025, 0.053], [0.014, 0.021, 0.007]);
    eye.add(pupil);
    headPivot.add(eye);
    eyes.push({ eye, pupil });
  }
  const mouth = addEllipsoid(headPivot, blush, [0, -0.18, 0.30], [0.035, 0.012, 0.012]);
  root.add(headPivot);
  return { root, headPivot, leftArm, rightArm, eyes, mouth };
}

const preview = createPreviewCharacter();
scene.add(preview.root);
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
let connected = false;

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
      mouthInput.disabled = true;
      if (!connected) {
        connected = true;
        renderStatus.textContent = "Voz local conectada";
        status("Yuna Desktop vinculada. A boca acompanha o áudio Windows "
               + "e reage ao início/fim da fala. Voz MP3 usa animação aproximada.");
      }
      if (next.gestureSeq !== lastGestureSeq) {
        lastGestureSeq = next.gestureSeq;
        if (next.gestureSeq > 0) updatePose(reactionPose(next));
      }
    } catch {
      if (connected) {
        connected = false;
        remoteState = null;
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
  const chest = bone("chest");
  return {
    head, upperArm, chest,
    originalHead: head?.quaternion.clone(),
    originalArm: upperArm?.quaternion.clone(),
    originalChest: chest?.quaternion.clone()
  };
}

function animatePreview(frame, dt) {
  preview.headPivot.rotation.y = smooth(preview.headPivot.rotation.y, frame.headYaw, 6, dt);
  preview.headPivot.rotation.x = smooth(preview.headPivot.rotation.x, frame.headPitch, 6, dt);
  preview.root.position.y = frame.breath;
  preview.root.rotation.z = frame.bodySway;
  preview.rightArm.rotation.z = frame.emotion === "wave" ? -2.1 + frame.wave : -0.14;
  preview.leftArm.rotation.z = 0.14;
  for (const { eye, pupil } of preview.eyes) {
    eye.scale.y = Math.max(0.05, 1 - frame.blink * 0.97);
    pupil.position.x = gazeX * 0.018;
    pupil.position.y = -gazeY * 0.012;
  }
  preview.mouth.scale.y = 0.012 + frame.mouth * 0.085;
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
                frame.headYaw, frame.emotion === "curious" ? -0.08 : 0, dt);
  applyRotation(rig.upperArm, rig.originalArm, 0, 0,
                frame.emotion === "wave" ? -1.05 + frame.wave : 0, dt);
  applyRotation(rig.chest, rig.originalChest, 0, 0, frame.bodySway * 0.5, dt);
  if (currentVrm.lookAt) {
    lookAtTarget.position.set(gazeX * 1.1, -gazeY * 0.65, 0);
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
  const minInterval = 1000 / Number(fpsSelect.value || 30);
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
  const frame = frameAt(time, {
    pose, pointerX: gazeX, pointerY: gazeY,
    mouthLevel,
    reducedMotion: reducedInput.checked
  });
  if (currentVrm) animateVrm(frame, dt);
  else animatePreview(frame, dt);
  controls.update();
  renderer.render(scene, camera);
}

requestAnimationFrame(animate);
