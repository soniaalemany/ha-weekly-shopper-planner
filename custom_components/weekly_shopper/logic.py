"""Lógica de dominio pura (sin dependencias de Home Assistant)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5

from .const import MAX_POSITION, SOURCE_MANUAL, SOURCE_PLANNER
from .models import MealPlanEntry, Recipe, ShoppingItem, UsageEntry


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def ingredient_key(name: str, unit: str | None) -> tuple[str, str]:
    return (name.strip().lower(), (unit or "").strip().lower())


def compact_positions(entries: list[MealPlanEntry]) -> list[MealPlanEntry]:
    """Renumera las posiciones de cada hueco (0, 1, …) y descarta el exceso."""
    grouped: dict[tuple[int, str], list[MealPlanEntry]] = defaultdict(list)
    for entry in entries:
        grouped[(entry.day, entry.meal)].append(entry)
    result: list[MealPlanEntry] = []
    for (day, meal), group in sorted(grouped.items()):
        for position, entry in enumerate(sorted(group, key=lambda e: e.position)):
            if position > MAX_POSITION:
                break
            entry.position = position
            result.append(entry)
    return result


def set_slot(
    entries: list[MealPlanEntry],
    day: int,
    meal: str,
    position: int,
    recipe_id: str | None,
    servings: int | None = None,
    selected_ingredient_ids: list[str] | None = None,
) -> list[MealPlanEntry]:
    """Asigna (o vacía, si recipe_id es None) un hueco y compacta posiciones."""
    existing = next((e for e in entries if e.slot == (day, meal, position)), None)
    others = [e for e in entries if e is not existing]
    if recipe_id is not None:
        keep_selection = (
            existing.selected_ingredient_ids
            if existing and existing.recipe_id == recipe_id
            else []
        )
        others.append(
            MealPlanEntry(
                day=day,
                meal=meal,
                position=position,
                recipe_id=recipe_id,
                servings=servings,
                selected_ingredient_ids=(
                    list(selected_ingredient_ids)
                    if selected_ingredient_ids is not None
                    else list(keep_selection)
                ),
            )
        )
    return compact_positions(others)


def move_slot(
    entries: list[MealPlanEntry],
    source: tuple[int, str, int],
    target: tuple[int, str, int],
) -> list[MealPlanEntry]:
    """Mueve una receta a otro hueco; si está ocupado, las intercambia."""
    if source == target:
        return compact_positions(entries)
    src = next((e for e in entries if e.slot == source), None)
    if src is None:
        raise KeyError("source slot is empty")
    dst = next((e for e in entries if e.slot == target), None)
    src.day, src.meal, src.position = target
    if dst is not None:
        dst.day, dst.meal, dst.position = source
    return compact_positions(entries)


def _planner_item_id(monday: str, key: tuple[str, str]) -> str:
    return str(uuid5(NAMESPACE_URL, f"weekly_shopper:{monday}:{key[0]}|{key[1]}"))


def build_planner_items(
    monday: str,
    entries: list[MealPlanEntry],
    recipes: dict[str, Recipe],
    include_all: bool = False,
) -> list[ShoppingItem]:
    """Acumula ingredientes (escalados por raciones) en artículos de la compra.

    Por defecto solo cuentan los ingredientes marcados en cada hueco del menú.
    """
    totals: dict[tuple[str, str], float] = defaultdict(float)
    meta: dict[tuple[str, str], object] = {}
    for entry in sorted(entries, key=lambda e: e.slot):
        recipe = recipes.get(entry.recipe_id)
        if recipe is None:
            continue
        scale = (entry.servings or recipe.servings) / recipe.servings
        selected = set(entry.selected_ingredient_ids)
        for ingredient in recipe.ingredients:
            if not include_all and ingredient.id not in selected:
                continue
            key = ingredient_key(ingredient.name, ingredient.unit)
            if ingredient.quantity is not None:
                totals[key] += ingredient.quantity * scale
            meta[key] = ingredient
    items: list[ShoppingItem] = []
    for key, total in sorted(totals.items()):
        src = meta[key]
        items.append(
            ShoppingItem(
                id=_planner_item_id(monday, key),
                name=src.name,
                quantity=round(total, 4),
                unit=src.unit,
                category=src.category,
                source=SOURCE_PLANNER,
            )
        )
    for key, src in meta.items():
        if key not in totals:
            items.append(
                ShoppingItem(
                    id=_planner_item_id(monday, key),
                    name=src.name,
                    unit=src.unit,
                    category=src.category,
                    source=SOURCE_PLANNER,
                )
            )
    return items


def merge_shopping_items(
    existing: list[ShoppingItem], planner_items: list[ShoppingItem]
) -> list[ShoppingItem]:
    """Conserva los artículos manuales y el estado «comprado» de los del planificador."""
    manual = [i for i in existing if i.source == SOURCE_MANUAL]
    checked = {i.id for i in existing if i.source == SOURCE_PLANNER and i.checked}
    for item in planner_items:
        item.checked = item.id in checked
    return manual + planner_items


def usage_rows(
    monday: str,
    entries: list[MealPlanEntry],
    previous: list[UsageEntry],
) -> list[UsageEntry]:
    """Filas de historial de una semana: una por (receta, comida)."""
    start = date.fromisoformat(monday)
    known = {(u.recipe_id, u.meal): u.used_at for u in previous if u.monday == monday}
    rows: dict[tuple[str, str], UsageEntry] = {}
    for entry in sorted(entries, key=lambda e: e.slot):
        key = (entry.recipe_id, entry.meal)
        if key in rows:
            continue
        used_at = known.get(key) or datetime.combine(
            start + timedelta(days=entry.day), time.min
        ).isoformat()
        rows[key] = UsageEntry(entry.recipe_id, monday, entry.meal, used_at)
    return list(rows.values())


def parse_quantity(value: str) -> tuple[float | None, str | None]:
    """«2 kg» → (2.0, «kg»); «un puñado» → (None, «un puñado»)."""
    import re

    text = value.strip()
    match = re.match(r"^(-?\d+(?:[.,]\d+)?)(?:\s+(.+))?$", text)
    if not match:
        return None, text or None
    return float(match.group(1).replace(",", ".")), match.group(2) or None


def format_quantity(quantity: float | None, unit: str | None) -> str:
    parts = []
    if quantity is not None:
        parts.append(f"{quantity:g}")
    if unit:
        parts.append(unit)
    return " ".join(parts)
