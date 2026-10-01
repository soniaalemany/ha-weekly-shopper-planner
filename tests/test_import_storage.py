"""Importación (3 formatos), HTTP, persistencia y migraciones de store."""
import json
from datetime import timedelta

import aiohttp
import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.weekly_shopper.const import STORE_RECIPES
from custom_components.weekly_shopper.storage import (
    InvalidData,
    WeeklyShopperData,
    migrate_data,
)

from .conftest import WEEK

MARKDOWN = """# Mis recetas
## Tortilla
- Huevos: 6
- Patatas: 500 g
- Sal: al gusto

## Sin ingredientes
texto
"""

EXTERNAL = {
    "products": [{"id": "p1", "name": "Leche"}, {"id": "p2", "name": "Harina", "deletedAt": "x"}],
    "recipes": [{"id": "r1", "name": "Crepes"}],
    "aisles": [{"id": "a1", "name": "Lácteos"}],
    "product_aisles": [{"productId": "p1", "aisleId": "a1"}],
    "products_recipies": [{"recipeId": "r1", "productId": "p1", "amount": 250, "unit": "ml"}],
    "schedule": [
        {"week": 0, "day": 0, "recipeId": "r1", "meal": "comida"},
        {"week": "2026-09-28", "day": 2, "recipeId": "r1", "meal": "cena"},
        {"week": "2026-09-28", "day": 2, "recipeId": "r1", "meal": "cena"},
        {"week": "2026-09-29", "day": 2, "recipeId": "r1"},  # no es lunes
    ],
}


async def test_markdown_import_is_idempotent(setup_integration, data):
    counts = data.import_markdown(MARKDOWN)
    assert counts == {"recipes": 1, "new_recipes": 1, "ingredients": 3, "usages": 0}
    recipe = next(iter(data.recipes.values()))
    assert recipe.servings == 2
    assert [(i.name, i.quantity, i.unit) for i in recipe.ingredients] == [
        ("Huevos", 6, None), ("Patatas", 500, "g"), ("Sal", None, None)]
    ids = [i.id for i in recipe.ingredients]
    counts = data.import_markdown(MARKDOWN)
    assert counts["new_recipes"] == 0 and len(data.recipes) == 1
    assert [i.id for i in data.recipes[recipe.id].ingredients] == ids  # ids estables
    with pytest.raises(InvalidData):
        data.import_markdown("  ")


async def test_external_import(setup_integration, data):
    counts = data.import_payload(EXTERNAL)
    assert counts["new_recipes"] == 1 and counts["ingredients"] == 1
    recipe = next(iter(data.recipes.values()))
    assert recipe.ingredients[0].category == "Lácteos"
    # semana 0 = 1970-01-05 y 2026-09-28; el lunes inválido se ignora;
    # dos filas del mismo hueco son primer y segundo plato
    assert sorted(data.meal_plans) == ["1970-01-05", WEEK]
    assert [e.slot for e in data.meal_plans[WEEK].entries] == [(2, "cena", 0), (2, "cena", 1)]
    again = data.import_payload(EXTERNAL)
    assert again["new_recipes"] == 0 and again["usages"] == 0
    assert len(data.recipes) == 1 and len(data.history) == 2


async def test_native_roundtrip_via_import(hass, setup_integration, data):
    data.import_markdown(MARKDOWN)
    recipe = next(iter(data.recipes.values()))
    data.set_slot(WEEK, 0, "comida", 0, recipe.id, selected_ingredient_ids=[recipe.ingredients[0].id])
    data.add_item(WEEK, {"name": "Pan"})
    exported = json.loads(json.dumps(data.export()))

    other = WeeklyShopperData(hass)
    counts = other.import_payload(exported)
    assert counts["recipes"] == 1 and counts["new_recipes"] == 1
    assert other.recipes[recipe.id].ingredients[0].id == recipe.ingredients[0].id
    plan = other.meal_plans[WEEK]
    assert plan.entries[0].selected_ingredient_ids == [recipe.ingredients[0].id]
    assert sorted(i.name for i in other.shopping_lists[WEEK].items) == ["Huevos", "Pan"]
    # idempotente
    again = other.import_payload(exported)
    assert again["new_recipes"] == 0 and again["usages"] == 0
    assert len(other.recipes) == 1 and len(other.history) == 1


async def test_native_v1_without_extensions(setup_integration, data):
    """Formato exportado por la app original: sin ids de ingrediente ni selección."""
    payload = {
        "format": "weekly-shopper-planner", "version": 1,
        "recipes": [{"id": "uuid-1", "name": "Lentejas", "servings": 3,
                     "ingredients": [{"name": "Lentejas", "quantity": 300, "unit": "g"}]}],
        "meal_plans": [{"monday": WEEK, "entries": [
            {"day_of_week": 1, "meal_type": "comida", "position": 0, "recipe_id": "uuid-1", "servings": None}]}],
        "usage_history": [{"recipe_id": "uuid-1", "monday": WEEK, "meal_type": "comida",
                           "used_at": "2026-09-29T00:00:00Z"}],
    }
    data.import_payload(payload)
    assert "uuid-1" in data.recipes and data.recipes["uuid-1"].servings == 3
    assert data.meal_plans[WEEK].entries[0].recipe_id == "uuid-1"
    assert data.history[0].used_at == "2026-09-29T00:00:00"


@pytest.mark.parametrize("mutate, message", [
    (lambda p: p.update(version=2), "version"),
    (lambda p: p["meal_plans"][0]["entries"][0].update(recipe_id="nope"), "Unknown recipe"),
    (lambda p: p["meal_plans"][0].update(monday="2026-09-29"), "Monday"),
    (lambda p: p.update(recipes="x"), "structure"),
])
async def test_native_import_validates_before_applying(setup_integration, data, mutate, message):
    payload = {
        "format": "weekly-shopper-planner", "version": 1,
        "recipes": [{"id": "r", "name": "A", "ingredients": []}],
        "meal_plans": [{"monday": WEEK, "entries": [
            {"day_of_week": 0, "meal_type": "comida", "position": 0, "recipe_id": "r"}]}],
    }
    mutate(payload)
    with pytest.raises(InvalidData, match=message):
        data.import_payload(payload)
    assert data.recipes == {} and data.meal_plans == {}  # nada a medias


async def test_http_import(hass, hass_client, setup_integration, data):
    client = await hass_client()
    for filename, content, expected in (
        ("recetas.md", MARKDOWN, "ingredients"),
        ("datos.json", json.dumps(EXTERNAL), "plans"),
    ):
        form = aiohttp.FormData()
        form.add_field("file", content, filename=filename)
        resp = await client.post("/api/weekly_shopper/import?client_id=x", data=form)
        assert resp.status == 200, await resp.text()
        assert expected in await resp.json()
    form = aiohttp.FormData()
    form.add_field("file", "{no json", filename="malo.json")
    assert (await client.post("/api/weekly_shopper/import", data=form)).status == 400
    form = aiohttp.FormData()
    form.add_field("file", json.dumps({"format": "weekly-shopper-planner", "version": 9}), filename="v.json")
    resp = await client.post("/api/weekly_shopper/import", data=form)
    assert resp.status == 400 and (await resp.json())["code"] == "invalid_format"
    assert (await client.post("/api/weekly_shopper/import", data={"x": "y"})).status == 400


async def test_requires_auth(hass, hass_client_no_auth, setup_integration):
    client = await hass_client_no_auth()
    assert (await client.post("/api/weekly_shopper/import")).status == 401


async def test_persistence_across_reload(hass, hass_storage, setup_integration, data):
    data.import_payload(EXTERNAL)
    data.add_item(WEEK, {"name": "Pan"})
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()
    assert "weekly_shopper.recipes" in hass_storage
    assert hass_storage["weekly_shopper.recipes"]["version"] == 1

    assert await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()
    loaded = setup_integration.runtime_data
    assert loaded is not data
    assert [r.name for r in loaded.recipes.values()] == ["Crepes"]
    assert sorted(i.name for i in loaded.shopping_lists[WEEK].items) == ["Pan"]
    assert loaded.meal_plans[WEEK].revision == data.meal_plans[WEEK].revision


async def test_unload_flushes_pending_saves(hass, hass_storage, setup_integration, data):
    data.add_item(WEEK, {"name": "Pan"})  # guardado diferido, aún sin escribir
    assert "weekly_shopper.shopping_lists" not in hass_storage
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    items = hass_storage["weekly_shopper.shopping_lists"]["data"]["lists"][WEEK]["items"]
    assert items[0]["name"] == "Pan"


async def test_migration_hook(hass, hass_storage):
    assert migrate_data(STORE_RECIPES, 1, 0, {"recipes": []}) == {"recipes": []}
    with pytest.raises(NotImplementedError):
        migrate_data(STORE_RECIPES, 99, 0, {})
    # un store guardado con minor_version antigua se carga y pasa por la migración
    hass_storage[STORE_RECIPES] = {
        "version": 1, "minor_version": 0, "key": STORE_RECIPES,
        "data": {"recipes": [{"id": "r", "name": "Vieja", "ingredients": []}]},
    }
    data = WeeklyShopperData(hass)
    await data.async_load()
    assert data.recipes["r"].name == "Vieja"


async def test_native_import_tolerates_extra_positions(setup_integration, data):
    """El export de la app original puede traer un tercer plato (position 2): se descarta sin fallar."""
    payload = {
        "format": "weekly-shopper-planner", "version": 1,
        "recipes": [{"id": "r", "name": "A", "ingredients": []}],
        "meal_plans": [{"monday": WEEK, "entries": [
            {"day_of_week": 2, "meal_type": "comida", "position": p, "recipe_id": "r"} for p in (0, 1, 2)]}],
    }
    counts = data.import_payload(payload)
    assert counts["skipped_entries"] == 1
    assert [e.slot for e in data.meal_plans[WEEK].entries] == [(2, "comida", 0), (2, "comida", 1)]
