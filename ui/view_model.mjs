export const DETAIL_MODES = [
  "HP",
  "hierarchy",
  ...Array.from({ length: 16 }, (_, bit) => `latent bit ${bit}`),
  "activity",
  "bond/contact",
];

export function clampByte(value) {
  return Math.max(0, Math.min(255, Number(value) || 0));
}

export function hierarchyLevel(structure) {
  const value = Number(structure) || 0;
  for (let level = 7; level >= 0; level -= 1) {
    if (((value >> (level * 2)) & 0b11) !== 0) return level;
  }
  return 0;
}

export function activityValue(item) {
  if (item.activity !== undefined) return clampByte(item.activity);
  return clampByte((Number(item.bond) || 0) + ((Number(item.latent) || 0).toString(2).replaceAll("0", "").length * 16));
}

export function modeValue(item = {}, selectedMode = "HP") {
  if (selectedMode === "hierarchy") return Number(item.hierarchy ?? hierarchyLevel(item.structure));
  if (selectedMode === "activity") return activityValue(item);
  if (selectedMode === "bond/contact") return clampByte(item.bond);
  const latentMatch = /^latent bit (\d+)$/.exec(selectedMode);
  if (latentMatch) return ((Number(item.latent) || 0) >> Number(latentMatch[1])) & 1;
  if (selectedMode === "latent bit") return Number(item.latent) & 1;
  return clampByte(item.hp);
}

export function overviewColor(cell = {}) {
  const activity = clampByte(cell.activity);
  const hierarchy = Math.max(0, Math.min(7, Number(cell.hierarchy) || 0));
  const hue = 210 - hierarchy * 20;
  const lightness = 12 + (activity / 255) * 58;
  return `hsl(${hue} 80% ${lightness}%)`;
}

export function detailColor(item = {}, selectedMode = "HP") {
  const value = modeValue(item, selectedMode);
  const bond = clampByte(item.bond);
  if (selectedMode === "hierarchy") {
    const level = Math.max(0, Math.min(7, Number(item.hierarchy ?? hierarchyLevel(item.structure))));
    return `hsl(${240 - level * 24} 80% ${Math.max(22, 32 + (bond / 255) * 38)}%)`;
  }
  if (selectedMode.startsWith("latent bit")) {
    return `hsl(${value ? 280 : 0} 80% ${value ? 58 : 12}%)`;
  }
  if (selectedMode === "activity") {
    return `hsl(190 80% ${Math.max(22, 22 + (value / 255) * 50)}%)`;
  }
  if (selectedMode === "bond/contact") {
    return `hsl(165 80% ${Math.max(22, 22 + (value / 255) * 50)}%)`;
  }
  const hue = value > 170 ? 210 : value > 60 ? 140 : 0;
  const lightness = Math.max(22, 25 + (value / 255) * 42 + (bond / 255) * 15);
  return `hsl(${hue} 80% ${lightness}%)`;
}
