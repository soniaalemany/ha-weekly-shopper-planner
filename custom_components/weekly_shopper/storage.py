"""Datos en memoria + persistencia con ``helpers.storage.Store``."""
from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from . import importer, logic
from .const import (
    MEALS,
    SAVE_DELAY,
    SCOPE_MEAL_PLAN,
    SCOPE_RECIPES,
    SCOPE_SHOPPING_LIST,
    SIGNAL_CHANGED,
    SOURCE_MANUAL,
    SOURCE_PLANNER,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
    STORE_HISTORY,
    STORE_MEAL_PLANS,
    STORE_RECIPES,
    STORE_SHOPPING_LISTS,
)
from .models import (
    Ingredient,
    MealPlan,
    MealPlanEntry,
    Recipe,
    ShoppingItem,
    ShoppingList,
    UsageEntry,
)


class WeeklyShopperError(Exception):
    """Error de dominio con un código estable para la API."""

    code = "error"


class NotFound(WeeklyShopperError):
    code = "not_found"


class Conflict(WeeklyShopperError):
    code = "conflict"


class InvalidData(WeeklyShopperError):
    code = "invalid_format"


class RecipeInUse(WeeklyShopperError):
    code = "recipe_in_use"


def migrate_data(key: str, old_major: int, old_minor: int, data: dict[str, Any]) -> dict[str, Any]:
    """Migra el contenido de un store a la versión actual.

    Regla: cambio compatible → ``minor_version``+1; incompatible → ``version``+1
    con una rama nueva aquí y su test. De momento solo existe la versión 1.
    """
    if old_major > STORAGE_VERSION:
        raise NotImplementedError(f"{key}: versión {old_major} más reciente que la soportada")
    return data


class _Store(Store[dict[str, Any]]):
    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        return migrate_data(self.key, old_major_version, old_minor_version, old_data)


def check_monday(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as err:
        raise InvalidData("week must be an ISO date") from err
    if parsed.weekday() != 0:
        raise InvalidData("week must be a Monday")
    return parsed.isoformat()


class WeeklyShopperData:
    """Fuente de verdad del dominio. Todo ocurre en el event loop (sin locks)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._stores = {
            name: _Store(hass, STORAGE_VERSION, name, minor_version=STORAGE_MINOR_VERSION)
            for name in (STORE_RECIPES, STORE_MEAL_PLANS, STORE_SHOPPING_LISTS, STORE_HISTORY)
        }
        self._dirty: set[str] = set()
        self.recipes: dict[str, Recipe] = {}
        self.meal_plans: dict[str, MealPlan] = {}
        self.shopping_lists: dict[str, ShoppingList] = {}
        self.history: list[UsageEntry] = []

    # ------------------------------------------------------------ persistencia
    async def async_load(self) -> None:
        recipes = await self._stores[STORE_RECIPES].async_load() or {}
        plans = await self._stores[STORE_MEAL_PLANS].async_load() or {}
        lists = await self._stores[STORE_SHOPPING_LISTS].async_load() or {}
        history = await self._stores[STORE_HISTORY].async_load() or {}
        self.recipes = {r["id"]: Recipe.from_dict(r) for r in recipes.get("recipes", [])}
        self.meal_plans = {k: MealPlan.from_dict(v) for k, v in plans.get("plans", {}).items()}
        self.shopping_lists = {k: ShoppingList.from_dict(v) for k, v in lists.get("lists", {}).items()}
        self.history = [UsageEntry.from_dict(u) for u in history.get("history", [])]

    def _serializers(self) -> dict[str, Callable[[], dict[str, Any]]]:
        return {
            STORE_RECIPES: lambda: {"recipes": [r.to_dict() for r in self.recipes.values()]},
            STORE_MEAL_PLANS: lambda: {"plans": {k: v.to_dict() for k, v in self.meal_plans.items()}},
            STORE_SHOPPING_LISTS: lambda: {"lists": {k: v.to_dict() for k, v in self.shopping_lists.items()}},
            STORE_HISTORY: lambda: {"history": [u.to_dict() for u in self.history]},
        }

    def _save(self, *names: str) -> None:
        serializers = self._serializers()
        for name in names:
            self._dirty.add(name)
            self._stores[name].async_delay_save(serializers[name], SAVE_DELAY)

    async def async_flush(self) -> None:
        serializers = self._serializers()
        for name in list(self._dirty):
            await self._stores[name].async_save(serializers[name]())
        self._dirty.clear()

    async def async_remove_stores(self) -> None:
        for store in self._stores.values():
            await store.async_remove()

    def _notify(self, scope: str, week: str | None, revision: int | None, data: Any, origin: str | None) -> None:
        async_dispatcher_send(
            self.hass,
            SIGNAL_CHANGED,
            {"scope": scope, "week": week, "revision": revision, "data": data, "origin": origin},
        )

    # ----------------------------------------------------------------- recetas
    def _usage_stats(self) -> dict[str, tuple[int, str | None]]:
        stats: dict[str, tuple[int, str | None]] = {}
        for usage in self.history:
            count, last = stats.get(usage.recipe_id, (0, None))
            stats[usage.recipe_id] = (count + 1, max(last or usage.used_at, usage.used_at))
        return stats

    def recipe_dict(self, recipe: Recipe, stats: dict | None = None) -> dict[str, Any]:
        count, last = (stats if stats is not None else self._usage_stats()).get(recipe.id, (0, None))
        return {**recipe.to_dict(), "usage_count": count, "last_used_date": last[:10] if last else None}

    def list_recipes(self) -> list[dict[str, Any]]:
        stats = self._usage_stats()
        return [
            self.recipe_dict(r, stats)
            for r in sorted(self.recipes.values(), key=lambda r: r.name.lower())
        ]

    def get_recipe(self, recipe_id: str) -> Recipe:
        recipe = self.recipes.get(recipe_id)
        if recipe is None:
            raise NotFound(f"Recipe {recipe_id} not found")
        return recipe

    def _notify_recipes(self, origin: str | None) -> None:
        self._notify(SCOPE_RECIPES, None, None, self.list_recipes(), origin)

    def create_recipe(self, values: dict[str, Any], origin: str | None = None) -> dict[str, Any]:
        recipe = Recipe(
            name=values["name"].strip(),
            servings=values.get("servings") or 4,
            description=values.get("description"),
            instructions=values.get("instructions"),
            prep_minutes=values.get("prep_minutes"),
            ingredients=[Ingredient.from_dict(i) for i in values.get("ingredients", [])],
        )
        self.recipes[recipe.id] = recipe
        self._save(STORE_RECIPES)
        self._notify_recipes(origin)
        return self.recipe_dict(recipe)

    def update_recipe(self, recipe_id: str, values: dict[str, Any], origin: str | None = None) -> dict[str, Any]:
        recipe = self.get_recipe(recipe_id)
        for attr in ("name", "description", "instructions", "servings", "prep_minutes"):
            if attr in values:
                setattr(recipe, attr, values[attr])
        if "ingredients" in values:
            old = list(recipe.ingredients)
            new = [Ingredient.from_dict(i) for i in values["ingredients"]]
            # los que llegan sin id conservan el de un ingrediente equivalente
            keyed = {logic.ingredient_key(i.name, i.unit): i.id for i in old}
            for raw, ingredient in zip(values["ingredients"], new, strict=True):
                if not raw.get("id"):
                    ingredient.id = keyed.pop(logic.ingredient_key(ingredient.name, ingredient.unit), ingredient.id)
            recipe.ingredients = new
        self._save(STORE_RECIPES)
        self._after_recipe_change(recipe_id, origin)
        self._notify_recipes(origin)
        return self.recipe_dict(recipe)

    def delete_recipe(self, recipe_id: str, origin: str | None = None) -> None:
        self.get_recipe(recipe_id)
        if any(e.recipe_id == recipe_id for p in self.meal_plans.values() for e in p.entries):
            raise RecipeInUse("Recipe is used in a meal plan")
        del self.recipes[recipe_id]
        self.history = [u for u in self.history if u.recipe_id != recipe_id]
        self._save(STORE_RECIPES, STORE_HISTORY)
        self._notify_recipes(origin)

    def _after_recipe_change(self, recipe_id: str, origin: str | None) -> None:
        recipe = self.recipes[recipe_id]
        valid = {i.id for i in recipe.ingredients}
        for monday, plan in self.meal_plans.items():
            touched = False
            for entry in plan.entries:
                if entry.recipe_id == recipe_id:
                    kept = [i for i in entry.selected_ingredient_ids if i in valid]
                    if kept != entry.selected_ingredient_ids:
                        entry.selected_ingredient_ids = kept
                    touched = True
            if touched:
                plan.revision += 1
                self._save(STORE_MEAL_PLANS)
                self._notify(SCOPE_MEAL_PLAN, monday, plan.revision, plan.to_dict(), origin)
                self._regenerate(monday, origin)

    # -------------------------------------------------------------------- menú
    def get_plan(self, monday: str) -> MealPlan:
        return self.meal_plans.get(check_monday(monday)) or MealPlan()

    def _commit_plan(self, monday: str, entries: list[MealPlanEntry], origin: str | None) -> MealPlan:
        plan = self.meal_plans.setdefault(monday, MealPlan())
        plan.entries = entries
        plan.revision += 1
        self.history = [u for u in self.history if u.monday != monday] + logic.usage_rows(
            monday, entries, self.history
        )
        self._save(STORE_MEAL_PLANS, STORE_HISTORY)
        self._notify(SCOPE_MEAL_PLAN, monday, plan.revision, plan.to_dict(), origin)
        self._regenerate(monday, origin)
        self._notify_recipes(origin)  # cambian last_used_date / usage_count
        return plan

    def set_slot(
        self,
        monday: str,
        day: int,
        meal: str,
        position: int,
        recipe_id: str | None,
        servings: int | None = None,
        selected_ingredient_ids: list[str] | None = None,
        origin: str | None = None,
    ) -> MealPlan:
        monday = check_monday(monday)
        if meal not in MEALS:
            raise InvalidData(f"meal must be one of {MEALS}")
        selected = selected_ingredient_ids
        if recipe_id is not None:
            recipe = self.get_recipe(recipe_id)
            if selected is not None:
                valid = {i.id for i in recipe.ingredients}
                selected = [i for i in selected if i in valid]
        current = self.get_plan(monday)
        entries = [MealPlanEntry.from_dict(e.to_dict()) for e in current.entries]
        entries = logic.set_slot(entries, day, meal, position, recipe_id, servings, selected)
        return self._commit_plan(monday, entries, origin)

    def move_slot(
        self,
        monday: str,
        source: tuple[int, str, int],
        target: tuple[int, str, int],
        base_revision: int | None = None,
        origin: str | None = None,
    ) -> MealPlan:
        monday = check_monday(monday)
        current = self.get_plan(monday)
        if base_revision is not None and base_revision != current.revision:
            raise Conflict("meal plan changed")
        if target[1] not in MEALS:
            raise InvalidData(f"meal must be one of {MEALS}")
        entries = [MealPlanEntry.from_dict(e.to_dict()) for e in current.entries]
        try:
            entries = logic.move_slot(entries, source, target)
        except KeyError as err:
            raise NotFound("source slot is empty") from err
        return self._commit_plan(monday, entries, origin)

    # ------------------------------------------------------------------ compra
    def get_list(self, monday: str) -> ShoppingList:
        return self.shopping_lists.get(check_monday(monday)) or ShoppingList()

    def _commit_list(self, monday: str, items: list[ShoppingItem], origin: str | None) -> ShoppingList:
        lst = self.shopping_lists.setdefault(monday, ShoppingList())
        lst.items = items
        lst.revision += 1
        self._save(STORE_SHOPPING_LISTS)
        self._notify(SCOPE_SHOPPING_LIST, monday, lst.revision, lst.to_dict(), origin)
        return lst

    def _regenerate(self, monday: str, origin: str | None) -> None:
        plan = self.meal_plans.get(monday)
        if plan is None:
            return
        existing = self.shopping_lists.get(monday)
        old_items = existing.items if existing else []
        planner_items = logic.build_planner_items(monday, plan.entries, self.recipes)
        merged = logic.merge_shopping_items(old_items, planner_items)
        if existing is None and not merged:
            return
        if [i.to_dict() for i in merged] == [i.to_dict() for i in old_items]:
            return
        self._commit_list(monday, merged, origin)

    def generate_list(
        self,
        monday: str,
        base_revision: int | None = None,
        all_ingredients: bool = False,
        origin: str | None = None,
    ) -> ShoppingList:
        monday = check_monday(monday)
        plan = self.meal_plans.get(monday)
        if plan is None:
            raise NotFound("Meal plan not found")
        lst = self.get_list(monday)
        if base_revision is not None and base_revision != lst.revision:
            raise Conflict("shopping list changed")
        if all_ingredients:
            for entry in plan.entries:
                recipe = self.recipes.get(entry.recipe_id)
                if recipe:
                    entry.selected_ingredient_ids = [i.id for i in recipe.ingredients]
            plan.revision += 1
            self._save(STORE_MEAL_PLANS)
            self._notify(SCOPE_MEAL_PLAN, monday, plan.revision, plan.to_dict(), origin)
        planner_items = logic.build_planner_items(monday, plan.entries, self.recipes)
        merged = logic.merge_shopping_items(lst.items, planner_items)
        return self._commit_list(monday, merged, origin)

    def add_item(self, monday: str, values: dict[str, Any], origin: str | None = None) -> ShoppingItem:
        monday = check_monday(monday)
        item = ShoppingItem.from_dict({**values, "source": SOURCE_MANUAL})
        if not item.name:
            raise InvalidData("name is required")
        lst = self.get_list(monday)
        self._commit_list(monday, [*lst.items, item], origin)
        return item

    def update_item(self, monday: str, item_id: str, values: dict[str, Any], origin: str | None = None) -> ShoppingItem:
        monday = check_monday(monday)
        lst = self.get_list(monday)
        items = [ShoppingItem.from_dict(i.to_dict()) for i in lst.items]
        item = next((i for i in items if i.id == item_id), None)
        if item is None:
            raise NotFound("Shopping item not found")
        for attr in ("name", "quantity", "unit", "category", "checked"):
            if attr in values:
                setattr(item, attr, values[attr])
        if not item.name.strip():
            raise InvalidData("name is required")
        self._commit_list(monday, items, origin)
        return item

    def delete_item(self, monday: str, item_id: str, origin: str | None = None) -> None:
        monday = check_monday(monday)
        lst = self.get_list(monday)
        item = next((i for i in lst.items if i.id == item_id), None)
        if item is None:
            raise NotFound("Shopping item not found")
        if item.source == SOURCE_PLANNER:
            # des-selecciona el ingrediente para que no reaparezca al regenerar
            key = logic.ingredient_key(item.name, item.unit)
            plan = self.meal_plans.get(monday)
            if plan:
                for entry in plan.entries:
                    recipe = self.recipes.get(entry.recipe_id)
                    if recipe:
                        drop = {i.id for i in recipe.ingredients if logic.ingredient_key(i.name, i.unit) == key}
                        entry.selected_ingredient_ids = [i for i in entry.selected_ingredient_ids if i not in drop]
                plan.revision += 1
                self._save(STORE_MEAL_PLANS)
                self._notify(SCOPE_MEAL_PLAN, monday, plan.revision, plan.to_dict(), origin)
        self._commit_list(monday, [i for i in lst.items if i.id != item_id], origin)

    # ------------------------------------------------------- import / export
    def export(self) -> dict[str, Any]:
        return importer.export_data(self.recipes, self.meal_plans, self.shopping_lists, self.history)

    def import_payload(self, payload: dict[str, Any], origin: str | None = None) -> dict[str, int]:
        try:
            if payload.get("format") == importer.NATIVE_FORMAT:
                bundle = importer.import_native(self.recipes, payload)
            else:
                bundle = importer.import_external(self.recipes, self.meal_plans, payload)
        except importer.ImportDataError as err:
            raise InvalidData(str(err)) from err
        return self._apply_import(bundle, origin)

    def import_markdown(self, content: str, origin: str | None = None) -> dict[str, int]:
        if not content.strip():
            raise InvalidData("Markdown content is required")
        return self._apply_import(importer.import_markdown(self.recipes, content), origin)

    def _apply_import(self, bundle: importer.ImportBundle, origin: str | None) -> dict[str, int]:
        self.recipes.update(bundle.recipes)
        known = {(u.recipe_id, u.monday, u.meal, u.used_at) for u in self.history}
        added = 0
        for usage in bundle.usages:
            key = (usage.recipe_id, usage.monday, usage.meal, usage.used_at)
            if usage.recipe_id in self.recipes and key not in known:
                self.history.append(usage)
                known.add(key)
                added += 1
        bundle.counts["usages"] = added
        self._save(STORE_RECIPES, STORE_HISTORY)
        self._notify_recipes(origin)
        for monday, entries in bundle.plans.items():
            plan = self.meal_plans.setdefault(monday, MealPlan())
            plan.entries = logic.compact_positions(entries)
            plan.revision += 1
            self._save(STORE_MEAL_PLANS)
            self._notify(SCOPE_MEAL_PLAN, monday, plan.revision, plan.to_dict(), origin)
        for monday, items in bundle.manual_items.items():
            lst = self.shopping_lists.get(monday)
            others = [i for i in (lst.items if lst else []) if i.source != SOURCE_MANUAL]
            self._commit_list(monday, items + others, origin)
        for monday in bundle.plans:
            self._regenerate(monday, origin)
        # recetas importadas con ingredientes nuevos: limpia selecciones inválidas
        for recipe_id in bundle.recipes:
            self._after_recipe_change(recipe_id, origin)
        return bundle.counts

    # ----------------------------------------------------------------- consulta
    def day_recipes(self, day: date, meal: str) -> list[str]:
        plan = self.meal_plans.get(logic.monday_of(day).isoformat())
        if plan is None:
            return []
        entries = sorted(
            (e for e in plan.entries if e.day == day.weekday() and e.meal == meal),
            key=lambda e: e.position,
        )
        return [self.recipes[e.recipe_id].name for e in entries if e.recipe_id in self.recipes]
