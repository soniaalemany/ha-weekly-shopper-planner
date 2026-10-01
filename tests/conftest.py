import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weekly_shopper.const import DOMAIN

WEEK = "2026-09-28"  # lunes


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Permite cargar custom_components en todos los tests."""
    yield


@pytest.fixture
async def setup_integration(hass):
    """Integración instalada y cargada."""
    assert await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Weekly Shopper Planner")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
def data(setup_integration):
    return setup_integration.runtime_data
