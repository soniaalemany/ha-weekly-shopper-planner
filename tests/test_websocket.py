"""API WebSocket: operaciones, conflictos y tiempo real entre dos clientes."""

from .conftest import WEEK


async def call(client, type_, **kwargs):
    await client.send_json_auto_id({"type": f"weekly_shopper/{type_}", **kwargs})
    return await client.receive_json()


async def make_recipe(client, name="Pasta", ingredients=None):
    resp = await call(client, "recipes/create", name=name, servings=2,
                      ingredients=ingredients or [{"name": "Tomate", "quantity": 200, "unit": "g"},
                                                  {"name": "Sal"}])
    assert resp["success"], resp
    return resp["result"]


async def test_recipe_crud(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    recipe = await make_recipe(client)
    assert recipe["usage_count"] == 0 and len(recipe["ingredients"]) == 2

    resp = await call(client, "recipes/update", recipe_id=recipe["id"], name="Pasta fresca")
    assert resp["result"]["name"] == "Pasta fresca"
    # sin ingredientes en el update, no se tocan
    assert len(resp["result"]["ingredients"]) == 2

    resp = await call(client, "recipes/list")
    assert [r["name"] for r in resp["result"]["recipes"]] == ["Pasta fresca"]

    resp = await call(client, "recipes/delete", recipe_id=recipe["id"])
    assert resp["success"]
    resp = await call(client, "recipes/delete", recipe_id=recipe["id"])
    assert resp["error"]["code"] == "not_found"


async def test_validation_errors(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    resp = await call(client, "meal_plan/get", week="2026-09-29")  # martes
    assert resp["error"]["code"] == "invalid_format"
    resp = await call(client, "recipes/create", name="")
    assert resp["error"]["code"] == "invalid_format"


async def test_set_slot_selection_generates_list(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    recipe = await make_recipe(client)
    tomato = recipe["ingredients"][0]["id"]

    resp = await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida",
                      position=0, recipe_id=recipe["id"], selected_ingredient_ids=[tomato])
    assert resp["result"]["revision"] == 1
    lst = (await call(client, "shopping_list/get", week=WEEK))["result"]
    assert [(i["name"], i["quantity"], i["source"]) for i in lst["items"]] == [("Tomate", 200, "planner")]

    # raciones ×2 → cantidad ×2
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0,
               recipe_id=recipe["id"], servings=4, selected_ingredient_ids=[tomato])
    lst = (await call(client, "shopping_list/get", week=WEEK))["result"]
    assert lst["items"][0]["quantity"] == 400

    # vaciar el hueco quita el artículo del planificador
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0, recipe_id=None)
    lst = (await call(client, "shopping_list/get", week=WEEK))["result"]
    assert lst["items"] == []


async def test_manual_items_survive_regeneration(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    recipe = await make_recipe(client)
    resp = await call(client, "shopping_list/item/add", week=WEEK, name="Pan", quantity=1, unit="barra")
    assert resp["result"]["item"]["source"] == "manual"
    await call(client, "meal_plan/set_slot", week=WEEK, day=1, meal="cena", position=0,
               recipe_id=recipe["id"], selected_ingredient_ids=[recipe["ingredients"][1]["id"]])
    resp = await call(client, "shopping_list/generate", week=WEEK)
    names = [i["name"] for i in resp["result"]["items"]]
    assert names == ["Pan", "Sal"]


async def test_item_update_check_and_delete(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    recipe = await make_recipe(client)
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0,
               recipe_id=recipe["id"], selected_ingredient_ids=[recipe["ingredients"][0]["id"]])
    item = (await call(client, "shopping_list/get", week=WEEK))["result"]["items"][0]
    resp = await call(client, "shopping_list/item/update", week=WEEK, item_id=item["id"], checked=True)
    assert resp["result"]["item"]["checked"] is True

    # regenerar mantiene el «comprado»
    await call(client, "shopping_list/generate", week=WEEK)
    lst = (await call(client, "shopping_list/get", week=WEEK))["result"]
    assert lst["items"][0]["checked"] is True

    # borrar un artículo del planificador des-selecciona el ingrediente
    await call(client, "shopping_list/item/delete", week=WEEK, item_id=item["id"])
    await call(client, "shopping_list/generate", week=WEEK)
    assert (await call(client, "shopping_list/get", week=WEEK))["result"]["items"] == []
    plan = (await call(client, "meal_plan/get", week=WEEK))["result"]
    assert plan["entries"][0]["selected_ingredient_ids"] == []

    resp = await call(client, "shopping_list/item/update", week=WEEK, item_id="nope", checked=True)
    assert resp["error"]["code"] == "not_found"


async def test_move_swaps_and_conflicts(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    a = await make_recipe(client, "A")
    b = await make_recipe(client, "B")
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0, recipe_id=a["id"])
    resp = await call(client, "meal_plan/set_slot", week=WEEK, day=1, meal="cena", position=0, recipe_id=b["id"])
    revision = resp["result"]["revision"]
    assert revision == 2

    src, dst = {"day": 0, "meal": "comida", "position": 0}, {"day": 1, "meal": "cena", "position": 0}
    stale = await call(client, "meal_plan/move", week=WEEK, source=src, target=dst, base_revision=revision - 1)
    assert stale["error"]["code"] == "conflict"

    ok = await call(client, "meal_plan/move", week=WEEK, source=src, target=dst, base_revision=revision)
    assert ok["success"]
    slots = {(e["day"], e["meal"]): e["recipe_id"] for e in ok["result"]["entries"]}
    assert slots == {(1, "cena"): a["id"], (0, "comida"): b["id"]}


async def test_generate_with_stale_revision_conflicts(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    recipe = await make_recipe(client)
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0, recipe_id=recipe["id"])
    await call(client, "shopping_list/item/add", week=WEEK, name="Pan")
    resp = await call(client, "shopping_list/generate", week=WEEK, base_revision=0)
    assert resp["error"]["code"] == "conflict"
    revision = (await call(client, "shopping_list/get", week=WEEK))["result"]["revision"]
    assert (await call(client, "shopping_list/generate", week=WEEK, base_revision=revision))["success"]
    resp = await call(client, "shopping_list/generate", week="2026-10-05")
    assert resp["error"]["code"] == "not_found"


async def test_generate_all_ingredients_selects_them(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    recipe = await make_recipe(client)
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0, recipe_id=recipe["id"])
    resp = await call(client, "shopping_list/generate", week=WEEK, all_ingredients=True)
    assert sorted(i["name"] for i in resp["result"]["items"]) == ["Sal", "Tomate"]
    # y sigue siendo así tras otro cambio del menú
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0,
               recipe_id=recipe["id"], servings=4)
    lst = (await call(client, "shopping_list/get", week=WEEK))["result"]
    assert len(lst["items"]) == 2


async def test_delete_recipe_in_use_rejected(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    recipe = await make_recipe(client)
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0, recipe_id=recipe["id"])
    resp = await call(client, "recipes/delete", recipe_id=recipe["id"])
    assert resp["error"]["code"] == "recipe_in_use"
    recipes = (await call(client, "recipes/list"))["result"]["recipes"]
    assert recipes[0]["usage_count"] == 1 and recipes[0]["last_used_date"] == WEEK


async def test_recipe_update_drops_stale_selection(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    recipe = await make_recipe(client)
    tomato, salt = (i["id"] for i in recipe["ingredients"])
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0,
               recipe_id=recipe["id"], selected_ingredient_ids=[tomato, salt])
    await call(client, "recipes/update", recipe_id=recipe["id"],
               ingredients=[{"id": salt, "name": "Sal"}, {"name": "Ajo"}])
    plan = (await call(client, "meal_plan/get", week=WEEK))["result"]
    assert plan["entries"][0]["selected_ingredient_ids"] == [salt]
    lst = (await call(client, "shopping_list/get", week=WEEK))["result"]
    assert [i["name"] for i in lst["items"]] == ["Sal"]


# ---------------------------------------------------------------- tiempo real
async def test_two_clients_realtime(hass, hass_ws_client, setup_integration):
    writer = await hass_ws_client(hass)
    reader = await hass_ws_client(hass)

    await reader.send_json_auto_id({"type": "weekly_shopper/subscribe", "week": WEEK})
    sub_id = (await reader.receive_json())["id"]

    recipe = await make_recipe(writer)
    event = await reader.receive_json()
    assert event["id"] == sub_id and event["type"] == "event"
    assert event["event"]["scope"] == "recipes"

    await call(writer, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0,
               recipe_id=recipe["id"], selected_ingredient_ids=[recipe["ingredients"][0]["id"]],
               client_id="tab-1")
    events = []
    for _ in range(3):  # menú + lista + recetas (usage_count)
        events.append((await reader.receive_json())["event"])
    scopes = [e["scope"] for e in events]
    assert sorted(scopes) == ["meal_plan", "recipes", "shopping_list"]
    plan_event = next(e for e in events if e["scope"] == "meal_plan")
    assert plan_event["origin"] == "tab-1" and plan_event["week"] == WEEK
    assert plan_event["data"]["entries"][0]["recipe_id"] == recipe["id"]
    list_event = next(e for e in events if e["scope"] == "shopping_list")
    assert list_event["data"]["items"][0]["name"] == "Tomate"

    # otra semana: el suscriptor solo recibe lo de la biblioteca
    await call(writer, "shopping_list/item/add", week="2026-10-05", name="Pan")
    await call(writer, "recipes/create", name="Otra")
    event = (await reader.receive_json())["event"]
    assert event["scope"] == "recipes"


async def test_unsubscribe_stops_events(hass, hass_ws_client, setup_integration):
    writer = await hass_ws_client(hass)
    reader = await hass_ws_client(hass)
    await reader.send_json_auto_id({"type": "weekly_shopper/subscribe", "week": WEEK})
    sub_id = (await reader.receive_json())["id"]
    await reader.send_json_auto_id({"type": "unsubscribe_events", "subscription": sub_id})
    assert (await reader.receive_json())["success"]
    await call(writer, "shopping_list/item/add", week=WEEK, name="Pan")
    # el siguiente mensaje que reciba el lector es la respuesta a su propio comando
    resp = await call(reader, "shopping_list/get", week=WEEK)
    assert resp["type"] == "result" and resp["result"]["items"][0]["name"] == "Pan"


async def test_export_roundtrip(hass, hass_ws_client, setup_integration):
    client = await hass_ws_client(hass)
    recipe = await make_recipe(client)
    await call(client, "meal_plan/set_slot", week=WEEK, day=0, meal="comida", position=0,
               recipe_id=recipe["id"], selected_ingredient_ids=[recipe["ingredients"][0]["id"]])
    await call(client, "shopping_list/item/add", week=WEEK, name="Pan")
    exported = (await call(client, "export"))["result"]
    assert exported["format"] == "weekly-shopper-planner" and exported["version"] == 1
    assert exported["meal_plans"][0]["entries"][0]["recipe_id"] == recipe["id"]
    assert exported["manual_shopping_items"][0]["items"][0]["name"] == "Pan"
    assert exported["usage_history"][0]["recipe_id"] == recipe["id"]
