"""Weekly Shopper Planner: menú semanal y lista de la compra para Home Assistant."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from . import logic
from .const import DOMAIN, PLATFORMS
from .http import ImportView
from .panel import async_register_panel, async_remove_panel
from .storage import WeeklyShopperData, WeeklyShopperError
from .websocket_api import async_register_commands

type WeeklyShopperConfigEntry = ConfigEntry[WeeklyShopperData]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_GENERATE = "generate_shopping_list"
SERVICE_IMPORT = "import_data"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async_register_commands(hass)
    hass.http.register_view(ImportView())

    def _data() -> WeeklyShopperData:
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError("Weekly Shopper Planner is not loaded")
        return entries[0].runtime_data

    async def generate(call: ServiceCall) -> None:
        week: date = call.data.get("week") or dt_util.now().date()
        try:
            _data().generate_list(
                logic.monday_of(week).isoformat(),
                all_ingredients=call.data["all_ingredients"],
            )
        except WeeklyShopperError as err:
            raise ServiceValidationError(str(err)) from err

    async def import_file(call: ServiceCall) -> None:
        path = Path(hass.config.path(call.data["path"]))  # relativa a /config
        if not hass.config.is_allowed_path(str(path)):
            raise ServiceValidationError(f"Path not allowed: {path}")
        try:
            text = await hass.async_add_executor_job(path.read_text, "utf-8-sig")
        except OSError as err:
            raise ServiceValidationError(f"Cannot read {path}: {err}") from err
        data = _data()
        try:
            if path.suffix.lower() in (".md", ".markdown"):
                data.import_markdown(text)
            else:
                payload = json.loads(text)
                if not isinstance(payload, dict):
                    raise ServiceValidationError("JSON object expected")
                data.import_payload(payload)
        except json.JSONDecodeError as err:
            raise ServiceValidationError(f"Invalid JSON: {err}") from err
        except WeeklyShopperError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE,
        generate,
        schema=vol.Schema(
            {vol.Optional("week"): cv.date, vol.Optional("all_ingredients", default=False): cv.boolean}
        ),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_IMPORT, import_file, schema=vol.Schema({vol.Required("path"): cv.string})
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WeeklyShopperConfigEntry) -> bool:
    data = WeeklyShopperData(hass)
    await data.async_load()
    entry.runtime_data = data
    integration = await async_get_integration(hass, DOMAIN)
    await async_register_panel(hass, str(integration.version))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WeeklyShopperConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        async_remove_panel(hass)
        await entry.runtime_data.async_flush()
    return unloaded

