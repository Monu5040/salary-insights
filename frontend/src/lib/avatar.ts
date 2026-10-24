/** Pale background and dark text pairs, each 6.3:1 or more. */
const PALETTE = [
  ["#e0e7ff", "#3730a3"], // indigo
  ["#e0f2fe", "#075985"], // sky
  ["#d1fae5", "#065f46"], // emerald
  ["#fef3c7", "#92400e"], // amber
  ["#ffe4e6", "#9f1239"], // rose
  ["#ede9fe", "#5b21b6"], // violet
  ["#ccfbf1", "#115e59"], // teal
  ["#e2e8f0", "#334155"], // slate
] as const;

/** "Asha Rao" → "AR": the first letters of the first and last names. */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const ends = words.length > 1 ? [words[0], words[words.length - 1]] : words;
  return ends.map((word) => [...word][0]).join("").toLocaleUpperCase();
}

/** The same colours for the same name, wherever it appears. */
export function avatarColours(name: string): readonly [string, string] {
  let hash = 0;
  for (const letter of name) hash = (hash * 31 + letter.codePointAt(0)!) >>> 0;
  return PALETTE[hash % PALETTE.length];
}
