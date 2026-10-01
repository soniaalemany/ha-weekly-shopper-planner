var A=`:host {
  display: block;
  min-height: 100%;
  background: var(--primary-background-color);
  color: var(--primary-text-color);
  font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
  --ws-accent: var(--primary-color, #39735b);
  --ws-card: var(--card-background-color, #fff);
  --ws-line: var(--divider-color, #e2e8f0);
  --ws-soft: var(--secondary-background-color, #f3f8f4);
  --ws-muted: var(--secondary-text-color, #748078);
  --ws-danger: var(--error-color, #a03f3f);
}
*, *::before, *::after { box-sizing: border-box; }
.hidden { display: none !important; }
button, input, textarea { font: inherit; color: inherit; }
button { cursor: pointer; min-height: 2.75rem; border: 0; border-radius: .75rem; padding: .6rem 1rem; font-weight: 700; }
button.small { min-height: 2.75rem; padding: .5rem .7rem; font-size: .85rem; border-radius: .6rem; }
.primary { background: var(--ws-accent); color: var(--text-primary-color, #fff); }
.secondary { background: var(--ws-soft); color: var(--ws-accent); }
.remove, .remove-recipe { background: color-mix(in srgb, var(--ws-danger) 14%, transparent); color: var(--ws-danger); }
input, textarea { width: 100%; border: 1px solid var(--ws-line); border-radius: .6rem; background: var(--ws-card); padding: .55rem; outline: none; }
input:focus, textarea:focus { border-color: var(--ws-accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ws-accent) 22%, transparent); }
label { display: grid; gap: .35rem; margin-bottom: 1rem; color: var(--ws-muted); font-size: .9rem; font-weight: 700; }
label input, label textarea { font-weight: 400; color: var(--primary-text-color); }

.wrap { max-width: 1200px; margin: 0 auto; padding: 0 1rem 2rem; }
header { display: flex; align-items: center; flex-wrap: wrap; gap: .5rem 1rem; padding: .75rem 0; }
header h1 { margin: 0; font-size: 1.25rem; font-weight: 800; flex: 1 1 auto; }
nav { display: flex; gap: .25rem; }
nav button { background: transparent; color: var(--ws-muted); min-height: 2.5rem; }
nav button[aria-current="page"] { background: var(--ws-soft); color: var(--ws-accent); }
.banner { margin: .5rem 0; padding: .75rem 1rem; border-radius: .75rem; background: var(--ws-danger); color: #fff; font-weight: 700; }
.status { min-height: 1.5rem; margin: .25rem 0 .75rem; font-size: .9rem; font-weight: 700; color: var(--ws-accent); }
.status.error { color: var(--ws-danger); }
.offline #view { pointer-events: none; opacity: .5; }
.muted { color: var(--ws-muted); }
.card { border: 1px solid var(--ws-line); border-radius: 1rem; background: var(--ws-card); padding: 1.1rem; margin-bottom: 1rem; }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; margin-bottom: 1rem; }
.week-controls input { width: auto; flex: 1 1 10rem; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: .65rem; margin-top: 1rem; }
.actions input[type=file] { width: auto; flex: 1 1 12rem; }

.week-grid { display: grid; grid-template-columns: 1fr; gap: .75rem; }
@media (min-width: 900px) { .week-grid { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1300px) { .week-grid { grid-template-columns: repeat(3, 1fr); } }
.day { border: 1px solid var(--ws-line); border-radius: 1rem; background: var(--ws-card); padding: 1rem; }
.day h2 { margin: 0 0 .5rem; font-size: .95rem; font-weight: 800; }
.date { font-size: .75rem; font-weight: 500; color: var(--ws-muted); }
.meal-group { margin-top: .85rem; }
.slot { padding: .35rem 0; border-top: 1px solid var(--ws-line); }
.slot-title { margin: 0; font-size: .7rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--ws-muted); }
.meal { display: flex; gap: .4rem; margin-top: .5rem; align-items: center; }
.meal[draggable=true] { cursor: grab; }
.slot.dragging { opacity: .45; }
.slot.drag-over { border-color: var(--ws-accent); background: var(--ws-soft); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ws-accent) 22%, transparent); }
.recipe-input-wrap { position: relative; min-width: 0; flex: 1; }
.recipe-input { padding-right: 2.6rem; }
.autocomplete { position: absolute; z-index: 10; top: calc(100% + .25rem); left: 0; right: 0; display: grid; max-height: 14rem; overflow-y: auto; border: 1px solid var(--ws-line); border-radius: .6rem; background: var(--ws-card); box-shadow: 0 8px 24px rgba(0,0,0,.2); }
.suggestion { min-height: 2.5rem; border-radius: 0; background: var(--ws-card); text-align: left; font-weight: 500; border-bottom: 1px solid var(--ws-line); }
.suggestion:hover, .suggestion:focus { background: var(--ws-soft); outline: none; }
.suggestion.create { color: var(--ws-accent); font-weight: 700; }
.ingredient-toggle { position: absolute; top: 50%; right: .4rem; transform: translateY(-50%); width: 1.9rem; min-height: 1.9rem; height: 1.9rem; padding: 0; border-radius: .5rem; background: var(--ws-soft); color: var(--ws-accent); }
.drag-handle { color: var(--ws-accent); font-size: 1.25rem; font-weight: 900; user-select: none; touch-action: none; cursor: grab; }
.drag-hint { color: var(--ws-muted); font-size: .7rem; font-weight: 700; white-space: nowrap; }
.add-optional { min-height: 1.75rem; margin-top: .35rem; padding: .2rem .6rem; }
.planner-ingredients { margin-top: .6rem; padding: .6rem; border-radius: .7rem; background: var(--ws-soft); }
.planner-ingredients label { display: flex; align-items: center; justify-content: space-between; gap: .5rem; margin: .3rem 0; font-size: .85rem; font-weight: 500; color: var(--primary-text-color); min-height: 1.75rem; }
.planner-ingredients input[type=checkbox] { width: 1.1rem; height: 1.1rem; flex: 0 0 1.1rem; accent-color: var(--ws-accent); }
.planner-ingredients small { color: var(--ws-muted); }

.shopping-row { display: grid; grid-template-columns: auto 1fr 1fr auto; align-items: center; gap: .6rem; padding: .6rem 0; border-bottom: 1px solid var(--ws-line); }
.shopping-row input[type=checkbox] { width: 1.3rem; height: 1.3rem; accent-color: var(--ws-accent); }
.shopping-row.checked .s-name, .shopping-row.checked .s-qty { color: var(--ws-muted); text-decoration: line-through; }
.new-item { border-bottom: 0; }

.card-list { display: grid; gap: .75rem; }
.recipe-card { display: flex; justify-content: space-between; gap: 1rem; border: 1px solid var(--ws-line); border-radius: 1rem; background: var(--ws-card); padding: 1.1rem; }
.recipe-card h2 { margin: 0 0 .25rem; font-size: 1.05rem; }
.recipe-card p { margin: 0 0 .6rem; color: var(--ws-muted); }
.recipe-card small { color: var(--ws-muted); }
.recipe-actions { display: flex; align-items: flex-start; gap: .5rem; }
.recipe-search-controls { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: 1rem; }
.recipe-search-controls label { margin: 0; }
.form-heading { display: flex; align-items: center; justify-content: space-between; margin: .25rem 0 .75rem; }
.ingredient-row { display: grid; grid-template-columns: 2fr 1fr 1fr auto; gap: .5rem; margin-bottom: .5rem; }

@media (max-width: 640px) {
  .recipe-card { flex-direction: column; }
  .recipe-actions button { flex: 1; }
  .recipe-search-controls { grid-template-columns: 1fr; }
  .ingredient-row { grid-template-columns: 1fr 1fr auto; }
  .ingredient-row .i-name { grid-column: 1 / -1; }
  .drag-hint { display: none; }
  .shopping-row { grid-template-columns: 2.75rem 1fr 2.75rem; }
  .shopping-row .s-qty { grid-column: 2; }
  .shopping-row button { grid-column: 3; grid-row: 1 / span 2; }
  .shopping-row input[type=checkbox] { justify-self: center; width: 1.5rem; height: 1.5rem; }
}
`;var b=class{constructor(){this.hass=null,this.clientId=crypto.randomUUID?.()??String(Math.random()).slice(2)}call(t,e={}){return this.hass.callWS({type:`weekly_shopper/${t}`,client_id:this.clientId,...e})}subscribe(t,e){return this.hass.connection.subscribeMessage(e,{type:"weekly_shopper/subscribe",week:t,client_id:this.clientId})}async upload(t){let e=new FormData;e.append("file",t,t.name);let i=await this.hass.fetchWithAuth(`/api/weekly_shopper/import?client_id=${encodeURIComponent(this.clientId)}`,{method:"POST",body:e}),s=await i.json();if(!i.ok)throw Object.assign(new Error(s.message),{code:s.code});return s}};var T=r=>r.toISOString().slice(0,10);function y(r){let t=r instanceof Date?new Date(Date.UTC(r.getFullYear(),r.getMonth(),r.getDate())):new Date(`${r}T00:00:00Z`);return t.setUTCDate(t.getUTCDate()-(t.getUTCDay()+6)%7),T(t)}function _(r,t){let e=new Date(`${r}T00:00:00Z`);return e.setUTCDate(e.getUTCDate()+t*7),T(e)}function C(r,t){let e=new Date(`${r}T00:00:00Z`);return e.setUTCDate(e.getUTCDate()+t),e.toLocaleDateString("es-ES",{day:"2-digit",month:"2-digit",timeZone:"UTC"})}var k=["Lunes","Martes","Mi\xE9rcoles","Jueves","Viernes","S\xE1bado","Domingo"],M=["comida","cena"];var N=(r,t,e)=>`${r}:${t}:${e}`,g=r=>{let[t,e,i]=r.split(":");return{day:+t,meal:e,position:+i}},u=(r,t,e,i)=>r.find(s=>s.day===t&&s.meal===e&&s.position===i);function O(r){let t=new Map;for(let i of r){let s=`${i.day}:${i.meal}`;t.has(s)||t.set(s,[]),t.get(s).push(i)}let e=[];for(let i of t.values())i.sort((s,a)=>s.position-a.position),i.slice(0,2).forEach((s,a)=>e.push({...s,position:a}));return e}function H(r,{day:t,meal:e,position:i,recipe_id:s,servings:a=null,selected_ingredient_ids:n}){let o=u(r,t,e,i),l=r.filter(d=>d!==o);if(s){let d=o&&o.recipe_id===s?o.selected_ingredient_ids:[];l.push({day:t,meal:e,position:i,recipe_id:s,servings:a,selected_ingredient_ids:n??[...d]})}return O(l)}function j(r,t,e){let i=r.map(n=>({...n})),s=u(i,t.day,t.meal,t.position);if(!s)return null;let a=u(i,e.day,e.meal,e.position);return Object.assign(s,{day:e.day,meal:e.meal,position:e.position}),a&&a!==s&&Object.assign(a,{day:t.day,meal:t.meal,position:t.position}),O(i)}function x(r){let t=r.trim(),e=t.match(/^(-?\d+(?:[.,]\d+)?)(?:\s+(.+))?$/);return e?{quantity:Number(e[1].replace(",",".")),unit:e[2]||null}:{quantity:null,unit:t||null}}function S(r,t){return[r==null?"":String(Math.round(r*100)/100),t].filter(Boolean).join(" ")}var v=r=>r.trim().toLocaleLowerCase(),B=(r,t)=>r.find(e=>v(e.name)===v(t)),$=(r,t)=>{let e=v(t);return e?r.filter(i=>v(i.name).includes(e)):[]};function c(r){return String(r??"").replace(/[&<>"']/g,t=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[t])}function L(r,t){return!t||r.revision==null||r.revision>(t.revision??-1)}function W(r,t,e){let i=new Set(t.selected_ingredient_ids),s=r.ingredients.map(a=>{let n=S(a.quantity,a.unit);return`<label><span>${c(a.name)}${n?` <small>(${c(n)})</small>`:""}</span>
      <input type="checkbox" data-ingredient="${c(a.id)}" ${i.has(a.id)?"checked":""}></label>`}).join("");return`<div class="planner-ingredients" data-slot="${e}">${s}</div>`}function U(r,t,e,i,s){let a=u(r.plan.entries,e,i,s),n=a&&r.recipes.find(w=>w.id===a.recipe_id),o=N(e,i,s),l=`${i}${s?" opcional":""} del ${k[e]}`,d=!!n,f=t.openIngredients.has(o);return`<div class="slot" data-slot="${o}">
    <div class="meal"${d?' draggable="true" title="Arrastra para mover esta receta"':""}>
      ${d?'<span class="drag-handle" aria-hidden="true">\u283F</span>':""}
      <div class="recipe-input-wrap">
        <input class="recipe-input" data-key="slot:${o}" data-slot="${o}" autocomplete="off"
          placeholder="${s?"A\xF1adir segundo plato...":"Buscar o crear plato..."}"
          value="${c(n?.name??"")}" aria-label="${c(l)}">
        ${d&&n.ingredients.length?`<button type="button" class="ingredient-toggle" data-action="toggle-ingredients" data-slot="${o}"
          aria-expanded="${f}" aria-label="Mostrar ingredientes para la compra" title="Mostrar ingredientes para la compra">\u2637</button>`:""}
        <div class="autocomplete hidden" role="listbox"></div>
      </div>
      ${d?`<span class="drag-hint">Arrastra para mover</span>
        <button type="button" class="remove-recipe small" data-action="remove-recipe" data-slot="${o}"
          aria-label="Eliminar plato" title="Eliminar plato">\u{1F5D1}</button>`:""}
    </div>
    ${d&&f?W(n,a,o):""}
  </div>`}function F(r,t){let e=k.map((i,s)=>{let a=M.map(n=>{let o=u(r.plan.entries,s,n,0),l=!!u(r.plan.entries,s,n,1)||t.openOptional.has(`${s}:${n}`);return`<section class="meal-group"><h3 class="slot-title">${n}</h3>
        ${U(r,t,s,n,0)}
        ${o&&!l?`<button type="button" class="secondary small add-optional" data-action="add-optional"
          data-day="${s}" data-meal="${n}" aria-label="A\xF1adir otro plato" title="A\xF1adir otro plato">+</button>`:""}
        ${o&&l?U(r,t,s,n,1):""}
      </section>`}).join("");return`<article class="day"><h2>${i}<br><span class="date">${C(r.week,s)}</span></h2>${a}</article>`}).join("");return`<section class="toolbar week-controls">
      <button class="secondary" data-action="prev-week" aria-label="Semana anterior">\u2190</button>
      <input class="week-picker" type="date" value="${r.week}" aria-label="Seleccionar semana (fecha de inicio)">
      <button class="secondary" data-action="next-week" aria-label="Semana siguiente">\u2192</button>
    </section>
    <section class="week-grid" aria-live="polite">${e}</section>`}function z(r){let t=r.list.items.map(e=>`
    <div class="shopping-row${e.checked?" checked":""}" data-id="${c(e.id)}">
      <input type="checkbox" data-action="check-item" ${e.checked?"checked":""} aria-label="Comprado">
      <input class="s-name" data-key="item:${c(e.id)}:name" value="${c(e.name)}" placeholder="Art\xEDculo">
      <input class="s-qty" data-key="item:${c(e.id)}:qty" value="${c(S(e.quantity,e.unit))}" placeholder="Cantidad">
      <button type="button" class="remove small" data-action="delete-item" aria-label="Eliminar art\xEDculo" title="Eliminar art\xEDculo">\u{1F5D1}</button>
    </div>`).join("");return`<section class="toolbar week-controls">
      <button class="secondary" data-action="prev-week" aria-label="Semana anterior">\u2190</button>
      <input class="week-picker" type="date" value="${r.week}" aria-label="Seleccionar semana (fecha de inicio)">
      <button class="secondary" data-action="next-week" aria-label="Semana siguiente">\u2192</button>
    </section>
    <section class="card">
      ${t||'<p class="muted">A\xFAn no hay art\xEDculos esta semana. Marca ingredientes en el men\xFA o a\xF1ade uno.</p>'}
      <div class="shopping-row new-item">
        <span></span>
        <input id="new-name" class="s-name" data-key="new-name" placeholder="Nuevo art\xEDculo" aria-label="Nuevo art\xEDculo">
        <input id="new-qty" class="s-qty" data-key="new-qty" placeholder="Cantidad" aria-label="Cantidad del nuevo art\xEDculo">
        <button type="button" class="primary small" data-action="add-item" aria-label="A\xF1adir art\xEDculo" title="A\xF1adir art\xEDculo">+</button>
      </div>
      <div class="actions"><button type="button" class="secondary" data-action="generate"
        title="Reconstruye los art\xEDculos del men\xFA; los manuales se conservan">Regenerar desde el men\xFA</button></div>
    </section>`}function P(){return`<section class="card recipe-search">
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
    <div id="recipe-list" class="card-list"></div>`}function E(r,t){let e=t.trim().toLocaleLowerCase(),i=r.filter(s=>s.name.toLocaleLowerCase().includes(e));return i.length?i.map(s=>`<article class="recipe-card" data-id="${c(s.id)}">
      <div><h2>${c(s.name)}</h2><p>${c(s.description||"Sin descripci\xF3n")}</p>
        <small>\xDAltimo uso: ${s.last_used_date?new Date(`${s.last_used_date}T00:00:00`).toLocaleDateString("es-ES"):"Nunca"}
        \xB7 Veces usada: ${s.usage_count||0}</small></div>
      <div class="recipe-actions">
        <button class="secondary" data-action="edit-recipe" aria-label="Editar receta" title="Editar receta">\u270E</button>
        <button class="remove" data-action="delete-recipe" aria-label="Eliminar receta" title="Eliminar receta">\u{1F5D1}</button>
      </div></article>`).join(""):`<p class="muted">${e?"No hay recetas que coincidan.":"A\xFAn no hay recetas. Crea la primera para empezar."}</p>`}function q(r={}){return`<div class="ingredient-row" data-id="${c(r.id??"")}">
    <input class="i-name" placeholder="Ingrediente" value="${c(r.name??"")}" required>
    <input class="i-qty" type="number" step="any" min="0" placeholder="Cantidad" value="${r.quantity??""}">
    <input class="i-unit" placeholder="Unidad" value="${c(r.unit??"")}">
    <button type="button" class="remove small" data-action="remove-ingredient" aria-label="Eliminar ingrediente" title="Eliminar ingrediente">\u{1F5D1}</button>
  </div>`}function V(r){let t=(r?.ingredients?.length?r.ingredients:[{}]).map(q).join("");return`<form class="card recipe-form" data-id="${c(r?.id??"")}">
    <label>Nombre<input class="r-name" value="${c(r?.name??"")}" required maxlength="200"></label>
    <label>Descripci\xF3n<textarea class="r-description" rows="2">${c(r?.description??"")}</textarea></label>
    <label>Raciones<input class="r-servings" type="number" min="1" step="1" value="${r?.servings??4}"></label>
    <div class="form-heading"><strong>Ingredientes</strong>
      <button type="button" class="secondary small" data-action="add-ingredient" aria-label="A\xF1adir ingrediente">+</button></div>
    <div class="ingredients">${t}</div>
    <div class="actions"><button type="submit" class="primary">Guardar</button>
      <button type="button" class="secondary" data-action="cancel-recipe">Cancelar</button></div>
  </form>`}var Y={planner:"Men\xFA",recipes:"Recetas",shopping:"Compra"},D={planner:"",recipes:"/recipes",shopping:"/shopping"},Z="/weekly-shopper",J=350,R={recipe_in_use:"La receta est\xE1 en alg\xFAn men\xFA; qu\xEDtala de \xE9l antes de eliminarla.",not_found:"No se encontr\xF3 lo que buscabas.",conflict:"Los datos cambiaron en otro dispositivo; int\xE9ntalo de nuevo."},I=class extends HTMLElement{constructor(){super(),this.api=new b,this.s={week:y(new Date),recipes:[],plan:{revision:0,entries:[]},list:{revision:0,items:[]}},this.tab="planner",this.ui={openOptional:new Set,openIngredients:new Set,recipeQuery:""},this._narrow=!1,this._pending=[],this._chain=Promise.resolve(),this._dirty=new Set,this._edits=new Map,this._timers=new Map,this._unsub=null,this._ready=!1,this._offline=!1,this._token=0,this.attachShadow({mode:"open"}),this.shadowRoot.innerHTML=`<style>${A}</style>
      <div class="wrap" id="root">
        <header><ha-menu-button></ha-menu-button><h1>Men\xFA semanal</h1><nav></nav></header>
        <div class="banner hidden" id="banner" role="alert">Sin conexi\xF3n con Home Assistant: la edici\xF3n est\xE1 bloqueada hasta reconectar.</div>
        <div class="status" id="status" role="status"></div>
        <main id="view"></main>
      </div>`,this._bind()}set hass(t){let e=!this.api.hass;this.api.hass=t;let i=this.shadowRoot.querySelector("ha-menu-button");i&&(i.hass=t),e&&this._start()}set narrow(t){this._narrow=t;let e=this.shadowRoot.querySelector("ha-menu-button");e&&(e.narrow=t)}get narrow(){return this._narrow}set route(t){let e=(t?.path||"").split("/")[1]||"",i=Object.keys(D).find(s=>D[s]===(e?`/${e}`:""))||"planner";i!==this.tab&&(this.tab=i,this._renderNav(),this._view=null,this.render())}set panel(t){}connectedCallback(){this._renderNav(),document.addEventListener("visibilitychange",this._onVisibility),window.addEventListener("pagehide",this._onVisibility),this.api.hass&&this._start()}disconnectedCallback(){this.flushEdits(),document.removeEventListener("visibilitychange",this._onVisibility),window.removeEventListener("pagehide",this._onVisibility),this._stopConnectionListeners(),this._unsub?.then?.(t=>t()).catch(()=>{}),this._unsub=null,this._started=!1}_onVisibility=()=>{document.visibilityState!=="visible"&&this.flushEdits()};async _start(){if(this._started||!this.isConnected||!this.api.hass)return;this._started=!0;let t=this.api.hass.connection;this._onReady=()=>{this._setOffline(!1),this.reloadAll()},this._onDisconnected=()=>this._setOffline(!0),t.addEventListener("ready",this._onReady),t.addEventListener("disconnected",this._onDisconnected),this._connection=t,await this._subscribe(),await this.reloadAll()}_stopConnectionListeners(){this._connection?.removeEventListener("ready",this._onReady),this._connection?.removeEventListener("disconnected",this._onDisconnected),this._connection=null}_setOffline(t){this._offline=t,this.shadowRoot.getElementById("banner").classList.toggle("hidden",!t),this.shadowRoot.getElementById("root").classList.toggle("offline",t)}async _subscribe(){let t=this._unsub;this._unsub=this.api.subscribe(this.s.week,e=>this.onChange(e));try{await this._unsub}catch{this.setStatus("No se pudo suscribir a los cambios.",!0)}t?.then?.(e=>e()).catch(()=>{})}async reloadAll(){let t=++this._token;try{let[e,i,s]=await Promise.all([this.api.call("recipes/list"),this.api.call("meal_plan/get",{week:this.s.week}),this.api.call("shopping_list/get",{week:this.s.week})]);if(t!==this._token)return;this.s.recipes=e.recipes,this.s.plan=i,this._setList(s),this._ready=!0,this.render()}catch{this.setStatus("No se pudieron cargar los datos.",!0)}}async reloadScope(t){try{t==="meal_plan"?this.s.plan=await this.api.call("meal_plan/get",{week:this.s.week}):this._setList(await this.api.call("shopping_list/get",{week:this.s.week})),this.render()}catch{}}_setList(t){this.s.list=t;for(let[e,i]of this._edits){let s=t.items.find(a=>a.id===e);s&&Object.assign(s,i)}}async changeWeek(t){this.flushEdits(),this.s.week=y(t),this.ui.openOptional.clear(),this.ui.openIngredients.clear(),this.s.plan={revision:0,entries:[]},this.s.list={revision:0,items:[]},this.render(),await this._subscribe(),await this.reloadAll()}onChange(t){if(t.scope==="recipes"){this.s.recipes=t.data,this.render();return}if(t.week!==this.s.week)return;let e=this._pending[0];if(!(t.origin===this.api.clientId&&e?.covers.includes(t.scope))){if(this._pending.some(i=>i.covers.includes(t.scope))){this._dirty.add(t.scope);return}if(t.scope==="meal_plan"){if(!L(t,this.s.plan))return;this.s.plan=t.data}else{if(!L(t,this.s.list))return;this._setList(t.data)}this.render()}}enqueue(t,e,{retry:i}={}){if(this._offline)return this.setStatus("Sin conexi\xF3n: no se puede editar.",!0),Promise.resolve();let s={covers:[t]};this._pending.push(s);let a=this._chain.then(async()=>{try{let n;try{n=await e()}catch(l){if(l?.code!=="conflict"||!i)throw l;await this.reloadScope(t);let d=i();if(!d)throw l;n=await d()}!this._pending.some(l=>l!==s&&l.covers.includes(t))&&n&&(t==="meal_plan"&&n.entries&&n.week===this.s.week&&(this.s.plan={revision:n.revision,entries:n.entries}),t==="shopping_list"&&n.items&&n.week===this.s.week&&this._setList({revision:n.revision,items:n.items}))}catch(n){this.setStatus(R[n?.code]||n?.message||"No se pudo guardar el cambio.",!0),this._dirty.add(t)}finally{this._pending.splice(this._pending.indexOf(s),1);let n=[...this._dirty].filter(o=>!this._pending.some(l=>l.covers.includes(o)));for(let o of n)this._dirty.delete(o),await this.reloadScope(o);this.render()}});return this._chain=a.catch(()=>{}),a}setStatus(t,e=!1){let i=this.shadowRoot.getElementById("status");i.textContent=t,i.classList.toggle("error",e)}_renderNav(){let t=this.shadowRoot.querySelector("nav");t.innerHTML=Object.entries(Y).map(([e,i])=>`<button data-action="tab" data-tab="${e}" ${e===this.tab?'aria-current="page"':""}>${i}</button>`).join("")}render(){if(!this._ready)return;let t=this.shadowRoot.getElementById("view");if(this.tab==="recipes"){this._view!=="recipes"&&(t.innerHTML=P(),this._view="recipes"),this.shadowRoot.getElementById("recipe-list").innerHTML=E(this.s.recipes,this.ui.recipeQuery);return}this._view=this.tab;let e=this.shadowRoot.activeElement,i=e?.dataset?.key?{key:e.dataset.key,value:e.value,start:e.selectionStart,end:e.selectionEnd}:null;t.innerHTML=this.tab==="shopping"?z(this.s):F(this.s,this.ui),i&&this._restoreFocus(i),this._focusSlot&&(this.shadowRoot.querySelector(`.recipe-input[data-slot="${this._focusSlot}"]`)?.focus(),this._focusSlot=null)}_restoreFocus({key:t,value:e,start:i,end:s}){let a=[...this.shadowRoot.querySelectorAll("[data-key]")].find(n=>n.dataset.key===t);if(a){a.value!==e&&(a.value=e),a.focus();try{a.setSelectionRange(i,s)}catch{}a.classList.contains("recipe-input")&&e!==a.defaultValue&&this._autocomplete(a)}}_bind(){let t=this.shadowRoot;t.addEventListener("click",e=>this._onClick(e)),t.addEventListener("input",e=>this._onInput(e)),t.addEventListener("change",e=>this._onChange(e)),t.addEventListener("keydown",e=>this._onKeydown(e)),t.addEventListener("focusout",e=>this._onFocusOut(e)),t.addEventListener("submit",e=>this._onSubmit(e)),t.addEventListener("dragstart",e=>this._onDragStart(e)),t.addEventListener("dragend",()=>this._clearDrag()),t.addEventListener("dragover",e=>this._onDragOver(e)),t.addEventListener("dragleave",e=>e.target.closest?.(".slot")?.classList.remove("drag-over")),t.addEventListener("drop",e=>this._onDrop(e)),t.addEventListener("pointerdown",e=>this._onPointerDown(e))}navigate(t){t!==this.tab&&(history.pushState(null,"",`${Z}${D[t]}`),window.dispatchEvent(new CustomEvent("location-changed",{detail:{replace:!1}})),this.tab=t,this._view=null,this._renderNav(),this.render())}_onClick(t){let e=t.target.closest("[data-action]");if(!e){t.target.closest(".recipe-input-wrap")||this.shadowRoot.querySelectorAll(".autocomplete").forEach(a=>a.classList.add("hidden"));return}let i=e.dataset.action,s={tab:()=>this.navigate(e.dataset.tab),"prev-week":()=>this.changeWeek(_(this.s.week,-1)),"next-week":()=>this.changeWeek(_(this.s.week,1)),"toggle-ingredients":()=>this._toggle(this.ui.openIngredients,e.dataset.slot),"add-optional":()=>{this.ui.openOptional.add(`${e.dataset.day}:${e.dataset.meal}`),this._focusSlot=`${e.dataset.day}:${e.dataset.meal}:1`,this.render()},"remove-recipe":()=>this.assign(e.dataset.slot,null),"pick-recipe":()=>this.assign(e.dataset.slot,e.dataset.recipe),"create-recipe":()=>this.createRecipeFor(e.dataset.slot,e.dataset.name),"check-item":()=>this._checkItem(e),"delete-item":()=>this._deleteItem(e),"add-item":()=>this._addItem(),generate:()=>this._generate(),"new-recipe":()=>this._openForm(null),"edit-recipe":()=>this._openForm(this.s.recipes.find(a=>a.id===e.closest(".recipe-card").dataset.id)),"delete-recipe":()=>this._deleteRecipe(e.closest(".recipe-card").dataset.id),"cancel-recipe":()=>this._closeForm(),"add-ingredient":()=>this.shadowRoot.querySelector(".ingredients").insertAdjacentHTML("beforeend",q()),"remove-ingredient":()=>e.closest(".ingredient-row").remove(),export:()=>this._export(),import:()=>this._import()}[i];s?.()}_toggle(t,e){t.has(e)?t.delete(e):t.add(e),this.render()}_onInput(t){let e=t.target;e.classList.contains("recipe-input")?this._autocomplete(e):e.classList.contains("recipe-query")?(this.ui.recipeQuery=e.value,this.shadowRoot.getElementById("recipe-list").innerHTML=E(this.s.recipes,e.value)):e.matches(".shopping-row .s-name, .shopping-row .s-qty")&&e.closest("[data-id]")&&this._editItem(e.closest(".shopping-row"))}_onChange(t){let e=t.target;if(e.classList.contains("week-picker")){e.value&&this.changeWeek(e.value);return}if(e.classList.contains("recipe-input")){setTimeout(()=>{this.shadowRoot.activeElement?.classList.contains("suggestion")||this._commitInput(e)},0);return}e.matches(".planner-ingredients input[type=checkbox]")&&this._ingredientToggled(e)}_onKeydown(t){let e=t.target;if(e.classList.contains("recipe-input")){if(t.key==="Enter")t.preventDefault(),this._commitInput(e,!0);else if(t.key==="Escape")e.parentElement.querySelector(".autocomplete").classList.add("hidden");else if(t.key==="ArrowDown"){let i=e.parentElement.querySelector(".suggestion");i&&(t.preventDefault(),i.focus())}}else e.classList.contains("suggestion")?(t.key==="ArrowDown"&&(t.preventDefault(),(e.nextElementSibling||e).focus()),t.key==="ArrowUp"&&(t.preventDefault(),(e.previousElementSibling||e.closest(".recipe-input-wrap").querySelector(".recipe-input")).focus())):t.key==="Enter"&&(e.id==="new-name"||e.id==="new-qty")&&(t.preventDefault(),this._addItem())}_onFocusOut(t){let e=t.target;e.closest?.(".shopping-row[data-id]")&&setTimeout(()=>{this.shadowRoot.activeElement?.closest?.(".shopping-row")||(this.flushEdits(),this.render())},0),e.classList?.contains("recipe-input")&&setTimeout(()=>e.parentElement?.querySelector(".autocomplete")?.classList.add("hidden"),150)}_onSubmit(t){t.preventDefault(),t.target.classList.contains("recipe-form")&&this._saveRecipe(t.target)}assign(t,e,i){let{day:s,meal:a,position:n}=g(t),o=H(this.s.plan.entries,{day:s,meal:a,position:n,recipe_id:e,selected_ingredient_ids:i});this.s.plan={...this.s.plan,entries:o},e||this.ui.openIngredients.delete(t),this.render();let l={week:this.s.week,day:s,meal:a,position:n,recipe_id:e};return i&&(l.selected_ingredient_ids=i),this.enqueue("meal_plan",()=>this.api.call("meal_plan/set_slot",l))}async createRecipeFor(t,e){try{let i=await this.api.call("recipes/create",{name:e,ingredients:[]});this.s.recipes.some(s=>s.id===i.id)||(this.s.recipes=[...this.s.recipes,i]),this.setStatus(`Receta "${i.name}" creada.`),await this.assign(t,i.id)}catch{this.setStatus("No se pudo crear la receta.",!0),this.render()}}_autocomplete(t){let e=t.parentElement.querySelector(".autocomplete"),i=t.value.trim();if(!i){e.classList.add("hidden");return}let s=t.dataset.slot,a=$(this.s.recipes,i);e.innerHTML=a.map(n=>`<button type="button" class="suggestion" role="option" data-action="pick-recipe" data-slot="${s}" data-recipe="${c(n.id)}">${c(n.name)}</button>`).join("")||`<button type="button" class="suggestion create" role="option" data-action="create-recipe" data-slot="${s}" data-name="${c(i)}">A\xF1adir "${c(i)}"</button>`,e.querySelectorAll("button").forEach(n=>n.addEventListener("mousedown",o=>o.preventDefault())),e.classList.remove("hidden")}_commitInput(t,e=!1){let i=t.dataset.slot,{day:s,meal:a,position:n}=g(i),o=u(this.s.plan.entries,s,a,n),l=t.value.trim(),d=B(this.s.recipes,l);d?d.id!==o?.recipe_id&&this.assign(i,d.id):l?e&&!$(this.s.recipes,l).length?this.createRecipeFor(i,l):e?this._autocomplete(t):this.render():o&&this.assign(i,null)}_ingredientToggled(t){let e=t.closest(".planner-ingredients"),i=[...e.querySelectorAll("input:checked")].map(l=>l.dataset.ingredient),{day:s,meal:a,position:n}=g(e.dataset.slot),o=u(this.s.plan.entries,s,a,n);o&&this.assign(e.dataset.slot,o.recipe_id,i)}_onDragStart(t){let e=t.target.closest?.('.meal[draggable="true"]');e&&(t.dataTransfer.effectAllowed="move",t.dataTransfer.setData("text/recipe-slot",e.closest(".slot").dataset.slot),e.closest(".slot").classList.add("dragging"))}_onDragOver(t){let e=t.target.closest?.(".slot");e&&Array.from(t.dataTransfer.types).includes("text/recipe-slot")&&(t.preventDefault(),e.classList.add("drag-over"),t.dataTransfer.dropEffect="move")}_onDrop(t){let e=t.target.closest?.(".slot");if(!e)return;t.preventDefault();let i=t.dataTransfer.getData("text/recipe-slot");this._clearDrag(),i&&this.move(i,e.dataset.slot)}_clearDrag(){this.shadowRoot.querySelectorAll(".slot.dragging, .slot.drag-over").forEach(t=>t.classList.remove("dragging","drag-over"))}move(t,e){if(t===e)return;let i=g(t),s=g(e),a=j(this.s.plan.entries,i,s);if(!a)return;let n=u(this.s.plan.entries,i.day,i.meal,i.position).recipe_id;this.s.plan={...this.s.plan,entries:a},this.render();let o=()=>this.api.call("meal_plan/move",{week:this.s.week,source:i,target:s,base_revision:this.s.plan.revision}),l=this.s.plan.revision;this.enqueue("meal_plan",()=>this.api.call("meal_plan/move",{week:this.s.week,source:i,target:s,base_revision:l}),{retry:()=>u(this.s.plan.entries,i.day,i.meal,i.position)?.recipe_id===n?o:null})}_onPointerDown(t){let e=t.target.closest?.(".drag-handle");if(!e||t.pointerType!=="touch")return;t.preventDefault();let i=e.closest(".slot"),s=e.closest(".meal"),a={timer:null,dragging:!1,target:null};s.draggable=!1;let n=t.pointerId;e.setPointerCapture(n),a.timer=setTimeout(()=>{a.dragging=!0,i.classList.add("dragging")},180);let o=p=>{let m=this.shadowRoot.elementsFromPoint(p.clientX,p.clientY).map(h=>h.closest(".slot")).find(h=>h&&h!==i);this.shadowRoot.querySelectorAll(".slot.drag-over").forEach(h=>{h!==m&&h.classList.remove("drag-over")}),a.target=m||null,m?.classList.add("drag-over")},l=p=>{p.pointerId===n&&a.dragging&&(p.preventDefault(),o(p))},d=(p,m)=>{if(p.pointerId!==n)return;clearTimeout(a.timer),e.removeEventListener("pointermove",l),e.removeEventListener("pointerup",f),e.removeEventListener("pointercancel",w),a.dragging&&!m&&o(p);let h=a.target;s.draggable=!0,this._clearDrag(),h&&!m&&this.move(i.dataset.slot,h.dataset.slot)},f=p=>d(p,!1),w=p=>d(p,!0);e.addEventListener("pointermove",l),e.addEventListener("pointerup",f),e.addEventListener("pointercancel",w)}_editItem(t){let e=t.dataset.id,i=this.s.list.items.find(o=>o.id===e);if(!i)return;let s=t.querySelector(".s-name").value,{quantity:a,unit:n}=x(t.querySelector(".s-qty").value);s.trim()?this._edits.set(e,{name:s.trim(),quantity:a,unit:n}):this._edits.delete(e),s.trim()&&Object.assign(i,{name:s.trim(),quantity:a,unit:n}),clearTimeout(this._timers.get(e)),this._timers.set(e,setTimeout(()=>this._flushItem(e),J))}_flushItem(t){clearTimeout(this._timers.get(t)),this._timers.delete(t);let e=this._edits.get(t);e&&(this._edits.delete(t),this.enqueue("shopping_list",()=>this.api.call("shopping_list/item/update",{week:this.s.week,item_id:t,...e})))}flushEdits(){for(let t of[...this._timers.keys()])this._flushItem(t)}_checkItem(t){let e=t.closest(".shopping-row"),i=e.dataset.id,s=this.s.list.items.find(a=>a.id===i);s&&(s.checked=t.checked),e.classList.toggle("checked",t.checked),this.enqueue("shopping_list",()=>this.api.call("shopping_list/item/update",{week:this.s.week,item_id:i,checked:t.checked}))}_deleteItem(t){let e=t.closest(".shopping-row").dataset.id;this._edits.delete(e),clearTimeout(this._timers.get(e)),this._timers.delete(e),this.s.list={...this.s.list,items:this.s.list.items.filter(i=>i.id!==e)},this.render(),this.enqueue("shopping_list",()=>this.api.call("shopping_list/item/delete",{week:this.s.week,item_id:e}))}_addItem(){let t=this.shadowRoot.getElementById("new-name"),e=this.shadowRoot.getElementById("new-qty");if(!t.value.trim()){t.focus();return}let i={week:this.s.week,name:t.value.trim(),...x(e.value)};t.value="",e.value="",t.focus(),this.enqueue("shopping_list",()=>this.api.call("shopping_list/item/add",i))}_generate(){let t=()=>this.api.call("shopping_list/generate",{week:this.s.week,base_revision:this.s.list.revision});this.enqueue("shopping_list",t,{retry:()=>t}).then(()=>this.setStatus("Lista regenerada desde el men\xFA."))}_openForm(t){let e=this.shadowRoot.getElementById("recipe-form");e.innerHTML=V(t),e.querySelector(".r-name").focus()}_closeForm(){this.shadowRoot.getElementById("recipe-form").innerHTML=""}async _saveRecipe(t){let i=[...t.querySelectorAll(".ingredient-row")].filter(a=>a.querySelector(".i-name").value.trim()).map(a=>{let n=a.querySelector(".i-qty").value;return{...a.dataset.id?{id:a.dataset.id}:{},name:a.querySelector(".i-name").value.trim(),quantity:n===""?null:Number(n),unit:a.querySelector(".i-unit").value.trim()||null}}),s={name:t.querySelector(".r-name").value.trim(),description:t.querySelector(".r-description").value.trim()||null,servings:Math.max(1,parseInt(t.querySelector(".r-servings").value,10)||4),ingredients:i};try{t.dataset.id?await this.api.call("recipes/update",{recipe_id:t.dataset.id,...s}):await this.api.call("recipes/create",s),this._closeForm(),this.setStatus("Receta guardada.")}catch(a){this.setStatus(R[a?.code]||"No se pudo guardar la receta.",!0)}}async _deleteRecipe(t){let e=this.s.recipes.find(i=>i.id===t);if(!(!e||!confirm(`\xBFEliminar ${e.name}?`)))try{await this.api.call("recipes/delete",{recipe_id:t}),this.setStatus("Receta eliminada.")}catch(i){this.setStatus(R[i?.code]||"No se pudo eliminar la receta.",!0)}}async _export(){try{let t=await this.api.call("export"),e=document.createElement("a");e.href=URL.createObjectURL(new Blob([JSON.stringify(t,null,2)],{type:"application/json"})),e.download=`weekly-shopper-planner-${new Date().toISOString().slice(0,10)}.json`,e.click(),URL.revokeObjectURL(e.href),this.setStatus("Datos exportados correctamente.")}catch{this.setStatus("No se pudieron exportar los datos.",!0)}}async _import(){let t=this.shadowRoot.querySelector(".import-file").files[0];if(!t){this.setStatus("Selecciona un archivo JSON o Markdown.",!0);return}try{let e=await this.api.upload(t);this.setStatus(`Importadas ${e.recipes} recetas, ${e.ingredients} ingredientes${e.plans!=null?`, ${e.plans} semanas y ${e.usages??0} usos`:""}${e.skipped_entries?` (${e.skipped_entries} platos sobrantes descartados)`:""}.`),await this.reloadAll()}catch(e){this.setStatus(`No se pudo importar el archivo${e.message?`: ${e.message}`:""}.`,!0)}}};customElements.define("weekly-shopper-panel",I);
