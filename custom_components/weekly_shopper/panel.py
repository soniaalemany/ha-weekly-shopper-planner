"""Registro del panel personalizado en la barra lateral."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_COMPONENT, PANEL_URL_PATH, STATIC_URL

FRONTEND_DIR = Path(__file__).parent / "frontend"
_STATIC_FLAG = f"{DOMAIN}_static_registered"


async def async_register_panel(hass: HomeAssistant, version: str) -> None:
    if not hass.data.get(_STATIC_FLAG):  # las rutas estáticas no se pueden quitar
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
        )
        hass.data[_STATIC_FLAG] = True
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT,
        frontend_url_path=PANEL_URL_PATH,
        module_url=f"{STATIC_URL}/{PANEL_COMPONENT}.js?v={version}",
        sidebar_title="Menú semanal",
        sidebar_icon="mdi:food",
        require_admin=False,
    )


def async_remove_panel(hass: HomeAssistant) -> None:
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
