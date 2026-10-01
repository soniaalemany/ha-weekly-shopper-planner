"""Comprueba que el entorno de desarrollo funciona (Fase 0)."""
from homeassistant.core import HomeAssistant


async def test_hass_fixture_works(hass: HomeAssistant) -> None:
    assert hass.is_running
