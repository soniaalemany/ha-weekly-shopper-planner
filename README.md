# Weekly Shopper Planner para Home Assistant

Planificador semanal de comidas y lista de la compra como **integración personalizada** (HACS) para Home Assistant.

- **Panel propio** en la barra lateral (*Menú semanal*) con pestañas Menú · Recetas · Compra.
- **Tiempo real** entre dispositivos: lo que cambias en un móvil se ve al instante en los demás.
- **Entidades nativas**: `todo.lista_de_la_compra` (app móvil, Assist, automatizaciones) y los sensores
  `sensor.comida_de_hoy`, `sensor.cena_de_hoy` y `sensor.articulos_pendientes`.
- Sin dependencias externas: los datos se guardan en `/config/.storage/` y entran en las copias de seguridad de HA.

## Instalación (HACS)

1. Con **HACS** instalado: menú ⋮ → **Repositorios personalizados** →
   `https://github.com/soniaalemany/ha-weekly-shopper-planner`, tipo **Integración**.
2. Busca «Weekly Shopper Planner» → **Descargar** → reinicia Home Assistant.
3. **Ajustes → Dispositivos y servicios → Añadir integración** → «Weekly Shopper Planner».

Requiere Home Assistant 2026.3 o superior.

## Uso

- **Menú**: busca o crea un plato en cada hueco (comida/cena, con un segundo plato opcional con «+»); arrástralo
  para moverlo o intercambiarlo. El icono ☷ despliega los ingredientes: **los que marques van a la lista de la compra**
  (con las cantidades escaladas por raciones).
- **Compra**: marca, edita, añade o borra artículos. «Regenerar desde el menú» reconstruye los artículos del
  menú y conserva los añadidos a mano y lo ya marcado como comprado.
- **Recetas**: biblioteca, importación (JSON externo, JSON nativo o Markdown) y exportación.

La lista de la compra se mantiene sola: cualquier cambio del menú actualiza los artículos de esa semana.

### Servicios

| Servicio | Descripción |
|---|---|
| `weekly_shopper.generate_shopping_list` | Reconstruye la lista de una semana (`week`, opcional) desde su menú; con `all_ingredients: true` marca todos los ingredientes. |
| `weekly_shopper.import_data` | Importa un fichero `.json`/`.md` ubicado en `/config` (`path`). |

### Importar desde la app original

En la app standalone: **Recetas → Exportar datos**; en el panel de HA: **Recetas → Importar** ese fichero.
Es idempotente (repetirlo no duplica recetas ni usos).

### Formato Markdown

```markdown
## Tortilla de patatas
- Huevos: 6
- Patatas: 500 g
```

## Desinstalar y borrar los datos

Eliminar la integración **no borra los datos** (para que reinstalar no pierda nada). Para borrarlos del todo, con
Home Assistant parado elimina de `/config/.storage/` los ficheros `weekly_shopper.recipes`,
`weekly_shopper.meal_plans`, `weekly_shopper.shopping_lists` y `weekly_shopper.history`.

## Desarrollo

```bash
./scripts/setup-dev.sh        # venv + Home Assistant + pytest
.venv/bin/hass -c ./config    # http://localhost:8123
.venv/bin/pytest              # backend
cd frontend && npm install && npm test && npm run build   # panel → custom_components/weekly_shopper/frontend/
```

El bundle compilado del panel (`weekly-shopper-panel.js`) se versiona en git: tras tocar `frontend/src/`
ejecuta `npm run build` y haz commit del resultado (el CI lo comprueba).

Arquitectura y decisiones: ver [`PLAN.md`](PLAN.md).
