import css from './styles.css';
import { Api } from './api.js';
import { mondayOf, shiftWeek } from './dates.js';
import {
  entryAt, escapeHtml, isNewer, moveSlot, parseQuantity, parseSlotKey, recipeByName, recipeMatches, setSlot,
} from './logic.js';
import {
  ingredientRowHtml, plannerHtml, recipeFormHtml, recipeListHtml, recipesShell, shoppingHtml,
} from './views.js';

const TABS = { planner: 'Menú', recipes: 'Recetas', shopping: 'Compra' };
const PATHS = { planner: '', recipes: '/recipes', shopping: '/shopping' };
const BASE_PATH = '/weekly-shopper';
const SAVE_DEBOUNCE = 350;
const ERRORS = {
  recipe_in_use: 'La receta está en algún menú; quítala de él antes de eliminarla.',
  not_found: 'No se encontró lo que buscabas.',
  conflict: 'Los datos cambiaron en otro dispositivo; inténtalo de nuevo.',
};

class WeeklyShopperPanel extends HTMLElement {
  constructor() {
    super();
    this.api = new Api();
    this.s = { week: mondayOf(new Date()), recipes: [], plan: { revision: 0, entries: [] }, list: { revision: 0, items: [] } };
    this.tab = 'planner';
    this.ui = { openOptional: new Set(), openIngredients: new Set(), recipeQuery: '' };
    this._narrow = false;
    this._pending = [];
    this._chain = Promise.resolve();
    this._dirty = new Set();
    this._edits = new Map();
    this._timers = new Map();
    this._unsub = null;
    this._ready = false;
    this._offline = false;
    this._token = 0;
    this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = `<style>${css}</style>
      <div class="wrap" id="root">
        <header><ha-menu-button></ha-menu-button><h1>Menú semanal</h1><nav></nav></header>
        <div class="banner hidden" id="banner" role="alert">Sin conexión con Home Assistant: la edición está bloqueada hasta reconectar.</div>
        <div class="status" id="status" role="status"></div>
        <main id="view"></main>
      </div>`;
    this._bind();
  }

  // ----------------------------------------------------- propiedades de HA
  set hass(hass) {
    const first = !this.api.hass;
    this.api.hass = hass;
    const button = this.shadowRoot.querySelector('ha-menu-button');
    if (button) button.hass = hass;
    if (first) this._start();
  }

  set narrow(value) {
    this._narrow = value;
    const button = this.shadowRoot.querySelector('ha-menu-button');
    if (button) button.narrow = value;
  }

  get narrow() { return this._narrow; }

  set route(route) {
    const segment = (route?.path || '').split('/')[1] || '';
    const tab = Object.keys(PATHS).find((t) => PATHS[t] === (segment ? `/${segment}` : '')) || 'planner';
    if (tab !== this.tab) { this.tab = tab; this._renderNav(); this._view = null; this.render(); }
  }

  set panel(_) {}

  connectedCallback() {
    this._renderNav();
    document.addEventListener('visibilitychange', this._onVisibility);
    window.addEventListener('pagehide', this._onVisibility);
    if (this.api.hass) this._start();
  }

  disconnectedCallback() {
    this.flushEdits();
    document.removeEventListener('visibilitychange', this._onVisibility);
    window.removeEventListener('pagehide', this._onVisibility);
    this._stopConnectionListeners();
    this._unsub?.then?.((fn) => fn()).catch(() => {});
    this._unsub = null;
    this._started = false;
  }

  _onVisibility = () => { if (document.visibilityState !== 'visible') this.flushEdits(); };

  // ------------------------------------------------------------- arranque
  async _start() {
    if (this._started || !this.isConnected || !this.api.hass) return;
    this._started = true;
    const connection = this.api.hass.connection;
    this._onReady = () => { this._setOffline(false); this.reloadAll(); };
    this._onDisconnected = () => this._setOffline(true);
    connection.addEventListener('ready', this._onReady);
    connection.addEventListener('disconnected', this._onDisconnected);
    this._connection = connection;
    await this._subscribe();
    await this.reloadAll();
  }

  _stopConnectionListeners() {
    this._connection?.removeEventListener('ready', this._onReady);
    this._connection?.removeEventListener('disconnected', this._onDisconnected);
    this._connection = null;
  }

  _setOffline(offline) {
    this._offline = offline;
    this.shadowRoot.getElementById('banner').classList.toggle('hidden', !offline);
    this.shadowRoot.getElementById('root').classList.toggle('offline', offline);
  }

  async _subscribe() {
    const previous = this._unsub;
    this._unsub = this.api.subscribe(this.s.week, (change) => this.onChange(change));
    try { await this._unsub; } catch (err) { this.setStatus('No se pudo suscribir a los cambios.', true); }
    previous?.then?.((fn) => fn()).catch(() => {});
  }

  async reloadAll() {
    const token = ++this._token;
    try {
      const [recipes, plan, list] = await Promise.all([
        this.api.call('recipes/list'),
        this.api.call('meal_plan/get', { week: this.s.week }),
        this.api.call('shopping_list/get', { week: this.s.week }),
      ]);
      if (token !== this._token) return;
      this.s.recipes = recipes.recipes;
      this.s.plan = plan;
      this._setList(list);
      this._ready = true;
      this.render();
    } catch (err) {
      this.setStatus('No se pudieron cargar los datos.', true);
    }
  }

  async reloadScope(scope) {
    try {
      if (scope === 'meal_plan') this.s.plan = await this.api.call('meal_plan/get', { week: this.s.week });
      else this._setList(await this.api.call('shopping_list/get', { week: this.s.week }));
      this.render();
    } catch (err) { /* el siguiente evento lo corregirá */ }
  }

  _setList(list) {
    this.s.list = list;
    for (const [id, edit] of this._edits) {
      const item = list.items.find((i) => i.id === id);
      if (item) Object.assign(item, edit);
    }
  }

  async changeWeek(week) {
    this.flushEdits();
    this.s.week = mondayOf(week);
    this.ui.openOptional.clear();
    this.ui.openIngredients.clear();
    this.s.plan = { revision: 0, entries: [] };
    this.s.list = { revision: 0, items: [] };
    this.render();
    await this._subscribe();
    await this.reloadAll();
  }

  // --------------------------------------------------- cambios remotos
  onChange(change) {
    if (change.scope === 'recipes') { this.s.recipes = change.data; this.render(); return; }
    if (change.week !== this.s.week) return;
    const current = this._pending[0];
    if (change.origin === this.api.clientId && current?.covers.includes(change.scope)) return; // lo cubre la respuesta
    if (this._pending.some((op) => op.covers.includes(change.scope))) { this._dirty.add(change.scope); return; }
    if (change.scope === 'meal_plan') {
      if (!isNewer(change, this.s.plan)) return;
      this.s.plan = change.data;
    } else {
      if (!isNewer(change, this.s.list)) return;
      this._setList(change.data);
    }
    this.render();
  }

  // --------------------------------------------- operaciones en serie
  /** Encadena una operación de escritura; la respuesta solo se aplica si es la última pendiente de su ámbito. */
  enqueue(scope, run, { retry } = {}) {
    if (this._offline) { this.setStatus('Sin conexión: no se puede editar.', true); return Promise.resolve(); }
    const op = { covers: [scope] };
    this._pending.push(op);
    const task = this._chain.then(async () => {
      try {
        let result;
        try { result = await run(); } catch (err) {
          if (err?.code !== 'conflict' || !retry) throw err;
          await this.reloadScope(scope); // conflicto: recarga y reintenta una vez
          const again = retry();
          if (!again) throw err;
          result = await again();
        }
        const last = !this._pending.some((o) => o !== op && o.covers.includes(scope));
        if (last && result) {
          if (scope === 'meal_plan' && result.entries && result.week === this.s.week) this.s.plan = { revision: result.revision, entries: result.entries };
          if (scope === 'shopping_list' && result.items && result.week === this.s.week) this._setList({ revision: result.revision, items: result.items });
        }
      } catch (err) {
        this.setStatus(ERRORS[err?.code] || err?.message || 'No se pudo guardar el cambio.', true);
        this._dirty.add(scope);
      } finally {
        this._pending.splice(this._pending.indexOf(op), 1);
        const dirty = [...this._dirty].filter((s) => !this._pending.some((o) => o.covers.includes(s)));
        for (const s of dirty) { this._dirty.delete(s); await this.reloadScope(s); }
        this.render();
      }
    });
    this._chain = task.catch(() => {});
    return task;
  }

  // ------------------------------------------------------------ render
  setStatus(message, error = false) {
    const el = this.shadowRoot.getElementById('status');
    el.textContent = message;
    el.classList.toggle('error', error);
  }

  _renderNav() {
    const nav = this.shadowRoot.querySelector('nav');
    nav.innerHTML = Object.entries(TABS).map(([id, label]) =>
      `<button data-action="tab" data-tab="${id}" ${id === this.tab ? 'aria-current="page"' : ''}>${label}</button>`).join('');
  }

  render() {
    if (!this._ready) return;
    const view = this.shadowRoot.getElementById('view');
    if (this.tab === 'recipes') {
      if (this._view !== 'recipes') { view.innerHTML = recipesShell(); this._view = 'recipes'; }
      this.shadowRoot.getElementById('recipe-list').innerHTML = recipeListHtml(this.s.recipes, this.ui.recipeQuery);
      return;
    }
    this._view = this.tab;
    const active = this.shadowRoot.activeElement;
    const snapshot = active?.dataset?.key
      ? { key: active.dataset.key, value: active.value, start: active.selectionStart, end: active.selectionEnd } : null;
    view.innerHTML = this.tab === 'shopping' ? shoppingHtml(this.s) : plannerHtml(this.s, this.ui);
    if (snapshot) this._restoreFocus(snapshot);
    if (this._focusSlot) {
      this.shadowRoot.querySelector(`.recipe-input[data-slot="${this._focusSlot}"]`)?.focus();
      this._focusSlot = null;
    }
  }

  _restoreFocus({ key, value, start, end }) {
    const el = [...this.shadowRoot.querySelectorAll('[data-key]')].find((e) => e.dataset.key === key);
    if (!el) return;
    if (el.value !== value) el.value = value; // texto aún sin enviar: no se pisa
    el.focus();
    try { el.setSelectionRange(start, end); } catch (err) { /* type=date, etc. */ }
    if (el.classList.contains('recipe-input') && value !== el.defaultValue) this._autocomplete(el);
  }

  // ------------------------------------------------------------ eventos
  _bind() {
    const root = this.shadowRoot;
    root.addEventListener('click', (e) => this._onClick(e));
    root.addEventListener('input', (e) => this._onInput(e));
    root.addEventListener('change', (e) => this._onChange(e));
    root.addEventListener('keydown', (e) => this._onKeydown(e));
    root.addEventListener('focusout', (e) => this._onFocusOut(e));
    root.addEventListener('submit', (e) => this._onSubmit(e));
    root.addEventListener('dragstart', (e) => this._onDragStart(e));
    root.addEventListener('dragend', () => this._clearDrag());
    root.addEventListener('dragover', (e) => this._onDragOver(e));
    root.addEventListener('dragleave', (e) => e.target.closest?.('.slot')?.classList.remove('drag-over'));
    root.addEventListener('drop', (e) => this._onDrop(e));
    root.addEventListener('pointerdown', (e) => this._onPointerDown(e));
  }

  navigate(tab) {
    if (tab === this.tab) return;
    history.pushState(null, '', `${BASE_PATH}${PATHS[tab]}`);
    window.dispatchEvent(new CustomEvent('location-changed', { detail: { replace: false } }));
    this.tab = tab; this._view = null; this._renderNav(); this.render();
  }

  _onClick(event) {
    const target = event.target.closest('[data-action]');
    if (!target) {
      if (!event.target.closest('.recipe-input-wrap')) this.shadowRoot.querySelectorAll('.autocomplete').forEach((a) => a.classList.add('hidden'));
      return;
    }
    const action = target.dataset.action;
    const handler = {
      tab: () => this.navigate(target.dataset.tab),
      'prev-week': () => this.changeWeek(shiftWeek(this.s.week, -1)),
      'next-week': () => this.changeWeek(shiftWeek(this.s.week, 1)),
      'toggle-ingredients': () => this._toggle(this.ui.openIngredients, target.dataset.slot),
      'add-optional': () => {
        this.ui.openOptional.add(`${target.dataset.day}:${target.dataset.meal}`);
        this._focusSlot = `${target.dataset.day}:${target.dataset.meal}:1`;
        this.render();
      },
      'remove-recipe': () => this.assign(target.dataset.slot, null),
      'pick-recipe': () => this.assign(target.dataset.slot, target.dataset.recipe),
      'create-recipe': () => this.createRecipeFor(target.dataset.slot, target.dataset.name),
      'check-item': () => this._checkItem(target),
      'delete-item': () => this._deleteItem(target),
      'add-item': () => this._addItem(),
      generate: () => this._generate(),
      'new-recipe': () => this._openForm(null),
      'edit-recipe': () => this._openForm(this.s.recipes.find((r) => r.id === target.closest('.recipe-card').dataset.id)),
      'delete-recipe': () => this._deleteRecipe(target.closest('.recipe-card').dataset.id),
      'cancel-recipe': () => this._closeForm(),
      'add-ingredient': () => this.shadowRoot.querySelector('.ingredients').insertAdjacentHTML('beforeend', ingredientRowHtml()),
      'remove-ingredient': () => target.closest('.ingredient-row').remove(),
      export: () => this._export(),
      import: () => this._import(),
    }[action];
    handler?.();
  }

  _toggle(set, key) {
    if (set.has(key)) set.delete(key); else set.add(key);
    this.render();
  }

  _onInput(event) {
    const el = event.target;
    if (el.classList.contains('recipe-input')) this._autocomplete(el);
    else if (el.classList.contains('recipe-query')) {
      this.ui.recipeQuery = el.value;
      this.shadowRoot.getElementById('recipe-list').innerHTML = recipeListHtml(this.s.recipes, el.value);
    } else if (el.matches('.shopping-row .s-name, .shopping-row .s-qty') && el.closest('[data-id]')) {
      this._editItem(el.closest('.shopping-row'));
    }
  }

  _onChange(event) {
    const el = event.target;
    if (el.classList.contains('week-picker')) { if (el.value) this.changeWeek(el.value); return; }
    if (el.classList.contains('recipe-input')) {
      // si el foco pasa a una sugerencia no se descarta el texto
      setTimeout(() => {
        if (!this.shadowRoot.activeElement?.classList.contains('suggestion')) this._commitInput(el);
      }, 0);
      return;
    }
    if (el.matches('.planner-ingredients input[type=checkbox]')) this._ingredientToggled(el);
  }

  _onKeydown(event) {
    const el = event.target;
    if (el.classList.contains('recipe-input')) {
      if (event.key === 'Enter') {
        event.preventDefault();
        this._commitInput(el, true);
      } else if (event.key === 'Escape') {
        el.parentElement.querySelector('.autocomplete').classList.add('hidden');
      } else if (event.key === 'ArrowDown') {
        const first = el.parentElement.querySelector('.suggestion');
        if (first) { event.preventDefault(); first.focus(); }
      }
    } else if (el.classList.contains('suggestion')) {
      if (event.key === 'ArrowDown') { event.preventDefault(); (el.nextElementSibling || el).focus(); }
      if (event.key === 'ArrowUp') { event.preventDefault(); (el.previousElementSibling || el.closest('.recipe-input-wrap').querySelector('.recipe-input')).focus(); }
    } else if (event.key === 'Enter' && (el.id === 'new-name' || el.id === 'new-qty')) {
      event.preventDefault();
      this._addItem();
    }
  }

  _onFocusOut(event) {
    const el = event.target;
    if (el.closest?.('.shopping-row[data-id]')) {
      // al salir de la fila se envía lo pendiente y se restaura lo que el servidor haya dejado
      setTimeout(() => {
        if (!this.shadowRoot.activeElement?.closest?.('.shopping-row')) { this.flushEdits(); this.render(); }
      }, 0);
    }
    if (el.classList?.contains('recipe-input')) {
      setTimeout(() => el.parentElement?.querySelector('.autocomplete')?.classList.add('hidden'), 150);
    }
  }

  _onSubmit(event) {
    event.preventDefault();
    if (event.target.classList.contains('recipe-form')) this._saveRecipe(event.target);
  }

  // ---------------------------------------------------------- planificador
  assign(slotKey, recipeId, selected) {
    const { day, meal, position } = parseSlotKey(slotKey);
    const entries = setSlot(this.s.plan.entries, { day, meal, position, recipe_id: recipeId, selected_ingredient_ids: selected });
    this.s.plan = { ...this.s.plan, entries };
    if (!recipeId) this.ui.openIngredients.delete(slotKey);
    this.render();
    const payload = { week: this.s.week, day, meal, position, recipe_id: recipeId };
    if (selected) payload.selected_ingredient_ids = selected;
    return this.enqueue('meal_plan', () => this.api.call('meal_plan/set_slot', payload));
  }

  async createRecipeFor(slotKey, name) {
    try {
      const recipe = await this.api.call('recipes/create', { name, ingredients: [] });
      if (!this.s.recipes.some((r) => r.id === recipe.id)) this.s.recipes = [...this.s.recipes, recipe];
      this.setStatus(`Receta "${recipe.name}" creada.`);
      await this.assign(slotKey, recipe.id);
    } catch (err) {
      this.setStatus('No se pudo crear la receta.', true);
      this.render();
    }
  }

  _autocomplete(input) {
    const box = input.parentElement.querySelector('.autocomplete');
    const query = input.value.trim();
    if (!query) { box.classList.add('hidden'); return; }
    const slot = input.dataset.slot;
    const matches = recipeMatches(this.s.recipes, query);
    box.innerHTML = matches.map((r) =>
      `<button type="button" class="suggestion" role="option" data-action="pick-recipe" data-slot="${slot}" data-recipe="${escapeHtml(r.id)}">${escapeHtml(r.name)}</button>`).join('')
      || `<button type="button" class="suggestion create" role="option" data-action="create-recipe" data-slot="${slot}" data-name="${escapeHtml(query)}">Añadir "${escapeHtml(query)}"</button>`;
    // mousedown no debe quitar el foco al input antes del click
    box.querySelectorAll('button').forEach((b) => b.addEventListener('mousedown', (e) => e.preventDefault()));
    box.classList.remove('hidden');
  }

  _commitInput(input, fromEnter = false) {
    const slot = input.dataset.slot;
    const { day, meal, position } = parseSlotKey(slot);
    const current = entryAt(this.s.plan.entries, day, meal, position);
    const text = input.value.trim();
    const recipe = recipeByName(this.s.recipes, text);
    if (recipe) { if (recipe.id !== current?.recipe_id) this.assign(slot, recipe.id); }
    else if (!text) { if (current) this.assign(slot, null); }
    else if (fromEnter && !recipeMatches(this.s.recipes, text).length) this.createRecipeFor(slot, text);
    else if (fromEnter) this._autocomplete(input);
    else this.render(); // texto que no corresponde a ninguna receta: se descarta
  }

  _ingredientToggled(checkbox) {
    const box = checkbox.closest('.planner-ingredients');
    const selected = [...box.querySelectorAll('input:checked')].map((c) => c.dataset.ingredient);
    const { day, meal, position } = parseSlotKey(box.dataset.slot);
    const entry = entryAt(this.s.plan.entries, day, meal, position);
    if (entry) this.assign(box.dataset.slot, entry.recipe_id, selected);
  }

  // --------------------------------------------------------- arrastrar
  _onDragStart(event) {
    const meal = event.target.closest?.('.meal[draggable="true"]');
    if (!meal) return;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/recipe-slot', meal.closest('.slot').dataset.slot);
    meal.closest('.slot').classList.add('dragging');
  }

  _onDragOver(event) {
    const slot = event.target.closest?.('.slot');
    if (slot && Array.from(event.dataTransfer.types).includes('text/recipe-slot')) {
      event.preventDefault();
      slot.classList.add('drag-over');
      event.dataTransfer.dropEffect = 'move';
    }
  }

  _onDrop(event) {
    const slot = event.target.closest?.('.slot');
    if (!slot) return;
    event.preventDefault();
    const source = event.dataTransfer.getData('text/recipe-slot');
    this._clearDrag();
    if (source) this.move(source, slot.dataset.slot);
  }

  _clearDrag() {
    this.shadowRoot.querySelectorAll('.slot.dragging, .slot.drag-over').forEach((s) => s.classList.remove('dragging', 'drag-over'));
  }

  move(sourceKey, targetKey) {
    if (sourceKey === targetKey) return;
    const source = parseSlotKey(sourceKey);
    const target = parseSlotKey(targetKey);
    const entries = moveSlot(this.s.plan.entries, source, target);
    if (!entries) return;
    const moved = entryAt(this.s.plan.entries, source.day, source.meal, source.position).recipe_id;
    this.s.plan = { ...this.s.plan, entries };
    this.render();
    const send = () => this.api.call('meal_plan/move', {
      week: this.s.week, source, target, base_revision: this.s.plan.revision,
    });
    const revision = this.s.plan.revision;
    this.enqueue('meal_plan', () => this.api.call('meal_plan/move', { week: this.s.week, source, target, base_revision: revision }), {
      // tras recargar, reintenta solo si el origen sigue siendo la misma receta
      retry: () => (entryAt(this.s.plan.entries, source.day, source.meal, source.position)?.recipe_id === moved ? send : null),
    });
  }

  _onPointerDown(event) {
    const handle = event.target.closest?.('.drag-handle');
    if (!handle || event.pointerType !== 'touch') return;
    event.preventDefault();
    const slot = handle.closest('.slot');
    const meal = handle.closest('.meal');
    const state = { timer: null, dragging: false, target: null };
    meal.draggable = false; // evita el arrastre nativo del navegador mientras dura el gesto táctil
    const pointerId = event.pointerId;
    handle.setPointerCapture(pointerId);
    state.timer = setTimeout(() => { state.dragging = true; slot.classList.add('dragging'); }, 180);
    const over = (e) => {
      const target = this.shadowRoot.elementsFromPoint(e.clientX, e.clientY)
        .map((el) => el.closest('.slot')).find((s) => s && s !== slot);
      this.shadowRoot.querySelectorAll('.slot.drag-over').forEach((s) => { if (s !== target) s.classList.remove('drag-over'); });
      state.target = target || null;
      target?.classList.add('drag-over');
    };
    const onMove = (e) => { if (e.pointerId === pointerId && state.dragging) { e.preventDefault(); over(e); } };
    const finish = (e, cancelled) => {
      if (e.pointerId !== pointerId) return;
      clearTimeout(state.timer);
      handle.removeEventListener('pointermove', onMove);
      handle.removeEventListener('pointerup', onUp);
      handle.removeEventListener('pointercancel', onCancel);
      if (state.dragging && !cancelled) over(e);
      const target = state.target;
      meal.draggable = true;
      this._clearDrag();
      if (target && !cancelled) this.move(slot.dataset.slot, target.dataset.slot);
    };
    const onUp = (e) => finish(e, false);
    const onCancel = (e) => finish(e, true);
    handle.addEventListener('pointermove', onMove);
    handle.addEventListener('pointerup', onUp);
    handle.addEventListener('pointercancel', onCancel);
  }

  // ----------------------------------------------------------------- compra
  _editItem(row) {
    const id = row.dataset.id;
    const item = this.s.list.items.find((i) => i.id === id);
    if (!item) return;
    const name = row.querySelector('.s-name').value;
    const { quantity, unit } = parseQuantity(row.querySelector('.s-qty').value);
    if (name.trim()) this._edits.set(id, { name: name.trim(), quantity, unit });
    else this._edits.delete(id);
    if (name.trim()) Object.assign(item, { name: name.trim(), quantity, unit });
    clearTimeout(this._timers.get(id));
    this._timers.set(id, setTimeout(() => this._flushItem(id), SAVE_DEBOUNCE));
  }

  _flushItem(id) {
    clearTimeout(this._timers.get(id));
    this._timers.delete(id);
    const edit = this._edits.get(id);
    if (!edit) return;
    this._edits.delete(id);
    this.enqueue('shopping_list', () => this.api.call('shopping_list/item/update', { week: this.s.week, item_id: id, ...edit }));
  }

  flushEdits() { for (const id of [...this._timers.keys()]) this._flushItem(id); }

  _checkItem(box) {
    const row = box.closest('.shopping-row');
    const id = row.dataset.id;
    const item = this.s.list.items.find((i) => i.id === id);
    if (item) item.checked = box.checked;
    row.classList.toggle('checked', box.checked);
    this.enqueue('shopping_list', () => this.api.call('shopping_list/item/update', { week: this.s.week, item_id: id, checked: box.checked }));
  }

  _deleteItem(button) {
    const id = button.closest('.shopping-row').dataset.id;
    this._edits.delete(id);
    clearTimeout(this._timers.get(id));
    this._timers.delete(id);
    this.s.list = { ...this.s.list, items: this.s.list.items.filter((i) => i.id !== id) };
    this.render();
    this.enqueue('shopping_list', () => this.api.call('shopping_list/item/delete', { week: this.s.week, item_id: id }));
  }

  _addItem() {
    const name = this.shadowRoot.getElementById('new-name');
    const qty = this.shadowRoot.getElementById('new-qty');
    if (!name.value.trim()) { name.focus(); return; }
    const payload = { week: this.s.week, name: name.value.trim(), ...parseQuantity(qty.value) };
    name.value = ''; qty.value = '';
    name.focus();
    this.enqueue('shopping_list', () => this.api.call('shopping_list/item/add', payload));
  }

  _generate() {
    const send = () => this.api.call('shopping_list/generate', { week: this.s.week, base_revision: this.s.list.revision });
    this.enqueue('shopping_list', send, { retry: () => send }).then(() => this.setStatus('Lista regenerada desde el menú.'));
  }

  // ----------------------------------------------------------------- recetas
  _openForm(recipe) {
    const holder = this.shadowRoot.getElementById('recipe-form');
    holder.innerHTML = recipeFormHtml(recipe);
    holder.querySelector('.r-name').focus();
  }

  _closeForm() {
    this.shadowRoot.getElementById('recipe-form').innerHTML = '';
  }

  async _saveRecipe(form) {
    const rows = [...form.querySelectorAll('.ingredient-row')].filter((r) => r.querySelector('.i-name').value.trim());
    const ingredients = rows.map((r) => {
      const qty = r.querySelector('.i-qty').value;
      return {
        ...(r.dataset.id ? { id: r.dataset.id } : {}),
        name: r.querySelector('.i-name').value.trim(),
        quantity: qty === '' ? null : Number(qty),
        unit: r.querySelector('.i-unit').value.trim() || null,
      };
    });
    const body = {
      name: form.querySelector('.r-name').value.trim(),
      description: form.querySelector('.r-description').value.trim() || null,
      servings: Math.max(1, parseInt(form.querySelector('.r-servings').value, 10) || 4),
      ingredients,
    };
    try {
      if (form.dataset.id) await this.api.call('recipes/update', { recipe_id: form.dataset.id, ...body });
      else await this.api.call('recipes/create', body);
      this._closeForm();
      this.setStatus('Receta guardada.');
    } catch (err) {
      this.setStatus(ERRORS[err?.code] || 'No se pudo guardar la receta.', true);
    }
  }

  async _deleteRecipe(id) {
    const recipe = this.s.recipes.find((r) => r.id === id);
    if (!recipe || !confirm(`¿Eliminar ${recipe.name}?`)) return;
    try { await this.api.call('recipes/delete', { recipe_id: id }); this.setStatus('Receta eliminada.'); }
    catch (err) { this.setStatus(ERRORS[err?.code] || 'No se pudo eliminar la receta.', true); }
  }

  async _export() {
    try {
      const data = await this.api.call('export');
      const link = document.createElement('a');
      link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
      link.download = `weekly-shopper-planner-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
      this.setStatus('Datos exportados correctamente.');
    } catch (err) { this.setStatus('No se pudieron exportar los datos.', true); }
  }

  async _import() {
    const file = this.shadowRoot.querySelector('.import-file').files[0];
    if (!file) { this.setStatus('Selecciona un archivo JSON o Markdown.', true); return; }
    try {
      const r = await this.api.upload(file);
      this.setStatus(`Importadas ${r.recipes} recetas, ${r.ingredients} ingredientes${r.plans != null ? `, ${r.plans} semanas y ${r.usages ?? 0} usos` : ''}${r.skipped_entries ? ` (${r.skipped_entries} platos sobrantes descartados)` : ''}.`);
      await this.reloadAll();
    } catch (err) { this.setStatus(`No se pudo importar el archivo${err.message ? `: ${err.message}` : ''}.`, true); }
  }
}

customElements.define('weekly-shopper-panel', WeeklyShopperPanel);
