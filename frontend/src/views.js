// Plantillas HTML de cada pestaña (cadenas; el panel las pinta con innerHTML).
import { DAY_NAMES, MEALS, dayLabel } from './dates.js';
import { entryAt, escapeHtml as esc, formatQuantity, slotKey } from './logic.js';

function ingredientList(recipe, entry, key) {
  const selected = new Set(entry.selected_ingredient_ids);
  const rows = recipe.ingredients.map((ingredient) => {
    const details = formatQuantity(ingredient.quantity, ingredient.unit);
    return `<label><span>${esc(ingredient.name)}${details ? ` <small>(${esc(details)})</small>` : ''}</span>
      <input type="checkbox" data-ingredient="${esc(ingredient.id)}" ${selected.has(ingredient.id) ? 'checked' : ''}></label>`;
  }).join('');
  return `<div class="planner-ingredients" data-slot="${key}">${rows}</div>`;
}

function slotHtml(state, ui, day, meal, position) {
  const entry = entryAt(state.plan.entries, day, meal, position);
  const recipe = entry && state.recipes.find((r) => r.id === entry.recipe_id);
  const key = slotKey(day, meal, position);
  const label = `${meal}${position ? ' opcional' : ''} del ${DAY_NAMES[day]}`;
  const has = Boolean(recipe);
  const open = ui.openIngredients.has(key);
  return `<div class="slot" data-slot="${key}">
    <div class="meal"${has ? ' draggable="true" title="Arrastra para mover esta receta"' : ''}>
      ${has ? '<span class="drag-handle" aria-hidden="true">⠿</span>' : ''}
      <div class="recipe-input-wrap">
        <input class="recipe-input" data-key="slot:${key}" data-slot="${key}" autocomplete="off"
          placeholder="${position ? 'Añadir segundo plato...' : 'Buscar o crear plato...'}"
          value="${esc(recipe?.name ?? '')}" aria-label="${esc(label)}">
        ${has && recipe.ingredients.length ? `<button type="button" class="ingredient-toggle" data-action="toggle-ingredients" data-slot="${key}"
          aria-expanded="${open}" aria-label="Mostrar ingredientes para la compra" title="Mostrar ingredientes para la compra">☷</button>` : ''}
        <div class="autocomplete hidden" role="listbox"></div>
      </div>
      ${has ? `<span class="drag-hint">Arrastra para mover</span>
        <button type="button" class="remove-recipe small" data-action="remove-recipe" data-slot="${key}"
          aria-label="Eliminar plato" title="Eliminar plato">🗑</button>` : ''}
    </div>
    ${has && open ? ingredientList(recipe, entry, key) : ''}
  </div>`;
}

export function plannerHtml(state, ui) {
  const days = DAY_NAMES.map((name, day) => {
    const meals = MEALS.map((meal) => {
      const first = entryAt(state.plan.entries, day, meal, 0);
      const showSecond = Boolean(entryAt(state.plan.entries, day, meal, 1)) || ui.openOptional.has(`${day}:${meal}`);
      return `<section class="meal-group"><h3 class="slot-title">${meal}</h3>
        ${slotHtml(state, ui, day, meal, 0)}
        ${first && !showSecond ? `<button type="button" class="secondary small add-optional" data-action="add-optional"
          data-day="${day}" data-meal="${meal}" aria-label="Añadir otro plato" title="Añadir otro plato">+</button>` : ''}
        ${first && showSecond ? slotHtml(state, ui, day, meal, 1) : ''}
      </section>`;
    }).join('');
    return `<article class="day"><h2>${name}<br><span class="date">${dayLabel(state.week, day)}</span></h2>${meals}</article>`;
  }).join('');
  return `<section class="toolbar week-controls">
      <button class="secondary" data-action="prev-week" aria-label="Semana anterior">←</button>
      <input class="week-picker" type="date" value="${state.week}" aria-label="Seleccionar semana (fecha de inicio)">
      <button class="secondary" data-action="next-week" aria-label="Semana siguiente">→</button>
    </section>
    <section class="week-grid" aria-live="polite">${days}</section>`;
}

export function shoppingHtml(state) {
  const rows = state.list.items.map((item) => `
    <div class="shopping-row${item.checked ? ' checked' : ''}" data-id="${esc(item.id)}">
      <input type="checkbox" data-action="check-item" ${item.checked ? 'checked' : ''} aria-label="Comprado">
      <input class="s-name" data-key="item:${esc(item.id)}:name" value="${esc(item.name)}" placeholder="Artículo">
      <input class="s-qty" data-key="item:${esc(item.id)}:qty" value="${esc(formatQuantity(item.quantity, item.unit))}" placeholder="Cantidad">
      <button type="button" class="remove small" data-action="delete-item" aria-label="Eliminar artículo" title="Eliminar artículo">🗑</button>
    </div>`).join('');
  return `<section class="toolbar week-controls">
      <button class="secondary" data-action="prev-week" aria-label="Semana anterior">←</button>
      <input class="week-picker" type="date" value="${state.week}" aria-label="Seleccionar semana (fecha de inicio)">
      <button class="secondary" data-action="next-week" aria-label="Semana siguiente">→</button>
    </section>
    <section class="card">
      ${rows || '<p class="muted">Aún no hay artículos esta semana. Marca ingredientes en el menú o añade uno.</p>'}
      <div class="shopping-row new-item">
        <span></span>
        <input id="new-name" class="s-name" data-key="new-name" placeholder="Nuevo artículo" aria-label="Nuevo artículo">
        <input id="new-qty" class="s-qty" data-key="new-qty" placeholder="Cantidad" aria-label="Cantidad del nuevo artículo">
        <button type="button" class="primary small" data-action="add-item" aria-label="Añadir artículo" title="Añadir artículo">+</button>
      </div>
      <div class="actions"><button type="button" class="secondary" data-action="generate"
        title="Reconstruye los artículos del menú; los manuales se conservan">Regenerar desde el menú</button></div>
    </section>`;
}

export function recipesShell() {
  return `<section class="card recipe-search">
      <div class="recipe-search-controls">
        <label>Buscar receta<input class="recipe-query" type="search" placeholder="Nombre de la receta"></label>
        <button class="primary" data-action="new-recipe">Nueva receta</button>
      </div>
      <div class="actions">
        <button class="secondary" data-action="export">Exportar datos</button>
        <input type="file" class="import-file" accept=".json,.md,.markdown" aria-label="Fichero a importar">
        <button class="secondary" data-action="import">Importar</button>
      </div>
    </section>
    <div id="recipe-form"></div>
    <div id="recipe-list" class="card-list"></div>`;
}

export function recipeListHtml(recipes, query) {
  const q = query.trim().toLocaleLowerCase();
  const visible = recipes.filter((r) => r.name.toLocaleLowerCase().includes(q));
  if (!visible.length) {
    return `<p class="muted">${q ? 'No hay recetas que coincidan.' : 'Aún no hay recetas. Crea la primera para empezar.'}</p>`;
  }
  return visible.map((r) => `<article class="recipe-card" data-id="${esc(r.id)}">
      <div><h2>${esc(r.name)}</h2><p>${esc(r.description || 'Sin descripción')}</p>
        <small>Último uso: ${r.last_used_date ? new Date(`${r.last_used_date}T00:00:00`).toLocaleDateString('es-ES') : 'Nunca'}
        · Veces usada: ${r.usage_count || 0}</small></div>
      <div class="recipe-actions">
        <button class="secondary" data-action="edit-recipe" aria-label="Editar receta" title="Editar receta">✎</button>
        <button class="remove" data-action="delete-recipe" aria-label="Eliminar receta" title="Eliminar receta">🗑</button>
      </div></article>`).join('');
}

export function ingredientRowHtml(item = {}) {
  return `<div class="ingredient-row" data-id="${esc(item.id ?? '')}">
    <input class="i-name" placeholder="Ingrediente" value="${esc(item.name ?? '')}" required>
    <input class="i-qty" type="number" step="any" min="0" placeholder="Cantidad" value="${item.quantity ?? ''}">
    <input class="i-unit" placeholder="Unidad" value="${esc(item.unit ?? '')}">
    <button type="button" class="remove small" data-action="remove-ingredient" aria-label="Eliminar ingrediente" title="Eliminar ingrediente">🗑</button>
  </div>`;
}

export function recipeFormHtml(recipe) {
  const ingredients = (recipe?.ingredients?.length ? recipe.ingredients : [{}]).map(ingredientRowHtml).join('');
  return `<form class="card recipe-form" data-id="${esc(recipe?.id ?? '')}">
    <label>Nombre<input class="r-name" value="${esc(recipe?.name ?? '')}" required maxlength="200"></label>
    <label>Descripción<textarea class="r-description" rows="2">${esc(recipe?.description ?? '')}</textarea></label>
    <label>Raciones<input class="r-servings" type="number" min="1" step="1" value="${recipe?.servings ?? 4}"></label>
    <div class="form-heading"><strong>Ingredientes</strong>
      <button type="button" class="secondary small" data-action="add-ingredient" aria-label="Añadir ingrediente">+</button></div>
    <div class="ingredients">${ingredients}</div>
    <div class="actions"><button type="submit" class="primary">Guardar</button>
      <button type="button" class="secondary" data-action="cancel-recipe">Cancelar</button></div>
  </form>`;
}
