"""Importación y exportación: JSON externo, Markdown y formato nativo v1.

Los parsers no tocan el almacenamiento: validan todo el fichero y devuelven un
``ImportBundle`` que ``WeeklyShopperData.async_apply_import`` aplica de una vez
(así un fichero inválido nunca deja datos a medias).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from .const import NATIVE_FORMAT, NATIVE_VERSION, SOURCE_MANUAL
from .logic import ingredient_key
from .models import (
    Ingredient,
    MealPlan,
    MealPlanEntry,
    Recipe,
    ShoppingItem,
    UsageEntry,
)

WEEK_INDEX_EPOCH = date(1970, 1, 5)

_QUANTITY_RE = re.compile(
    r"(?P<quantity>\d+(?:[.,]\d+)?)(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?"
    r"(?:\s*(?P<unit>[^\d,.;()]+?))?(?=\s*(?:\(|$|,|;))",
    re.IGNORECASE,
)


class ImportDataError(ValueError):
    """Fichero de importación inválido."""


@dataclass
class ImportBundle:
    recipes: dict[str, Recipe] = field(default_factory=dict)
    plans: dict[str, list[MealPlanEntry]] = field(default_factory=dict)
    usages: list[UsageEntry] = field(default_factory=list)
    manual_items: dict[str, list[ShoppingItem]] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------- helpers
def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _week_date(value: Any) -> date | None:
    """Convierte el índice de semana del export externo (semanas desde 1970-01-05)."""
    if isinstance(value, (int, float)) and int(value) == value:
        return WEEK_INDEX_EPOCH + timedelta(weeks=int(value))
    return _date(value)


def _active(row: dict[str, Any]) -> bool:
    return not row.get("deletedAt")


def _recipe_by_name(recipes: dict[str, Recipe], name: str) -> Recipe | None:
    return next((r for r in recipes.values() if r.name == name), None)


def _reuse_ingredient_ids(old: list[Ingredient], new: list[Ingredient]) -> None:
    """Conserva los id de ingredientes existentes con la misma clave (nombre+unidad)."""
    by_key = {ingredient_key(i.name, i.unit): i.id for i in old}
    for ingredient in new:
        key = ingredient_key(ingredient.name, ingredient.unit)
        if key in by_key:
            ingredient.id = by_key.pop(key)


# -------------------------------------------------------------------- Markdown
def parse_markdown_recipes(content: str) -> list[dict[str, Any]]:
    """Recetas como `## Nombre` seguido de `- Ingrediente: cantidad`."""
    parsed: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = {"name": heading.group(1).strip(), "ingredients": []}
            parsed.append(current)
            continue
        if current is None or not line.startswith("-"):
            continue
        ingredient_line = line[1:].strip()
        if ":" not in ingredient_line:
            continue
        name, details = (part.strip() for part in ingredient_line.split(":", 1))
        if not name:
            continue
        match = _QUANTITY_RE.search(details)
        quantity = unit = None
        if match:
            quantity = _number(match.group("quantity").replace(",", "."))
            unit = _text(match.group("unit")) or None
        current["ingredients"].append({"name": name, "quantity": quantity, "unit": unit})
    return [r for r in parsed if r["ingredients"]]


def import_markdown(existing: dict[str, Recipe], content: str) -> ImportBundle:
    sources = parse_markdown_recipes(content)
    bundle = ImportBundle()
    new_recipes = ingredients = 0
    staged: dict[str, Recipe] = dict(existing)
    for source in sources:
        name = _text(source["name"])
        recipe = _recipe_by_name(staged, name)
        if recipe is None:
            recipe = Recipe(name=name, servings=2)
            new_recipes += 1
        old = list(recipe.ingredients)
        recipe = Recipe.from_dict(recipe.to_dict())  # copia: no mutar hasta aplicar
        recipe.ingredients = [
            Ingredient(name=i["name"], quantity=i["quantity"], unit=i["unit"])
            for i in source["ingredients"]
        ]
        _reuse_ingredient_ids(old, recipe.ingredients)
        ingredients += len(recipe.ingredients)
        bundle.recipes[recipe.id] = recipe
        staged[recipe.id] = recipe
    bundle.counts = {
        "recipes": len(sources),
        "new_recipes": new_recipes,
        "ingredients": ingredients,
    }
    return bundle


# ------------------------------------------------------------- JSON externo
def import_external(
    existing: dict[str, Recipe],
    existing_plans: dict[str, MealPlan],
    payload: dict[str, Any],
) -> ImportBundle:
    products = {
        str(r.get("id")): r
        for r in payload.get("products", [])
        if isinstance(r, dict) and r.get("id") and _active(r) and _text(r.get("name"))
    }
    ext_recipes = {
        str(r.get("id")): r
        for r in payload.get("recipes", [])
        if isinstance(r, dict) and r.get("id") and _active(r) and _text(r.get("name"))
    }
    aisles = {
        str(r.get("id")): _text(r.get("name"))
        for r in payload.get("aisles", [])
        if isinstance(r, dict) and r.get("id")
    }
    product_aisle = {
        str(r.get("productId", r.get("product_id"))): aisles.get(
            str(r.get("aisleId", r.get("aisle_id"))), ""
        )
        for r in payload.get("product_aisles", [])
        if isinstance(r, dict)
    }

    bundle = ImportBundle()
    staged: dict[str, Recipe] = {}
    local_ids: dict[str, str] = {}  # id externo -> id local
    new_recipes = 0
    for ext_id, source in ext_recipes.items():
        name = _text(source["name"])
        recipe = _recipe_by_name(existing, name) or _recipe_by_name(staged, name)
        if recipe is None:
            recipe = Recipe(name=name, servings=4)
            new_recipes += 1
        else:
            recipe = staged.get(recipe.id) or Recipe.from_dict(recipe.to_dict())
        staged[recipe.id] = recipe
        local_ids[ext_id] = recipe.id

    grouped: dict[str, list[Ingredient]] = {}
    relations = payload.get("products_recipies", payload.get("products_recipes", []))
    for relation in relations:
        if not isinstance(relation, dict) or not _active(relation):
            continue
        recipe_key = str(relation.get("recipeId", relation.get("recipe_id")))
        product_key = str(relation.get("productId", relation.get("product_id")))
        local = local_ids.get(recipe_key)
        product = products.get(product_key)
        if local is None or product is None:
            continue
        grouped.setdefault(local, []).append(
            Ingredient(
                name=_text(product["name"]),
                quantity=_number(relation.get("amount", relation.get("quantity"))),
                unit=_text(relation.get("unit")) or None,
                category=product_aisle.get(product_key) or None,
            )
        )
    ingredient_count = 0
    for local, ingredients in grouped.items():
        recipe = staged[local]
        _reuse_ingredient_ids(recipe.ingredients, ingredients)
        recipe.ingredients = ingredients
        ingredient_count += len(ingredients)

    plans: dict[str, list[MealPlanEntry]] = {}
    new_weeks = 0
    usages: list[UsageEntry] = []
    positions: dict[tuple[str, int, str], int] = {}
    for source in payload.get("schedule", []):
        if not isinstance(source, dict) or not _active(source):
            continue
        monday = _week_date(source.get("week", source.get("monday")))
        recipe_id = local_ids.get(str(source.get("recipeId", source.get("recipe_id"))))
        if monday is None or monday.weekday() != 0 or recipe_id is None:
            continue
        try:
            day = int(source.get("day", source.get("day_of_week", 0)))
        except (TypeError, ValueError):
            continue
        if not 0 <= day <= 6:
            continue
        key = monday.isoformat()
        if key not in plans:
            current = existing_plans.get(key)
            plans[key] = [MealPlanEntry.from_dict(e.to_dict()) for e in current.entries] if current else []
            if current is None:
                new_weeks += 1
        meal = _text(source.get("meal", source.get("mealType", "comida"))) or "comida"
        pos_key = (key, day, meal)
        position = positions.get(pos_key, 0)
        positions[pos_key] = position + 1
        if position <= 1 and not any(e.slot == (day, meal, position) for e in plans[key]):
            plans[key].append(MealPlanEntry(day=day, meal=meal, position=position, recipe_id=recipe_id))
        usages.append(
            UsageEntry(
                recipe_id,
                key,
                meal,
                datetime.combine(monday + timedelta(days=day), time.min).isoformat(),
            )
        )

    bundle.recipes = staged
    bundle.plans = plans
    bundle.usages = usages
    bundle.counts = {
        "recipes": len(ext_recipes),
        "new_recipes": new_recipes,
        "ingredients": ingredient_count,
        "plans": new_weeks,
        "usages": len(usages),
    }
    return bundle


# ------------------------------------------------------------------ nativo v1
def export_data(
    recipes: dict[str, Recipe],
    plans: dict[str, MealPlan],
    lists: dict[str, Any],
    history: list[UsageEntry],
) -> dict[str, Any]:
    return {
        "format": NATIVE_FORMAT,
        "version": NATIVE_VERSION,
        "exported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "recipes": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "instructions": r.instructions,
                "servings": r.servings,
                "prep_minutes": r.prep_minutes,
                "ingredients": [i.to_dict() for i in r.ingredients],
            }
            for r in sorted(recipes.values(), key=lambda r: r.name.lower())
        ],
        "meal_plans": [
            {
                "monday": monday,
                "entries": [
                    {
                        "day_of_week": e.day,
                        "meal_type": e.meal,
                        "position": e.position,
                        "recipe_id": e.recipe_id,
                        "servings": e.servings,
                        "selected_ingredient_ids": list(e.selected_ingredient_ids),
                    }
                    for e in sorted(plan.entries, key=lambda e: e.slot)
                ],
            }
            for monday, plan in sorted(plans.items())
        ],
        "manual_shopping_items": [
            {"monday": monday, "items": [i.to_dict() for i in lst.items if i.source == SOURCE_MANUAL]}
            for monday, lst in sorted(lists.items())
            if any(i.source == SOURCE_MANUAL for i in lst.items)
        ],
        "usage_history": [
            {"recipe_id": u.recipe_id, "monday": u.monday, "meal_type": u.meal, "used_at": u.used_at}
            for u in sorted(history, key=lambda u: u.used_at)
            if u.recipe_id in recipes
        ],
    }


def import_native(existing: dict[str, Recipe], payload: dict[str, Any]) -> ImportBundle:
    if payload.get("version") != NATIVE_VERSION:
        raise ImportDataError(f"Unsupported export version: {payload.get('version')}")
    source_recipes = payload.get("recipes")
    source_plans = payload.get("meal_plans", [])
    source_usages = payload.get("usage_history", [])
    source_lists = payload.get("manual_shopping_items", [])
    if not all(isinstance(x, list) for x in (source_recipes, source_plans, source_usages, source_lists)):
        raise ImportDataError("Invalid export structure")

    bundle = ImportBundle()
    by_exported_id: dict[str, Recipe] = {}
    created = updated = ingredient_count = 0
    for source in source_recipes:
        if not isinstance(source, dict) or not _text(source.get("id")) or not _text(source.get("name")):
            raise ImportDataError("Each exported recipe requires id and name")
        exported_id = _text(source["id"])
        current = existing.get(exported_id) or _recipe_by_name(existing, _text(source["name"]))
        if current is None:
            recipe = Recipe(id=exported_id, name=_text(source["name"]), servings=4)
            created += 1
        else:
            recipe = Recipe.from_dict(current.to_dict())
            updated += 1
        for attr in ("name", "description", "instructions", "servings", "prep_minutes"):
            if attr in source:
                setattr(recipe, attr, source[attr])
        raw = source.get("ingredients", [])
        if not isinstance(raw, list):
            raise ImportDataError(f"Invalid ingredients for recipe {exported_id}")
        old = list(recipe.ingredients)
        recipe.ingredients = [
            Ingredient.from_dict(i)
            for i in raw
            if isinstance(i, dict) and _text(i.get("name"))
        ]
        if not any(isinstance(i, dict) and i.get("id") for i in raw):
            _reuse_ingredient_ids(old, recipe.ingredients)
        ingredient_count += len(recipe.ingredients)
        bundle.recipes[recipe.id] = recipe
        by_exported_id[exported_id] = recipe

    new_weeks = 0
    for source in source_plans:
        if not isinstance(source, dict):
            raise ImportDataError("Invalid meal plan")
        monday = _date(source.get("monday"))
        if monday is None or monday.weekday() != 0:
            raise ImportDataError("Meal plan monday must be a Monday")
        raw_entries = source.get("entries", [])
        if not isinstance(raw_entries, list):
            raise ImportDataError("Invalid meal plan entries")
        entries: list[MealPlanEntry] = []
        for item in raw_entries:
            if not isinstance(item, dict):
                raise ImportDataError("Invalid meal plan entry")
            recipe = by_exported_id.get(_text(item.get("recipe_id")))
            if recipe is None:
                raise ImportDataError(f"Unknown recipe reference: {item.get('recipe_id')}")
            try:
                entry = MealPlanEntry(
                    day=int(item["day_of_week"]),
                    meal=_text(item["meal_type"]),
                    position=int(item.get("position", 0)),
                    recipe_id=recipe.id,
                    servings=item.get("servings"),
                    selected_ingredient_ids=list(item.get("selected_ingredient_ids", [])),
                )
            except (KeyError, TypeError, ValueError) as err:
                raise ImportDataError("Invalid meal plan entry") from err
            if not 0 <= entry.day <= 6 or entry.position not in (0, 1) or not entry.meal:
                raise ImportDataError("Invalid meal plan entry")
            valid = {i.id for i in recipe.ingredients}
            entry.selected_ingredient_ids = [i for i in entry.selected_ingredient_ids if i in valid]
            entries.append(entry)
        if len({e.slot for e in entries}) != len(entries):
            raise ImportDataError("Duplicate recipe position in meal slot")
        bundle.plans[monday.isoformat()] = entries
        new_weeks += 1

    for source in source_lists:
        if not isinstance(source, dict) or _date(source.get("monday")) is None:
            raise ImportDataError("Invalid shopping list")
        bundle.manual_items[_date(source["monday"]).isoformat()] = [
            ShoppingItem.from_dict({**i, "source": SOURCE_MANUAL})
            for i in source.get("items", [])
            if isinstance(i, dict) and _text(i.get("name"))
        ]

    for source in source_usages:
        if not isinstance(source, dict):
            raise ImportDataError("Invalid usage history entry")
        recipe = by_exported_id.get(_text(source.get("recipe_id")))
        if recipe is None:
            raise ImportDataError(f"Unknown usage recipe reference: {source.get('recipe_id')}")
        used_at = _text(source.get("used_at")).replace("Z", "") or datetime.now(UTC).replace(tzinfo=None).isoformat()
        bundle.usages.append(
            UsageEntry(recipe.id, _text(source.get("monday")) or None, source.get("meal_type"), used_at)
        )

    bundle.counts = {
        "recipes": len(source_recipes),
        "new_recipes": created,
        "updated_recipes": updated,
        "ingredients": ingredient_count,
        "plans": new_weeks,
        "usages": len(bundle.usages),
    }
    return bundle
