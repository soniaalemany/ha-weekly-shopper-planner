// Lógica pura del cliente: refleja la del servidor (logic.py) para la actualización optimista.
export const slotKey = (day, meal, position) => `${day}:${meal}:${position}`;
export const parseSlotKey = (key) => {
  const [day, meal, position] = key.split(':');
  return { day: +day, meal, position: +position };
};
export const entryAt = (entries, day, meal, position) =>
  entries.find((e) => e.day === day && e.meal === meal && e.position === position);

export function compactPositions(entries) {
  const groups = new Map();
  for (const entry of entries) {
    const key = `${entry.day}:${entry.meal}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(entry);
  }
  const result = [];
  for (const group of groups.values()) {
    group.sort((a, b) => a.position - b.position);
    group.slice(0, 2).forEach((entry, position) => result.push({ ...entry, position }));
  }
  return result;
}

export function setSlot(entries, { day, meal, position, recipe_id, servings = null, selected_ingredient_ids }) {
  const existing = entryAt(entries, day, meal, position);
  const others = entries.filter((e) => e !== existing);
  if (recipe_id) {
    const keep = existing && existing.recipe_id === recipe_id ? existing.selected_ingredient_ids : [];
    others.push({
      day, meal, position, recipe_id, servings,
      selected_ingredient_ids: selected_ingredient_ids ?? [...keep],
    });
  }
  return compactPositions(others);
}

export function moveSlot(entries, source, target) {
  const copy = entries.map((e) => ({ ...e }));
  const src = entryAt(copy, source.day, source.meal, source.position);
  if (!src) return null;
  const dst = entryAt(copy, target.day, target.meal, target.position);
  Object.assign(src, { day: target.day, meal: target.meal, position: target.position });
  if (dst && dst !== src) Object.assign(dst, { day: source.day, meal: source.meal, position: source.position });
  return compactPositions(copy);
}

export function parseQuantity(text) {
  const value = text.trim();
  const match = value.match(/^(-?\d+(?:[.,]\d+)?)(?:\s+(.+))?$/);
  if (!match) return { quantity: null, unit: value || null };
  return { quantity: Number(match[1].replace(',', '.')), unit: match[2] || null };
}

export function formatQuantity(quantity, unit) {
  const q = quantity == null ? '' : String(Math.round(quantity * 100) / 100);
  return [q, unit].filter(Boolean).join(' ');
}

export const norm = (text) => text.trim().toLocaleLowerCase();
export const recipeByName = (recipes, name) => recipes.find((r) => norm(r.name) === norm(name));
export const recipeMatches = (recipes, query) => {
  const q = norm(query);
  return q ? recipes.filter((r) => norm(r.name).includes(q)) : [];
};

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[c]
  ));
}

// Un cambio remoto solo sustituye el documento local si es más nuevo.
export function isNewer(change, doc) {
  return !doc || change.revision == null || change.revision > (doc.revision ?? -1);
}
