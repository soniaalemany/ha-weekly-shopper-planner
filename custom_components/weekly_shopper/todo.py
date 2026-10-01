"""Lista de la compra de la semana actual como entidad ``todo``."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from . import logic
from .const import SCOPE_SHOPPING_LIST, SIGNAL_CHANGED
from .storage import WeeklyShopperData


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([ShoppingTodoList(entry.runtime_data, entry.entry_id)])


def current_monday() -> str:
    return logic.monday_of(dt_util.now().date()).isoformat()


class ShoppingTodoList(TodoListEntity):
    """Semana actual (cambia sola el lunes a las 00:00)."""

    _attr_has_entity_name = True
    _attr_name = "Lista de la compra"
    _attr_should_poll = False
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, data: WeeklyShopperData, entry_id: str) -> None:
        self._data = data
        self._attr_unique_id = f"{entry_id}_shopping_list"

    @property
    def todo_items(self) -> list[TodoItem]:
        return [
            TodoItem(
                uid=item.id,
                summary=item.name,
                status=TodoItemStatus.COMPLETED if item.checked else TodoItemStatus.NEEDS_ACTION,
                description=logic.format_quantity(item.quantity, item.unit) or None,
            )
            for item in self._data.get_list(current_monday()).items
        ]

    async def async_added_to_hass(self) -> None:
        @callback
        def changed(change: dict) -> None:
            if change["scope"] == SCOPE_SHOPPING_LIST and change["week"] == current_monday():
                self.async_write_ha_state()

        @callback
        def new_day(_: datetime) -> None:
            self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_CHANGED, changed))
        self.async_on_remove(async_track_time_change(self.hass, new_day, hour=0, minute=0, second=5))

    async def async_create_todo_item(self, item: TodoItem) -> None:
        values: dict = {"name": item.summary or ""}
        if item.description:
            values["quantity"], values["unit"] = logic.parse_quantity(item.description)
        created = self._data.add_item(current_monday(), values)
        if item.status == TodoItemStatus.COMPLETED:
            self._data.update_item(current_monday(), created.id, {"checked": True})

    async def async_update_todo_item(self, item: TodoItem) -> None:
        values: dict = {}
        if item.summary is not None:
            values["name"] = item.summary
        if item.status is not None:
            values["checked"] = item.status == TodoItemStatus.COMPLETED
        if item.description is not None:
            values["quantity"], values["unit"] = logic.parse_quantity(item.description)
        self._data.update_item(current_monday(), item.uid, values)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            self._data.delete_item(current_monday(), uid)
