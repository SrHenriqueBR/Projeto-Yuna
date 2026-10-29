/** Modelo original 3D em geometria Three.js, desenhado para prévia local.
 * Não é um avatar VRM rigado, nem modelo de terceiros.
 */
import * as THREE from "three";
import { PALETTES, validateAppearance } from "./appearance.mjs";
import { smooth, clamp } from "./motion.mjs";

const SPHERE_SEGMENTS = 24;

function sphere(parent, material, position, scale, segments = SPHERE_SEGMENTS) {
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(1, segments, 16), material
  );
  mesh.position.set(...position);
  mesh.scale.set(...scale);
  parent.add(mesh);
  return mesh;
}

function cylinder(parent, material, top, bottom, height, position, segments = 20) {
  const object = new THREE.Mesh(
    new THREE.CylinderGeometry(top, bottom, height, segments), material
  );
  object.position.set(...position);
  parent.add(object);
  return object;
}

function strand(parent, material, points, radius = 0.025) {
  const curve = new THREE.CatmullRomCurve3(points.map(point => new THREE.Vector3(...point)));
  const object = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 12, radius, 7, false), material
  );
  parent.add(object);
  return object;
}

function capsule(parent, material, start, end, width) {
  const a = new THREE.Vector3(...start);
  const b = new THREE.Vector3(...end);
  const center = a.clone().add(b).multiplyScalar(0.5);
  const delta = b.clone().sub(a);
  const object = sphere(parent, material, center.toArray(),
    [width, delta.length() / 2 + width * 0.35, width], 20);
  object.quaternion.setFromUnitVectors(
    new THREE.Vector3(0, 1, 0), delta.normalize()
  );
  return object;
}

function bow(parent, materials, center = [0, 0, 0], scale = 1) {
  const group = new THREE.Group();
  group.position.set(...center);
  group.scale.setScalar(scale);
  sphere(group, materials.accent, [-0.075, 0, 0], [0.09, 0.058, 0.035]);
  sphere(group, materials.accent, [0.075, 0, 0], [0.09, 0.058, 0.035]);
  sphere(group, materials.dark, [0, 0, 0.032], [0.034, 0.036, 0.027]);
  parent.add(group);
  return group;
}

function createMaterials(appearance) {
  return {
    skin: new THREE.MeshToonMaterial({color: "#f8dcdb"}),
    shadowSkin: new THREE.MeshToonMaterial({color: "#e9b8c7"}),
    hair: new THREE.MeshToonMaterial({color: PALETTES.hair[appearance.hair]}),
    shine: new THREE.MeshToonMaterial({
      color: new THREE.Color(PALETTES.hair[appearance.hair]).lerp(
        new THREE.Color("#eac2ff"), 0.20)
    }),
    iris: new THREE.MeshToonMaterial({color: PALETTES.eyes[appearance.eyes]}),
    pupil: new THREE.MeshToonMaterial({color: "#25132b"}),
    white: new THREE.MeshToonMaterial({color: "#fcf9ff"}),
    lash: new THREE.MeshToonMaterial({color: "#2b162e"}),
    blush: new THREE.MeshToonMaterial({
      color: "#df819f", transparent: true, opacity: 0.56
    }),
    mouth: new THREE.MeshToonMaterial({color: "#ad4965"}),
    dress: new THREE.MeshToonMaterial({color: PALETTES.outfit[appearance.outfit]}),
    dark: new THREE.MeshToonMaterial({color: "#1e162c"}),
    accent: new THREE.MeshToonMaterial({color: "#a98af1"}),
    trim: new THREE.MeshToonMaterial({color: "#c6aaff"}),
    metal: new THREE.MeshStandardMaterial({
      color: "#c7b7e3", metalness: 0.62, roughness: 0.28
    })
  };
}

function addOutfit(root, materials, appearance) {
  const { skin, dress, accent, dark, trim } = materials;
  const skirt = cylinder(root, dress, 0.195, 0.315, 0.41, [0, 0.50, 0]);
  skirt.scale.z = 0.77;
  sphere(root, dress, [0, 0.77, 0], [0.217, 0.31, 0.145]);
  sphere(root, skin, [0, 1.015, 0], [0.06, 0.11, 0.065]);

  for (const side of [-1, 1]) {
    capsule(root, skin, [side * 0.11, 0.34, 0],
      [side * 0.11, 0.12, 0], 0.067);
    sphere(root, dark, [side * 0.11, 0.095, 0.047], [0.106, 0.067, 0.155]);
    strand(root, trim, [
      [side * 0.24, 0.54, 0.02],
      [side * 0.28, 0.46, 0.04],
      [side * 0.29, 0.34, 0.04]
    ], 0.012);
  }

  if (appearance.costume === "vestido") {
    for (const side of [-1, 1]) {
      strand(root, trim, [
        [side * 0.04, 1.00, 0.139],
        [side * 0.08, 0.89, 0.150],
        [side * 0.07, 0.77, 0.147]
      ], 0.012);
    }
    bow(root, materials, [0, 0.85, 0.156], 0.58);
    cylinder(root, dark, 0.16, 0.17, 0.047, [0, 0.61, 0]);
  } else if (appearance.costume === "casual") {
    sphere(root, accent, [0, 0.77, 0.142], [0.092, 0.082, 0.022]);
    strand(root, dark, [
      [-0.20, 0.92, 0.03], [-0.08, 0.78, 0.145], [0.16, 0.66, 0.14]
    ], 0.019);
  } else if (appearance.costume === "casaco") {
    sphere(root, accent, [0, 0.985, 0.116], [0.24, 0.083, 0.14]);
    for (const side of [-1, 1]) {
      cylinder(root, trim, 0.13, 0.12, 0.29, [side * 0.18, 0.80, 0.01]);
      strand(root, dark, [
        [side * 0.17, 0.96, 0.10],
        [side * 0.13, 0.74, 0.147],
        [side * 0.12, 0.60, 0.13]
      ], 0.014);
    }
  }
  return { skirt };
}

function addHair(head, materials, appearance) {
  const { hair, shine } = materials;
  const back = new THREE.Group();
  back.position.set(0, 0.0, -0.14);
  head.add(back);
  sphere(back, hair, [0, 0.05, -0.06], [0.36, 0.38, 0.265]);

  const short = appearance.hair_style === "curto";
  const tail = appearance.hair_style === "rabo";
  const twin = appearance.hair_style === "marias";
  if (!short && !tail && !twin) {
    for (const side of [-1, 1]) {
      sphere(back, hair, [side * 0.25, -0.30, -0.06], [0.135, 0.36, 0.18]);
      strand(back, shine, [
        [side * 0.24, -0.02, 0.09],
        [side * 0.28, -0.32, 0.10],
        [side * 0.23, -0.56, 0.05]
      ], 0.028);
    }
  } else if (tail) {
    const pony = new THREE.Group();
    pony.position.set(0, 0.18, -0.28);
    back.add(pony);
    sphere(pony, hair, [0, -0.29, -0.065], [0.19, 0.36, 0.14]);
    bow(pony, materials, [0, -0.02, -0.15], 0.75);
  } else if (twin) {
    for (const side of [-1, 1]) {
      sphere(back, hair, [side * 0.34, -0.23, -0.06], [0.155, 0.36, 0.14]);
      bow(back, materials, [side * 0.34, 0.065, 0], 0.7);
    }
  }

  sphere(head, hair, [0, 0.26, -0.045], [0.343, 0.17, 0.279]);
  const bangs = [-0.22, -0.11, -0.015, 0.095, 0.205];
  for (const x of bangs) {
    const lock = sphere(head, Math.abs(x - 0.095) < 0.01 ? shine : hair,
      [x, 0.16 - 0.13 * Math.abs(x), 0.228],
      [0.082, 0.165 + 0.025 * Math.abs(x), 0.083]);
    lock.rotation.z = x * 0.9;
  }
  for (const side of [-1, 1]) {
    sphere(head, hair, [side * 0.30, -0.12, 0.035],
      [0.11, short ? 0.25 : 0.30, 0.155]);
    strand(head, shine, [
      [side * 0.17, 0.29, 0.13],
      [side * 0.28, 0.11, 0.20],
      [side * 0.30, -0.22, 0.09]
    ], 0.018);
  }
  return back;
}

function addAccessory(head, materials, appearance) {
  if (appearance.accessory === "nenhum") return;
  if (appearance.accessory === "laco") {
    bow(head, materials, [0.29, 0.29, 0.065], 0.9);
  } else if (appearance.accessory === "tiara") {
    const curve = [
      [-0.315, 0.05, 0.09],
      [-0.25, 0.29, 0.10],
      [0, 0.40, 0.11],
      [0.25, 0.29, 0.10],
      [0.315, 0.05, 0.09]
    ];
    strand(head, materials.metal, curve, 0.023);
    sphere(head, materials.accent, [0, 0.413, 0.112], [0.035, 0.034, 0.018]);
  } else if (appearance.accessory === "oculos") {
    for (const side of [-1, 1]) {
      const outer = new THREE.Mesh(
        new THREE.TorusGeometry(0.12, 0.013, 8, 24), materials.metal
      );
      outer.position.set(side * 0.148, -0.005, 0.332);
      outer.scale.set(1, 0.85, 1);
      head.add(outer);
    }
    strand(head, materials.metal, [
      [-0.04, -0.003, 0.333],
      [0, 0.018, 0.339],
      [0.04, -0.003, 0.333]
    ], 0.011);
  }
}

/** Constructs an original stylized anime character entirely from geometry. */
export function createAnimePreview(style = {}) {
  const appearance = validateAppearance(style);
  const mats = createMaterials(appearance);
  const root = new THREE.Group();
  root.name = "YunaOriginalAnimePreview";
  const outfit = addOutfit(root, mats, appearance);

  const leftArm = new THREE.Group();
  leftArm.position.set(-0.22, 0.96, 0);
  capsule(leftArm, mats.dress, [-0.035, -0.06, 0],
    [-0.095, -0.27, 0.015], 0.098);
  sphere(leftArm, mats.skin, [-0.11, -0.32, 0.02], [0.070, 0.09, 0.07]);
  root.add(leftArm);

  const rightArm = new THREE.Group();
  rightArm.position.set(0.22, 0.96, 0);
  capsule(rightArm, mats.dress, [0.035, -0.06, 0],
    [0.095, -0.27, 0.015], 0.098);
  sphere(rightArm, mats.skin, [0.11, -0.32, 0.02], [0.070, 0.09, 0.07]);
  root.add(rightArm);

  const headPivot = new THREE.Group();
  headPivot.position.set(0, 1.29, 0);
  root.add(headPivot);
  sphere(headPivot, mats.skin, [0, 0, 0.035], [0.308, 0.334, 0.275]);
  sphere(headPivot, mats.shadowSkin, [0, -0.245, 0.137],
    [0.135, 0.088, 0.104]);
  for (const side of [-1, 1]) {
    sphere(headPivot, mats.skin, [side * 0.298, -0.035, 0],
      [0.057, 0.085, 0.065]);
    sphere(headPivot, mats.blush, [side * 0.196, -0.142, 0.293],
      [0.07, 0.036, 0.013]);
  }
  sphere(headPivot, mats.skin, [0, -0.115, 0.309], [0.026, 0.023, 0.026]);
  const mouth = sphere(headPivot, mats.mouth, [0, -0.197, 0.307],
    [0.040, 0.017, 0.013]);

  const eyes = [];
  for (const side of [-1, 1]) {
    const eye = new THREE.Group();
    eye.position.set(side * 0.143, 0.015, 0.283);
    sphere(eye, mats.white, [0, 0, 0], [0.091, 0.116, 0.026]);
    const irisGroup = new THREE.Group();
    sphere(irisGroup, mats.iris, [0, -0.008, 0.027],
      [0.061, 0.082, 0.013]);
    sphere(irisGroup, mats.pupil, [0, -0.003, 0.040],
      [0.034, 0.052, 0.011]);
    sphere(irisGroup, mats.white, [-0.020, 0.029, 0.049],
      [0.015, 0.024, 0.008]);
    sphere(irisGroup, mats.white, [0.022, -0.036, 0.048],
      [0.007, 0.010, 0.004]);
    eye.add(irisGroup);
    capsule(eye, mats.lash,
      [-0.097, 0.091, 0.007], [0.101, 0.097, 0.007], 0.017);
    headPivot.add(eye);
    const eyebrow = capsule(headPivot, mats.lash,
      [side * 0.143 - 0.070, 0.158, 0.288],
      [side * 0.143 + 0.070, 0.172, 0.285], 0.013);
    eyes.push({eye, irisGroup, eyebrow});
  }
  const backHair = addHair(headPivot, mats, appearance);
  addAccessory(headPivot, mats, appearance);

  let dead = false;
  const preview = {
    appearance, root, headPivot, leftArm, rightArm, eyes, mouth, backHair, outfit,
    animate(frame, gazeX = 0, gazeY = 0, dt = 1 / 30) {
      if (dead) return;
      headPivot.rotation.y = smooth(headPivot.rotation.y, frame.headYaw, 6, dt);
      headPivot.rotation.x = smooth(headPivot.rotation.x, frame.headPitch, 6, dt);
      headPivot.rotation.z = smooth(headPivot.rotation.z,
        frame.emotion === "curious" ? -0.06 : 0, 6, dt);
      root.position.y = frame.breath;
      root.rotation.z = frame.bodySway;
      rightArm.rotation.z = frame.emotion === "wave"
        ? -2.1 + frame.wave : -0.14;
      leftArm.rotation.z = 0.14;
      backHair.rotation.z = -frame.bodySway * 1.6;
      for (const {eye, irisGroup, eyebrow} of eyes) {
        const surprised = frame.emotion === "surprised";
        const wink = frame.emotion === "shy";
        eye.scale.y = Math.max(0.03, (surprised ? 1.10 : 1) -
          frame.blink * (wink ? 0.99 : 0.96));
        irisGroup.position.set(clamp(gazeX, -1, 1) * 0.019,
          -clamp(gazeY, -1, 1) * 0.012, 0);
        eyebrow.position.y = frame.emotion === "curious" ? 0.018 : 0;
      }
      mouth.scale.y = frame.mouth > 0
        ? 0.018 + frame.mouth * 0.095
        : frame.emotion === "happy" ? 0.025 : 0.013;
    },
    dispose() {
      if (dead) return;
      dead = true;
      const geometries = new Set();
      const materials = new Set();
      root.traverse(node => {
        if (!node.isMesh) return;
        if (node.geometry) geometries.add(node.geometry);
        if (Array.isArray(node.material)) {
          for (const material of node.material) materials.add(material);
        } else if (node.material) materials.add(node.material);
      });
      for (const geometry of geometries) geometry.dispose();
      for (const material of materials) material.dispose();
      root.removeFromParent();
    }
  };
  return preview;
}
