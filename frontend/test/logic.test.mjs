import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mondayOf, shiftWeek } from '../src/dates.js';
import {
  compactPositions, entryAt, formatQuantity, isNewer, moveSlot, parseQuantity, recipeMatches, setSlot,
} from '../src/logic.js';

const e = (day, meal, position, recipe_id, extra = {}) => ({ day, meal, position, recipe_id, servings: null, selected_ingredient_ids: [], ...extra });
const slots = (entries) => entries.map((x) => `${x.day}:${x.meal}:${x.position}=${x.recipe_id}`).sort();

test('setSlot: vaciar el primer plato asciende el segundo', () => {
  const out = setSlot([e(0, 'comida', 0, 'a'), e(0, 'comida', 1, 'b')], { day: 0, meal: 'comida', position: 0, recipe_id: null });
  assert.deepEqual(slots(out), ['0:comida:0=b']);
});

test('setSlot: conserva la selección si la receta es la misma y la borra si cambia', () => {
  const start = [e(0, 'comida', 0, 'a', { selected_ingredient_ids: ['x'] })];
  const same = setSlot(start, { day: 0, meal: 'comida', position: 0, recipe_id: 'a' });
  assert.deepEqual(same[0].selected_ingredient_ids, ['x']);
  const other = setSlot(same, { day: 0, meal: 'comida', position: 0, recipe_id: 'b' });
  assert.deepEqual(other[0].selected_ingredient_ids, []);
  const explicit = setSlot(start, { day: 0, meal: 'comida', position: 0, recipe_id: 'a', selected_ingredient_ids: ['y', 'z'] });
  assert.deepEqual(explicit[0].selected_ingredient_ids, ['y', 'z']);
});

test('moveSlot: intercambia si el destino está ocupado, mueve si está libre, null si el origen está vacío', () => {
  const swapped = moveSlot([e(0, 'comida', 0, 'a'), e(1, 'cena', 0, 'b')], { day: 0, meal: 'comida', position: 0 }, { day: 1, meal: 'cena', position: 0 });
  assert.deepEqual(slots(swapped), ['0:comida:0=b', '1:cena:0=a']);
  const moved = moveSlot([e(0, 'comida', 0, 'a')], { day: 0, meal: 'comida', position: 0 }, { day: 3, meal: 'cena', position: 0 });
  assert.deepEqual(slots(moved), ['3:cena:0=a']);
  assert.equal(moveSlot([], { day: 0, meal: 'comida', position: 0 }, { day: 1, meal: 'cena', position: 0 }), null);
});

test('moveSlot no muta la entrada', () => {
  const entries = [e(0, 'comida', 0, 'a')];
  moveSlot(entries, { day: 0, meal: 'comida', position: 0 }, { day: 2, meal: 'cena', position: 0 });
  assert.deepEqual(slots(entries), ['0:comida:0=a']);
});

test('compactPositions renumera y descarta el exceso', () => {
  const out = compactPositions([e(0, 'comida', 1, 'b'), e(0, 'comida', 5, 'c'), e(0, 'comida', 9, 'd')]);
  assert.deepEqual(slots(out), ['0:comida:0=b', '0:comida:1=c']);
  assert.equal(entryAt(out, 0, 'comida', 1).recipe_id, 'c');
});

test('parseQuantity / formatQuantity', () => {
  assert.deepEqual(parseQuantity('2 kg'), { quantity: 2, unit: 'kg' });
  assert.deepEqual(parseQuantity('1,5'), { quantity: 1.5, unit: null });
  assert.deepEqual(parseQuantity('un puñado'), { quantity: null, unit: 'un puñado' });
  assert.deepEqual(parseQuantity(''), { quantity: null, unit: null });
  assert.equal(formatQuantity(333.3333, 'g'), '333.33 g');
  assert.equal(formatQuantity(null, null), '');
});

test('recipeMatches ignora mayúsculas y vacío', () => {
  const recipes = [{ name: 'Pasta' }, { name: 'Sopa de pasta' }, { name: 'Tortilla' }];
  assert.equal(recipeMatches(recipes, 'PASTA').length, 2);
  assert.equal(recipeMatches(recipes, '  ').length, 0);
});

test('isNewer compara revisiones', () => {
  assert.equal(isNewer({ revision: 3 }, { revision: 3 }), false);
  assert.equal(isNewer({ revision: 4 }, { revision: 3 }), true);
  assert.equal(isNewer({ revision: 1 }, null), true);
});

test('semanas: lunes y desplazamiento', () => {
  assert.equal(mondayOf('2026-10-04'), '2026-09-28'); // domingo
  assert.equal(mondayOf('2026-09-28'), '2026-09-28');
  assert.equal(shiftWeek('2026-09-28', 1), '2026-10-05');
  assert.equal(shiftWeek('2026-09-28', -1), '2026-09-21');
});
