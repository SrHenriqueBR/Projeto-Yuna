/** Identidade visual original do avatar 3D de prévia.
 * É somente aparência: não concede permissões e não modifica um VRM importado.
 * Opções alinhadas ao avatar 2D sem depender do Python ou de dados privados.
 */
export const PALETTES = Object.freeze({
  hair: Object.freeze({
    preto: "#241630", branco: "#ede7f8", ruivo: "#c45e50", roxo: "#7553a4"
  }),
  eyes: Object.freeze({
    vermelhos: "#db5e79", azuis: "#62b6ee",
    dourados: "#e8b65e", roxos: "#a476ed"
  }),
  outfit: Object.freeze({escura: "#392849", clara: "#b4a4d2"})
});

export const OPTIONS = Object.freeze({
  hair: Object.keys(PALETTES.hair),
  eyes: Object.keys(PALETTES.eyes),
  outfit: Object.keys(PALETTES.outfit),
  hair_style: ["longo", "curto", "marias", "rabo"],
  costume: ["vestido", "casual", "casaco"],
  accessory: ["laco", "tiara", "oculos", "nenhum"]
});

export const DEFAULT_APPEARANCE = Object.freeze({
  hair: "preto",
  eyes: "roxos",
  outfit: "escura",
  hair_style: "longo",
  costume: "vestido",
  accessory: "laco"
});

export const PRESETS = Object.freeze({
  yuna: Object.freeze({...DEFAULT_APPEARANCE}),
  neve: Object.freeze({
    hair: "branco", eyes: "azuis", outfit: "clara",
    hair_style: "longo", costume: "casaco", accessory: "tiara"
  }),
  eclipse: Object.freeze({
    hair: "roxo", eyes: "vermelhos", outfit: "escura",
    hair_style: "rabo", costume: "casual", accessory: "oculos"
  })
});

export function validateAppearance(raw) {
  const source = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  const safe = {};
  for (const [key, choices] of Object.entries(OPTIONS)) {
    const choice = source[key];
    safe[key] = typeof choice === "string" && choices.includes(choice)
      ? choice : DEFAULT_APPEARANCE[key];
  }
  return safe;
}

export function appearanceForPreset(preset) {
  return validateAppearance(PRESETS[preset] || PRESETS.yuna);
}

export const APPEARANCE_STORAGE_KEY = "yuna-avatar3d-preview-v1";
export function readAppearance(storage) {
  try {
    const raw = storage?.getItem(APPEARANCE_STORAGE_KEY);
    if (typeof raw !== "string" || raw.length > 1200) {
      return appearanceForPreset("yuna");
    }
    return validateAppearance(JSON.parse(raw));
  } catch {
    return appearanceForPreset("yuna");
  }
}

export function writeAppearance(storage, appearance) {
  const safe = validateAppearance(appearance);
  try {
    storage?.setItem(APPEARANCE_STORAGE_KEY, JSON.stringify(safe));
    return true;
  } catch {
    return false;
  }
}

/** Resolve opt-in visuals shared by Python's 2D avatar when available.
 * Only supported enum fields may cross the renderer boundary.
 */
export function applySharedAppearance(current, incoming) {
  return validateAppearance({...validateAppearance(current), ...(
    incoming && typeof incoming === "object" && !Array.isArray(incoming)
      ? Object.fromEntries(Object.entries(incoming).filter(([key, value]) =>
          key in OPTIONS && typeof value === "string" && OPTIONS[key].includes(value)))
      : {}
  )});
}
