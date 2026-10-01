"""Sensores: comida y cena de hoy, artículos pendientes (sin polling)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from . import logic
from .const import SIGNAL_CHANGED
from .storage import WeeklyShopperData


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    data = entry.runtime_data
    async_add_entities(
        [
            MealSensor(data, entry.entry_id, "comida", "Comida de hoy", "mdi:food"),
            MealSensor(data, entry.entry_id, "cena", "Cena de hoy", "mdi:food-variant"),
            PendingItemsSensor(data, entry.entry_id),
        ]
    )


class _Base(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, data: WeeklyShopperData) -> None:
        self._data = data

    async def async_added_to_hass(self) -> None:
        @callback
        def refresh(*_: Any) -> None:
            self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_CHANGED, refresh))
        self.async_on_remove(async_track_time_change(self.hass, refresh, hour=0, minute=0, second=5))


class MealSensor(_Base):
    def __init__(self, data: WeeklyShopperData, entry_id: str, meal: str, name: str, icon: str) -> None:
        super().__init__(data)
        self._meal = meal
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry_id}_{meal}_today"

    @property
    def native_value(self) -> str | None:
        names = self._data.day_recipes(dt_util.now().date(), self._meal)
        return " + ".join(names) or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"recipes": self._data.day_recipes(dt_util.now().date(), self._meal)}


class PendingItemsSensor(_Base):
    _attr_name = "Artículos pendientes"
    _attr_icon = "mdi:cart"
    _attr_native_unit_of_measurement = "artículos"

    def __init__(self, data: WeeklyShopperData, entry_id: str) -> None:
        super().__init__(data)
        self._attr_unique_id = f"{entry_id}_pending_items"

    @property
    def native_value(self) -> int:
        monday = logic.monday_of(dt_util.now().date()).isoformat()
        return sum(1 for i in self._data.get_list(monday).items if not i.checked)
