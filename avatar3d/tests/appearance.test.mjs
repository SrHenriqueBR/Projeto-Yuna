import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_APPEARANCE, PALETTES, OPTIONS, PRESETS,
  validateAppearance, appearanceForPreset,
  readAppearance, writeAppearance, APPEARANCE_STORAGE_KEY,
  applySharedAppearance
} from "../src/appearance.mjs";
import { createAnimePreview } from "../src/preview_character.js";
import { frameAt } from "../src/motion.mjs";

test("appearance fields are validated against the original palettes", () => {
  const value = validateAppearance({
    hair: "ruivo", eyes: "INJECTED", accessory: 23,
    costume: "casaco", unexpected: "not allowed"
  });
  assert.equal(value.hair, "ruivo");
  assert.equal(value.eyes, DEFAULT_APPEARANCE.eyes);
  assert.equal(value.accessory, DEFAULT_APPEARANCE.accessory);
  assert.equal(value.costume, "casaco");
  assert.equal(value.unexpected, undefined);
  assert.equal(Object.keys(value).length, Object.keys(DEFAULT_APPEARANCE).length);
  for (const [field, choices] of Object.entries(OPTIONS)) {
    assert.ok(choices.includes(value[field]));
  }
  assert.equal(PALETTES.eyes.roxos, "#a476ed");
});

test("presets differ and corrupted storage falls back without crashing", () => {
  assert.notDeepEqual(appearanceForPreset("neve"), appearanceForPreset("eclipse"));
  const storage = {
    saved: null,
    getItem() { return this.saved; },
    setItem(key, value) {
      assert.equal(key, APPEARANCE_STORAGE_KEY);
      this.saved = value;
    }
  };
  const preset = appearanceForPreset("neve");
  assert.equal(writeAppearance(storage, preset), true);
  assert.deepEqual(readAppearance(storage), preset);
  storage.saved = "{wrong-json";
  assert.deepEqual(readAppearance(storage), appearanceForPreset("yuna"));
  assert.deepEqual(validateAppearance([]), appearanceForPreset("yuna"));
  assert.equal(writeAppearance({setItem() { throw Error("no storage"); }}, preset), false);
  assert.deepEqual(readAppearance({getItem() { throw Error("blocked"); }}),
    appearanceForPreset("yuna"));
});

test("shared appearance ignores unknown keys and privileged data", () => {
  const result = applySharedAppearance(appearanceForPreset("yuna"), {
    hair: "branco", hair_style: "rabo", eyes: "roxos",
    outfit: "<script>", api_key: "do-not-use"
  });
  assert.equal(result.hair, "branco");
  assert.equal(result.hair_style, "rabo");
  assert.equal(result.outfit, DEFAULT_APPEARANCE.outfit);
  assert.equal(result.api_key, undefined);
});

test("original anime preview animates and disposes without WebGL or assets", () => {
  const figure = createAnimePreview(appearanceForPreset("yuna"));
  try {
    assert.equal(figure.root.name, "YunaOriginalAnimePreview");
    assert.ok(figure.root.children.length >= 6);
    assert.equal(figure.eyes.length, 2);
    const eyebrow = figure.eyes[0].eyebrow;
    const original = eyebrow.position.y;
    figure.animate(frameAt(0.2, {pose:"curious", mouthLevel:0.6}), 0.2, 0.1, 0.016);
    assert.ok(figure.mouth.scale.y > 0.018);
    assert.equal(eyebrow.position.y, original + 0.018);
    figure.animate(frameAt(0.3, {pose:"idle"}), 0, 0, 0.016);
    assert.equal(eyebrow.position.y, original);
  } finally {
    figure.dispose();
    figure.dispose();
  }
  assert.equal(figure.root.parent, null);
});

test("every hairstyle and costume creates a distinct valid rig", () => {
  for (const hair_style of OPTIONS.hair_style) {
    for (const costume of OPTIONS.costume) {
      const figure = createAnimePreview({
        ...DEFAULT_APPEARANCE, hair_style, costume, accessory: "oculos"
      });
      assert.equal(figure.appearance.hair_style, hair_style);
      assert.ok(figure.headPivot.children.length > 12);
      figure.animate(frameAt(2, {pose:"wave", reducedMotion:true}), 0, 0);
      assert.equal(figure.rightArm.rotation.z, -2.1);
      figure.dispose();
    }
  }
});
