"""Constantes de Weekly Shopper Planner."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "weekly_shopper"
PLATFORMS = [Platform.TODO, Platform.SENSOR]

SIGNAL_CHANGED = f"{DOMAIN}_changed"

STORAGE_VERSION = 1
STORAGE_MINOR_VERSION = 1
STORE_RECIPES = f"{DOMAIN}.recipes"
STORE_MEAL_PLANS = f"{DOMAIN}.meal_plans"
STORE_SHOPPING_LISTS = f"{DOMAIN}.shopping_lists"
STORE_HISTORY = f"{DOMAIN}.history"
SAVE_DELAY = 1

PANEL_URL_PATH = "weekly-shopper"
PANEL_COMPONENT = "weekly-shopper-panel"
STATIC_URL = "/weekly_shopper_static"
IMPORT_URL = "/api/weekly_shopper/import"

MEALS = ("comida", "cena")
MAX_POSITION = 1

SCOPE_RECIPES = "recipes"
SCOPE_MEAL_PLAN = "meal_plan"
SCOPE_SHOPPING_LIST = "shopping_list"

SOURCE_PLANNER = "planner"
SOURCE_MANUAL = "manual"

NATIVE_FORMAT = "weekly-shopper-planner"
NATIVE_VERSION = 1
