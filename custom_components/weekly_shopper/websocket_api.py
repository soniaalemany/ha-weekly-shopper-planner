"""Comandos WebSocket y suscripción de cambios en tiempo real."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SCOPE_RECIPES, SIGNAL_CHANGED
from .storage import WeeklyShopperData, WeeklyShopperError

_OPT_NUM = vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0)))
_OPT_STR = vol.Any(None, str)
_ORIGIN = {vol.Optional("client_id"): str}
_BASE = {vol.Optional("base_revision"): vol.Any(None, int)}

_INGREDIENT = vol.Schema(
    {
        vol.Optional("id"): str,
        vol.Required("name"): vol.All(str, vol.Length(min=1, max=200)),
        vol.Optional("quantity"): _OPT_NUM,
        vol.Optional("unit"): vol.Any(None, vol.All(str, vol.Length(max=40))),
        vol.Optional("category"): vol.Any(None, vol.All(str, vol.Length(max=80))),
    }
)
_RECIPE_FIELDS = {
    vol.Optional("description"): _OPT_STR,
    vol.Optional("instructions"): _OPT_STR,
    vol.Optional("servings"): vol.All(int, vol.Range(min=1)),
    vol.Optional("prep_minutes"): vol.Any(None, vol.All(int, vol.Range(min=0))),
    vol.Optional("ingredients"): [_INGREDIENT],
}
_SLOT = vol.Schema(
    {
        vol.Required("day"): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required("meal"): str,
        vol.Required("position"): vol.All(int, vol.Range(min=0, max=1)),
    }
)


def _data(hass: HomeAssistant) -> WeeklyShopperData:
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries or not hasattr(entries[0], "runtime_data"):
        raise WeeklyShopperError("not loaded")
    return entries[0].runtime_data


def _command(schema: dict):
    """Registra un comando síncrono que se ejecuta en el event loop (atómico)."""

    def decorator(func):
        name = func.__name__.removeprefix("ws_").replace("__item__", "/item/").replace("__", "/")

        @websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/{name}", **_ORIGIN, **schema})
        @callback
        def handler(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
            try:
                result = func(_data(hass), msg)
            except WeeklyShopperError as err:
                connection.send_error(msg["id"], err.code, str(err))
                return
            connection.send_result(msg["id"], result)

        return handler

    return decorator


def _origin(msg: dict[str, Any]) -> str | None:
    return msg.get("client_id")


def _plan(data: WeeklyShopperData, week: str) -> dict[str, Any]:
    return {"week": week, **data.get_plan(week).to_dict()}


def _list(data: WeeklyShopperData, week: str) -> dict[str, Any]:
    return {"week": week, **data.get_list(week).to_dict()}


# ------------------------------------------------------------------- recetas
@_command({**_ORIGIN})
def ws_recipes__list(data, msg):
    return {"recipes": data.list_recipes()}


@_command({vol.Required("name"): vol.All(str, vol.Length(min=1, max=200)), **_RECIPE_FIELDS, **_ORIGIN})
def ws_recipes__create(data, msg):
    return data.create_recipe(msg, _origin(msg))


@_command(
    {
        vol.Required("recipe_id"): str,
        vol.Optional("name"): vol.All(str, vol.Length(min=1, max=200)),
        **_RECIPE_FIELDS,
        **_ORIGIN,
    }
)
def ws_recipes__update(data, msg):
    values = {k: v for k, v in msg.items() if k not in ("id", "type", "recipe_id", "client_id")}
    return data.update_recipe(msg["recipe_id"], values, _origin(msg))


@_command({vol.Required("recipe_id"): str, **_ORIGIN})
def ws_recipes__delete(data, msg):
    data.delete_recipe(msg["recipe_id"], _origin(msg))
    return {}


# --------------------------------------------------------------------- menú
@_command({vol.Required("week"): str})
def ws_meal_plan__get(data, msg):
    return _plan(data, msg["week"])


@_command(
    {
        vol.Required("week"): str,
        vol.Required("day"): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required("meal"): str,
        vol.Required("position"): vol.All(int, vol.Range(min=0, max=1)),
        vol.Required("recipe_id"): vol.Any(None, str),
        vol.Optional("servings"): vol.Any(None, vol.All(int, vol.Range(min=1))),
        vol.Optional("selected_ingredient_ids"): [str],
        **_BASE,
        **_ORIGIN,
    }
)
def ws_meal_plan__set_slot(data, msg):
    # Granular: se aplica aunque base_revision esté desfasada (último gana en ese hueco).
    plan = data.set_slot(
        msg["week"], msg["day"], msg["meal"], msg["position"], msg["recipe_id"],
        msg.get("servings"), msg.get("selected_ingredient_ids"), _origin(msg),
    )
    return {"week": msg["week"], **plan.to_dict()}


@_command({vol.Required("week"): str, vol.Required("source"): _SLOT, vol.Required("target"): _SLOT, **_BASE, **_ORIGIN})
def ws_meal_plan__move(data, msg):
    s, t = msg["source"], msg["target"]
    plan = data.move_slot(
        msg["week"], (s["day"], s["meal"], s["position"]), (t["day"], t["meal"], t["position"]),
        msg.get("base_revision"), _origin(msg),
    )
    return {"week": msg["week"], **plan.to_dict()}


# ------------------------------------------------------------------- compra
@_command({vol.Required("week"): str})
def ws_shopping_list__get(data, msg):
    return _list(data, msg["week"])


@_command(
    {
        vol.Required("week"): str,
        vol.Required("name"): vol.All(str, vol.Length(min=1, max=200)),
        vol.Optional("quantity"): _OPT_NUM,
        vol.Optional("unit"): _OPT_STR,
        vol.Optional("category"): _OPT_STR,
        vol.Optional("checked"): bool,
        **_BASE,
        **_ORIGIN,
    }
)
def ws_shopping_list__item__add(data, msg):
    values = {k: v for k, v in msg.items() if k in ("name", "quantity", "unit", "category", "checked")}
    item = data.add_item(msg["week"], values, _origin(msg))
    return {**_list(data, msg["week"]), "item": item.to_dict()}


@_command(
    {
        vol.Required("week"): str,
        vol.Required("item_id"): str,
        vol.Optional("name"): vol.All(str, vol.Length(min=1, max=200)),
        vol.Optional("quantity"): _OPT_NUM,
        vol.Optional("unit"): _OPT_STR,
        vol.Optional("category"): _OPT_STR,
        vol.Optional("checked"): bool,
        **_BASE,
        **_ORIGIN,
    }
)
def ws_shopping_list__item__update(data, msg):
    values = {k: v for k, v in msg.items() if k in ("name", "quantity", "unit", "category", "checked")}
    item = data.update_item(msg["week"], msg["item_id"], values, _origin(msg))
    return {**_list(data, msg["week"]), "item": item.to_dict()}


@_command({vol.Required("week"): str, vol.Required("item_id"): str, **_BASE, **_ORIGIN})
def ws_shopping_list__item__delete(data, msg):
    data.delete_item(msg["week"], msg["item_id"], _origin(msg))
    return _list(data, msg["week"])


@_command({vol.Required("week"): str, vol.Optional("all_ingredients"): bool, **_BASE, **_ORIGIN})
def ws_shopping_list__generate(data, msg):
    data.generate_list(msg["week"], msg.get("base_revision"), msg.get("all_ingredients", False), _origin(msg))
    return _list(data, msg["week"])


@_command({})
def ws_export(data, msg):
    return data.export()


# ---------------------------------------------------------------- suscripción
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/subscribe", vol.Optional("week"): vol.Any(None, str), **_ORIGIN}
)
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Reenvía los cambios de la biblioteca y de la semana indicada."""
    week = msg.get("week")

    @callback
    def forward(change: dict[str, Any]) -> None:
        if change["scope"] != SCOPE_RECIPES and change["week"] != week:
            return
        connection.send_message(websocket_api.event_message(msg["id"], change))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_CHANGED, forward)
    connection.send_result(msg["id"])


def async_register_commands(hass: HomeAssistant) -> None:
    for handler in (
        ws_recipes__list, ws_recipes__create, ws_recipes__update, ws_recipes__delete,
        ws_meal_plan__get, ws_meal_plan__set_slot, ws_meal_plan__move,
        ws_shopping_list__get, ws_shopping_list__item__add, ws_shopping_list__item__update,
        ws_shopping_list__item__delete, ws_shopping_list__generate, ws_export, ws_subscribe,
    ):
        websocket_api.async_register_command(hass, handler)
