"""Entidad todo, sensores y servicios."""

import pytest
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.weekly_shopper.const import DOMAIN

from .conftest import WEEK

TODAY = "2026-09-30 10:00:00+00:00"  # miércoles de la semana WEEK


@pytest.fixture(autouse=True)
def frozen(freezer):
    freezer.move_to(TODAY)
    return freezer


async def _items(hass):
    resp = await hass.services.async_call(
        "todo", "get_items", {"entity_id": "todo.lista_de_la_compra"},
        blocking=True, return_response=True)
    return resp["todo.lista_de_la_compra"]["items"]


async def test_todo_reflects_and_edits_list(hass, setup_integration, data):
    assert await _items(hass) == []
    await hass.services.async_call(
        "todo", "add_item",
        {"entity_id": "todo.lista_de_la_compra", "item": "Leche", "description": "2 l"},
        blocking=True)
    assert data.get_list(WEEK).items[0].quantity == 2 and data.get_list(WEEK).items[0].unit == "l"
    items = await _items(hass)
    assert [(i["summary"], i["status"], i["description"]) for i in items] == [("Leche", "needs_action", "2 l")]
    assert hass.states.get("todo.lista_de_la_compra").state == "1"

    await hass.services.async_call(
        "todo", "update_item",
        {"entity_id": "todo.lista_de_la_compra", "item": items[0]["uid"], "status": "completed"},
        blocking=True)
    assert data.get_list(WEEK).items[0].checked is True
    assert hass.states.get("todo.lista_de_la_compra").state == "0"

    await hass.services.async_call(
        "todo", "remove_item",
        {"entity_id": "todo.lista_de_la_compra", "item": items[0]["uid"]}, blocking=True)
    assert data.get_list(WEEK).items == []


async def test_panel_change_updates_todo_state(hass, setup_integration, data):
    """Un cambio hecho desde el panel (datos) se refleja al instante en la entidad."""
    data.add_item(WEEK, {"name": "Pan"})
    data.add_item(WEEK, {"name": "Agua"})
    await hass.async_block_till_done()
    assert hass.states.get("todo.lista_de_la_compra").state == "2"
    assert hass.states.get("sensor.articulos_pendientes").state == "2"
    data.update_item(WEEK, data.get_list(WEEK).items[0].id, {"checked": True})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.articulos_pendientes").state == "1"


async def test_todo_follows_current_week(hass, setup_integration, data, frozen):
    data.add_item(WEEK, {"name": "Pan"})
    await hass.async_block_till_done()
    assert hass.states.get("todo.lista_de_la_compra").state == "1"
    # lunes 00:00:05 en la zona horaria de HA (US/Pacific en los tests = UTC-7)
    frozen.move_to("2026-10-05 07:00:05+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("todo.lista_de_la_compra").state == "0"


async def test_meal_sensors(hass, setup_integration, data):
    assert hass.states.get("sensor.comida_de_hoy").state == "unknown"
    pasta = data.create_recipe({"name": "Pasta"})
    sopa = data.create_recipe({"name": "Sopa"})
    data.set_slot(WEEK, 2, "comida", 0, pasta["id"])
    data.set_slot(WEEK, 2, "comida", 1, sopa["id"])
    data.set_slot(WEEK, 2, "cena", 0, sopa["id"])
    data.set_slot(WEEK, 3, "cena", 0, pasta["id"])  # mañana
    await hass.async_block_till_done()
    comida = hass.states.get("sensor.comida_de_hoy")
    assert comida.state == "Pasta + Sopa" and comida.attributes["recipes"] == ["Pasta", "Sopa"]
    assert hass.states.get("sensor.cena_de_hoy").state == "Sopa"


async def test_service_generate_shopping_list(hass, setup_integration, data):
    recipe = data.create_recipe({"name": "Pasta", "ingredients": [{"name": "Tomate", "quantity": 1}]})
    data.set_slot(WEEK, 0, "comida", 0, recipe["id"])
    assert data.get_list(WEEK).items == []
    await hass.services.async_call(
        DOMAIN, "generate_shopping_list", {"week": "2026-10-02", "all_ingredients": True}, blocking=True)
    assert [i.name for i in data.get_list(WEEK).items] == ["Tomate"]
    with pytest.raises(ServiceValidationError):  # semana sin menú
        await hass.services.async_call(
            DOMAIN, "generate_shopping_list", {"week": "2027-01-01"}, blocking=True)
    # sin semana: usa la actual (la del menú)
    await hass.services.async_call(DOMAIN, "generate_shopping_list", {}, blocking=True)


async def test_service_import_data(hass, setup_integration, data, tmp_path):
    hass.config.config_dir = str(tmp_path)
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    (tmp_path / "recetas.md").write_text("## Tortilla\n- Huevos: 6\n", encoding="utf-8")
    await hass.services.async_call(DOMAIN, "import_data", {"path": "recetas.md"}, blocking=True)
    assert [r.name for r in data.recipes.values()] == ["Tortilla"]
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "import_data", {"path": "no_existe.json"}, blocking=True)
    (tmp_path / "malo.json").write_text("{", encoding="utf-8")
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "import_data", {"path": "malo.json"}, blocking=True)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "import_data", {"path": "../../etc/passwd"}, blocking=True)


async def test_panel_registered_and_removed(hass, setup_integration):
    assert "weekly-shopper" in hass.data["frontend_panels"]
    panel = hass.data["frontend_panels"]["weekly-shopper"]
    assert panel.sidebar_title == "Menú semanal" and panel.require_admin is False
    assert panel.config["_panel_custom"]["name"] == "weekly-shopper-panel"
    assert "?v=0.1.0" in panel.config["_panel_custom"]["module_url"]
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert "weekly-shopper" not in hass.data["frontend_panels"]
    assert await hass.config_entries.async_setup(setup_integration.entry_id)  # re-alta sin errores


async def test_single_instance(hass, setup_integration):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "abort" and result["reason"] == "single_instance_allowed"
