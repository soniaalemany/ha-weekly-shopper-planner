# Plan: Weekly Shopper Planner como integración de Home Assistant (HACS)

Objetivo: convertir `weekly-shopper-planner` (FastAPI + SQLite + HTML/JS vanilla, servido en el puerto 9009) en una **integración personalizada** (`custom_components`) instalable desde **HACS**, con su propio panel en la barra lateral de Home Assistant, sincronización en tiempo real entre dispositivos y entidades nativas (lista de la compra como entidad `todo`).

Fecha del plan: 2026-10-01 · Revisión 2: se elimina SQLAlchemy y se añade sincronización en tiempo real.

---

## 1. Decisiones de arquitectura

| Tema | Hoy | En Home Assistant | Motivo |
|---|---|---|---|
| Tipo de paquete | Web independiente / Docker | **Integración** en `custom_components/weekly_shopper` | HACS instala integraciones; los add-ons no se distribuyen por HACS y requieren HA OS/Supervised. |
| Comunicación panel ↔ backend | REST (FastAPI) | **API WebSocket de HA** (`websocket_api.async_register_command`) + una única vista HTTP para subir ficheros de importación | Va por la conexión que el frontend de HA ya tiene abierta y autenticada, y permite **suscripciones** para enviar cambios en tiempo real. |
| Validación | Pydantic (`schemas.py`) | **voluptuous** (esquemas de los comandos WS) | Es lo que usa HA; cero dependencias externas. |
| Persistencia | SQLAlchemy + SQLite | **`homeassistant.helpers.storage.Store`** (JSON en `/config/.storage/`) con modelo en memoria | Sin dependencias externas (`"requirements": []`), migraciones de esquema integradas, escrituras atómicas, incluido en los backups de HA. Elimina el riesgo de incompatibilidad con la versión de SQLAlchemy de HA. |
| Concurrencia | Peticiones HTTP independientes | Todas las mutaciones ocurren en el **event loop** de HA sobre datos en memoria | Al ser un único hilo, cada operación es atómica sin locks. |
| Frontend | 3 páginas HTML servidas en `/` | **Panel personalizado** (web component) registrado con `panel_custom`, con pestañas Menú / Recetas / Compra | El panel recibe el objeto `hass` → `hass.callWS()` y `hass.connection.subscribeMessage()` con la autenticación ya resuelta. |
| Estilos | Tailwind por CDN | **Tailwind compilado** e inyectado en el Shadow DOM | El CDN no funciona bien dentro de Shadow DOM y era una limitación conocida para producción. |
| Integración con HA | — | Entidad **`todo.lista_de_la_compra`**, sensores de comida/cena de hoy, servicios | Uso desde la app móvil de HA, Assist (voz) y automatizaciones. |

---

## 2. Persistencia sin SQLAlchemy

### 2.1 Almacenes

Un `Store` por colección, para que guardar una lista de la compra no reescriba todas las recetas:

| Store (`/config/.storage/…`) | Contenido |
|---|---|
| `weekly_shopper.recipes` | Recetas con `id` (UUID, el actual `external_id`), nombre, raciones, ingredientes (`id`, nombre, cantidad, unidad, categoría). |
| `weekly_shopper.meal_plans` | `{ "<lunes ISO>": { "revision": n, "entries": [{day, meal, position, recipe_id, servings, selected_ingredient_ids}] } }` |
| `weekly_shopper.shopping_lists` | `{ "<lunes ISO>": { "revision": n, "items": [{id, name, quantity, unit, category, checked, source}] } }` |
| `weekly_shopper.history` | Historial de uso de recetas. |

- Todos los identificadores pasan a ser **UUID** (se acaban los IDs autoincrementales de SQLite). El formato de exportación nativo v1 ya usa UUID para las recetas, así que la importación sigue siendo compatible.
- Cada documento (menú semanal, lista semanal) lleva un contador **`revision`** que se incrementa en cada cambio (ver §3.3).

### 2.2 Capa de datos

- `models.py`: `dataclass`es (`Recipe`, `Ingredient`, `MealPlan`, `MealPlanEntry`, `ShoppingList`, `ShoppingItem`) con `to_dict()` / `from_dict()`.
- `storage.py`: clase `WeeklyShopperData` que carga los cuatro stores en `async_setup_entry`, mantiene los datos en memoria y expone métodos de dominio (`create_recipe`, `set_slot`, `generate_shopping_list`, `update_item`, …).
- Cada mutación: modifica la memoria → incrementa `revision` → `store.async_delay_save(self._data_to_save, 1)` (agrupa ráfagas de cambios en una sola escritura por segundo) → emite la señal de cambio (§3).
- `crud.py` se convierte en estos métodos: la lógica (acumular ingredientes de ambas recetas, respetar raciones, compactar posiciones, conservar artículos `manual` al regenerar) se porta tal cual, solo cambia el acceso a datos.
- `importer.py` se mantiene casi intacto: sus parsers (JSON externo, Markdown, nativo v1) pasan a devolver dataclasses en vez de objetos ORM.

### 2.3 Migraciones de esquema

- Se usa `Store(hass, version=1, key=..., minor_version=1)` sobrescribiendo `_async_migrate_func` en una subclase. Así se sustituyen las migraciones manuales de `database.py` (`position`, `source`, `external_id`) por un mecanismo oficial y probado.
- Regla: cambio compatible → `minor_version`+1; cambio incompatible → `version`+1 con función de migración y test.

### 2.4 Escala

Para cientos de recetas y años de menús, el JSON ocupa del orden de cientos de KB a pocos MB: carga instantánea y sin problemas. Si alguna vez el historial creciera mucho, se puede archivar por años en otro store.

---

## 3. Sincronización multiusuario en tiempo real

### 3.1 Comandos WebSocket

Registrados en `websocket_api.py` con `@websocket_api.websocket_command` + `@websocket_api.async_response`:

| Comando | Uso |
|---|---|
| `weekly_shopper/recipes/list`, `/create`, `/update`, `/delete` | Biblioteca de recetas |
| `weekly_shopper/meal_plan/get` | Menú de una semana (incluye `revision`) |
| `weekly_shopper/meal_plan/set_slot` | Cambia **un** hueco (día + comida + posición): receta, raciones, ingredientes marcados |
| `weekly_shopper/meal_plan/move` | Mover/intercambiar recetas (drag & drop) en una sola operación atómica |
| `weekly_shopper/shopping_list/get` | Lista de una semana (incluye `revision`) |
| `weekly_shopper/shopping_list/item/add`, `/update`, `/delete` | Cambios **por artículo** (marcar, cantidad, texto) |
| `weekly_shopper/shopping_list/generate` | Regenerar desde el menú (conserva `manual`) |
| `weekly_shopper/export` | Devuelve el JSON nativo; el panel lo descarga como fichero |
| `weekly_shopper/subscribe` | Suscripción a cambios de una semana y de la biblioteca de recetas |

Importación: vista HTTP `POST /api/weekly_shopper/import` (multipart), llamada desde el panel con `hass.fetchWithAuth`, porque los ficheros pueden ser grandes para un mensaje WS.

### 3.2 Difusión de cambios

1. Cada mutación en `WeeklyShopperData` llama a `async_dispatcher_send(hass, SIGNAL_CHANGED, change)` con `{scope: "meal_plan"|"shopping_list"|"recipes", week, revision, data, origin}`.
2. El comando `subscribe` registra un listener del dispatcher y reenvía cada cambio relevante con `connection.send_message(websocket_api.event_message(msg["id"], change))`; se limpia con `connection.subscriptions[msg["id"]] = unsub`.
3. La entidad `todo` y los sensores escuchan la misma señal → cuando alguien marca un artículo desde Assist o la app de HA, el panel abierto en otro móvil se actualiza al instante, y viceversa.
4. En el panel: `hass.connection.subscribeMessage(onChange, {type: "weekly_shopper/subscribe", week})`. El cliente WS de HA **re-suscribe automáticamente** al reconectar; al recibir el evento de reconexión el panel recarga el estado completo para no perder nada.

### 3.3 Conflictos

- **Operaciones granulares** en lugar de “reemplazar todo”: hoy el frontend envía el menú y la lista enteros (`PUT`), lo que hace que dos dispositivos se pisen. Con `set_slot`, `move` e `item/update`, dos personas editando cosas distintas nunca entran en conflicto.
- **Revisión optimista**: cada comando de escritura envía `base_revision`. Si coincide con la del servidor, se aplica. Si no, para cambios por artículo/hueco se aplica igualmente (último en escribir gana *solo en ese campo*); para `generate` y `move` se rechaza con error `conflict` y el panel recarga y reintenta.
- **Eco propio**: cada pestaña genera un `client_id`; el servidor lo devuelve como `origin` y el panel ignora sus propios ecos (ya aplicó el cambio de forma optimista).
- **Edición en curso**: si llega un cambio remoto sobre un campo que el usuario está escribiendo (pendiente de debounce), no se pisa el input; se aplica al perder el foco o se marca visualmente que ha cambiado.
- **Debounce**: se mantiene (350 ms) pero se fuerza el envío en `blur` y `visibilitychange` para no perder cambios al cerrar la app.

---

## 4. Nuevo repositorio

- Nombre propuesto: **`ha-weekly-shopper-planner`** (GitHub: `soniaalemany/ha-weekly-shopper-planner`, público).
- Dominio de la integración: **`weekly_shopper`**.
- El repo original se mantiene como versión standalone.

### Estructura

```
ha-weekly-shopper-planner/
├── custom_components/
│   └── weekly_shopper/
│       ├── __init__.py          # async_setup_entry / async_unload_entry
│       ├── manifest.json
│       ├── const.py             # DOMAIN, SIGNAL_CHANGED, claves de store
│       ├── config_flow.py       # alta desde la UI, instancia única
│       ├── models.py            # dataclasses del dominio
│       ├── storage.py           # WeeklyShopperData + Stores + migraciones
│       ├── logic.py             # ← crud.py: generación de listas, raciones, compactado de posiciones
│       ├── importer.py          # ← importer.py (JSON externo, Markdown, nativo v1)
│       ├── websocket_api.py     # comandos WS + subscribe
│       ├── http.py              # vista de importación de ficheros
│       ├── panel.py             # static paths + panel_custom
│       ├── todo.py              # TodoListEntity de la lista de la compra
│       ├── sensor.py            # comida/cena de hoy, artículos pendientes
│       ├── services.yaml
│       ├── strings.json
│       ├── translations/{es,en}.json
│       ├── brand/icon.png       # (+ icon@2x.png, logo.png, dark_*) — HA ≥ 2026.3
│       └── frontend/
│           └── weekly-shopper-panel.js   # bundle compilado (versionado en git)
├── frontend/
│   ├── src/
│   │   ├── panel.js             # <weekly-shopper-panel>
│   │   ├── store.js             # estado local + aplicación de eventos remotos
│   │   ├── api.js               # wrapper sobre hass.callWS / subscribeMessage
│   │   ├── planner.js           # ← app.js
│   │   ├── recipes.js           # ← recipes.js
│   │   ├── shopping.js          # ← shopping.js
│   │   └── styles.css           # ← styles.css + @tailwind
│   ├── package.json
│   ├── tailwind.config.js
│   └── build.mjs                # esbuild → custom_components/.../frontend/
├── tests/                       # pytest-homeassistant-custom-component
├── .github/workflows/
│   ├── validate.yml             # hassfest + HACS action + pytest
│   └── release.yml
├── hacs.json
├── README.md
└── LICENSE
```

### Ficheros clave

`manifest.json`
```json
{
  "domain": "weekly_shopper",
  "name": "Weekly Shopper Planner",
  "version": "0.1.0",
  "documentation": "https://github.com/soniaalemany/ha-weekly-shopper-planner",
  "issue_tracker": "https://github.com/soniaalemany/ha-weekly-shopper-planner/issues",
  "codeowners": ["@soniaalemany"],
  "config_flow": true,
  "dependencies": ["http", "frontend", "panel_custom", "websocket_api"],
  "iot_class": "local_push",
  "integration_type": "service",
  "requirements": []
}
```

`hacs.json`
```json
{
  "name": "Weekly Shopper Planner",
  "homeassistant": "2026.3.0",
  "render_readme": true
}
```
(`2026.3.0` porque es la primera versión que lee los iconos de la carpeta `brand/` local.)

---

## 5. Fases de trabajo

### Fase 0 — Preparación (½ día)
1. Crear el repo `ha-weekly-shopper-planner` en GitHub y clonarlo en `~/code/`.
2. Entorno de desarrollo de HA:
   - **venv**: `python3 -m venv .venv && pip install homeassistant` y `hass -c ./config` (enlazando `config/custom_components/weekly_shopper` → carpeta del repo).
   - o **Docker / devcontainer** con `ghcr.io/home-assistant/home-assistant:stable`. (En la última sesión no había permisos sobre el socket de Docker; usar venv si sigue así.)
3. Instalar `pytest-homeassistant-custom-component`.

### Fase 1 — Esqueleto (1 día)
1. `manifest.json`, `const.py`, `__init__.py`, `config_flow.py` (instancia única), traducciones.
2. Comprobar que aparece en **Ajustes → Dispositivos y servicios → Añadir integración**.

### Fase 2 — Modelo y persistencia (2–3 días)
1. `models.py` con dataclasses a partir de `models.py` actual; IDs UUID.
2. `storage.py` con los cuatro `Store`, carga en memoria, `async_delay_save` y subclase con `_async_migrate_func`.
3. Portar la lógica de `crud.py` a `logic.py` como **funciones puras** (entrada: dataclasses; salida: dataclasses). Así se testean sin HA.
4. Adaptar `importer.py` para producir dataclasses; mantener los tres formatos.
5. Tests unitarios: generación de listas con raciones, conservación de artículos `manual`, compactado de posiciones, importación repetida sin duplicados, migración de versión de store.

### Fase 3 — API WebSocket y tiempo real (2 días)
1. `websocket_api.py` con los comandos de §3.1 y esquemas voluptuous.
2. Señal `SIGNAL_CHANGED` emitida desde `WeeklyShopperData` en cada mutación, con `revision` y `origin`.
3. Comando `subscribe` con limpieza al cerrar la conexión.
4. Reglas de conflicto de §3.3 (`base_revision`, error `conflict`).
5. Vista HTTP de importación.
6. Tests con el cliente WS de `pytest-homeassistant-custom-component`: **dos clientes suscritos**; uno modifica, el otro recibe el evento; conflicto en `generate` devuelve `conflict`.

### Fase 4 — Panel (3–4 días)
1. `<weekly-shopper-panel>` como custom element (vanilla o Lit) con propiedades `hass`, `narrow`, `route`, `panel`.
2. `api.js` + `store.js`: sustituir los `fetch('/api/...')` y los `PUT` completos por llamadas granulares (`set_slot`, `move`, `item/update`…); actualización optimista local; aplicar eventos remotos; ignorar ecos propios por `client_id`.
3. Suscribirse al montar el panel y al cambiar de semana; desuscribirse al desmontar; recargar estado completo tras reconexión.
4. Unificar las tres páginas en pestañas con navegación por `route.path` (`/weekly-shopper/shopping`, …).
5. `querySelector` → `this.shadowRoot.querySelector`; en el drag & drop táctil, `document.elementsFromPoint` → `this.shadowRoot.elementsFromPoint`.
6. Tailwind compilado e inyectado en el Shadow DOM; colores con variables del tema de HA (`--primary-color`, `--card-background-color`, `--primary-text-color`) para modo claro/oscuro.
7. `panel.py`:
   - `hass.http.async_register_static_paths([StaticPathConfig("/weekly_shopper_static", <ruta frontend>, cache_headers=False)])`
   - `panel_custom.async_register_panel(hass, webcomponent_name="weekly-shopper-panel", frontend_url_path="weekly-shopper", module_url="/weekly_shopper_static/weekly-shopper-panel.js?v=<version>", sidebar_title="Menú semanal", sidebar_icon="mdi:food", require_admin=False)`
   - `frontend.async_remove_panel(hass, "weekly-shopper")` en `async_unload_entry`.
8. `npm run build` deja el bundle en `custom_components/weekly_shopper/frontend/` (versionado en git).

### Fase 5 — Entidades y servicios (1–2 días)
1. `todo.py`: `TodoListEntity` de la semana actual; crear/actualizar/borrar artículos llamando a `WeeklyShopperData` (artículos nuevos con `source="manual"`); se refresca con `SIGNAL_CHANGED`.
2. `sensor.py`: `sensor.comida_de_hoy`, `sensor.cena_de_hoy`, `sensor.articulos_pendientes`; también por señal, sin polling.
3. Servicios: `weekly_shopper.generate_shopping_list`, `weekly_shopper.import_data` (fichero en `/config`).

### Fase 6 — Calidad, CI y publicación (1 día)
1. `brand/icon.png` (256×256), `icon@2x.png` (512×512); opcional `logo.png` y variantes `dark_`.
2. `validate.yml`: `home-assistant/actions/hassfest@master`, `hacs/action@main` (`category: integration`) y `pytest`.
3. `release.yml`: en cada tag `vX.Y.Z`, compilar frontend, comprobar versión de `manifest.json`, publicar release.
4. README, LICENSE (p. ej. MIT), descripción y *topics* del repo (`home-assistant`, `hacs`, `integration`).
5. Release `v0.1.0`.

### Fase 7 (opcional) — Tienda por defecto de HACS
PR en `hacs/default` cuando sea estable (requiere validaciones en verde y al menos una release).

---

## 6. Instalación en Home Assistant

1. Tener **HACS** instalado.
2. HACS → menú ⋮ → **Repositorios personalizados** → `https://github.com/soniaalemany/ha-weekly-shopper-planner`, tipo **Integración**.
3. Buscar “Weekly Shopper Planner” → **Descargar**.
4. **Reiniciar Home Assistant**.
5. **Ajustes → Dispositivos y servicios → Añadir integración** → “Weekly Shopper Planner”.
6. Aparece **Menú semanal** en la barra lateral y la entidad `todo.lista_de_la_compra`.

Actualizaciones: HACS avisa → Actualizar → reiniciar HA. El `?v=<version>` del `module_url` evita caché del panel.

## 7. Migración de los datos actuales (SQLite → Store)

1. En la app actual (puerto 9009): **Recetas → Exportar datos** → `weekly-shopper-planner-YYYY-MM-DD.json`.
2. En el panel de HA: **Recetas → Importar** ese fichero. El importador nativo v1 conserva los UUID de recetas, asigna UUID nuevos a menús/artículos y es idempotente.
3. Comprobar recetas, menús e historial; apagar el contenedor Docker antiguo.

No hace falta leer el `.db` de SQLite desde HA: la exportación nativa es el puente, y así la integración no necesita SQLAlchemy ni siquiera para migrar.

---

## 8. Checklist de verificación

- [ ] `hassfest`, acción de HACS y `pytest` en verde en CI.
- [ ] `manifest.json` con `"requirements": []`.
- [ ] Instalación desde repositorio personalizado de HACS en una instancia limpia.
- [ ] Los datos sobreviven a reinicios de HA y aparecen en un backup de HA.
- [ ] Migración de store de versión N a N+1 probada con test.
- [ ] **Tiempo real**: dos dispositivos con el panel abierto → marcar un artículo, cambiar una receta o mover con drag & drop en uno se ve en el otro en < 1 s.
- [ ] **Tiempo real con HA**: añadir/marcar un artículo desde la entidad `todo` (app de HA o Assist) se refleja en el panel abierto, y viceversa.
- [ ] Dos dispositivos editando huecos distintos a la vez no se pisan.
- [ ] Regenerar la lista con revisión desfasada devuelve `conflict` y el panel se recupera solo.
- [ ] Tras cortar la red y reconectar, el panel vuelve a estar sincronizado sin recargar la página.
- [ ] Panel en escritorio y app móvil de HA, tema claro y oscuro; drag & drop con ratón y táctil.
- [ ] Autoguardado con debounce y envío forzado al salir de la app.
- [ ] Artículos manuales sobreviven a la regeneración.
- [ ] Importación JSON externa, Markdown y nativa; exportación.
- [ ] Usuario no administrador puede usar el panel.
- [ ] Desinstalar elimina el panel sin errores; documentar cómo borrar los stores.
- [ ] Sin avisos `Detected blocking call` en el log.

## 9. Riesgos y puntos abiertos

| Riesgo | Estado | Mitigación |
|---|---|---|
| Incompatibilidad con la versión de SQLAlchemy de HA | **Eliminado** | Persistencia con `Store` de HA; cero dependencias externas. |
| Cambios de dos dispositivos que no se ven / se pisan | **Mitigado** | Suscripciones WS, operaciones granulares, `revision` por documento, ecos ignorados. |
| Reescritura de `crud.py` sin ORM | Nuevo, bajo | La lógica se porta como funciones puras con tests antes de conectarla al panel. |
| Cambios en la API de `Store` o `websocket_api` de HA | Bajo | APIs públicas y estables usadas por integraciones core; CI con la versión estable de HA. |
| Edición offline (móvil sin conexión) | Abierto | Fuera de alcance de v0.1: el panel muestra aviso de desconexión y bloquea la edición hasta reconectar. |
| Semana que muestra la entidad `todo` | Abierto | Decidir: semana actual o última lista generada. |

## 10. Estimación

| Fase | Tiempo |
|---|---|
| 0. Preparación | ½ día |
| 1. Esqueleto | 1 día |
| 2. Modelo y persistencia | 2–3 días |
| 3. API WS y tiempo real | 2 días |
| 4. Panel | 3–4 días |
| 5. Entidades y servicios | 1–2 días |
| 6. CI y release | 1 día |
| **Total** | **~11–14 días** |

## Referencias

- HACS – requisitos de integraciones: https://hacs.xyz/docs/publish/integration
- HA – imágenes de marca en integraciones personalizadas (2026.3+): https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api
- HA – brand images: https://developers.home-assistant.io/docs/core/integration/brand_images
- HA – extender la API WebSocket: https://developers.home-assistant.io/docs/api/websocket#extending-the-websocket-api
- HA – almacenamiento (`helpers.storage.Store`): https://developers.home-assistant.io/docs/development_guidelines/storage

---

## 11. Estado de implementación (2026-10-01)

Fases 0–6 implementadas en local. Verificado con 45 tests de backend (`pytest`), 9 de frontend (`npm test`) y una
prueba manual del panel en una instancia real de Home Assistant 2026.9.4 (menú, autocompletado, drag & drop,
ingredientes → lista, edición con debounce, recetas, importación, reconexión, `todo` → panel en vivo, tema oscuro).

Desviaciones respecto al plan original:

- **Sin Tailwind**: el panel usa un `styles.css` propio con las variables del tema de HA (el CSS de Tailwind solo
  servía para el encabezado y la navegación de la web original, que ahora son las pestañas del panel).
- **Ingredientes marcados**: la lista generada contiene solo los ingredientes marcados en cada hueco
  (`selected_ingredient_ids`), que es lo que hacía la UI original. `generate` con `all_ingredients` los marca todos.
- **Lista siempre sincronizada**: cada cambio del menú regenera los artículos `planner` de esa semana (IDs
  deterministas, así «comprado» sobrevive); borrar un artículo del planificador des-selecciona su ingrediente.
- **Entidad `todo`**: muestra la **semana actual** (cambia sola el lunes a las 00:00).
- **Borrado de recetas**: se rechaza (`recipe_in_use`) si la receta está en algún menú (equivale al `RESTRICT` de SQLite).
- **Datos al desinstalar**: no se borran automáticamente; el README explica cómo hacerlo.
- Formato de exportación nativo v1 ampliado de forma compatible (ids de ingrediente, `selected_ingredient_ids` y
  artículos manuales); los ficheros v1 antiguos se importan igual.

Pendiente (acciones externas, no hechas): crear el repo público en GitHub y subirlo, publicar `v0.1.0`, ejecutar
hassfest/HACS en CI, probar la instalación por HACS en una instancia limpia y el drag & drop táctil en un móvil real.
