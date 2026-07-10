// Small unit helpers shared by the builders and the renderer.
//
// docx font sizes are expressed in half-points; paragraph line spacing (with
// lineRule "auto") is expressed in 240ths of a line. These keep the theme file
// readable (points / line-multiples) while emitting what docx expects.

/** points -> half-points */
export const pt = (p) => Math.round(p * 2);

/** line multiple (e.g. 1.3) -> docx line units */
export const line = (m) => Math.round(m * 240);

/** Deep-merge `over` onto `base` (objects only; arrays/scalars overwrite). */
export function deepMerge(base, over) {
  if (over === undefined || over === null) return base;
  if (typeof base !== "object" || base === null || Array.isArray(base)) return over;
  const out = { ...base };
  for (const k of Object.keys(over)) {
    const b = base[k];
    const o = over[k];
    if (o && typeof o === "object" && !Array.isArray(o) && b && typeof b === "object" && !Array.isArray(b)) {
      out[k] = deepMerge(b, o);
    } else {
      out[k] = o;
    }
  }
  return out;
}
