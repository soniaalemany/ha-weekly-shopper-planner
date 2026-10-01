"""Lógica pura (sin Home Assistant)."""
from custom_components.weekly_shopper import logic
from custom_components.weekly_shopper.models import (
    Ingredient,
    MealPlanEntry,
    Recipe,
    ShoppingItem,
)


def _recipes():
    pasta = Recipe(
        name="Pasta",
        servings=2,
        ingredients=[
            Ingredient("Tomate", 200, "g"),
            Ingredient("Sal"),
            Ingredient("Pasta", 100, "g"),
        ],
    )
    sopa = Recipe(name="Sopa", servings=4, ingredients=[Ingredient("tomate", 100, "G")])
    return {pasta.id: pasta, sopa.id: sopa}, pasta, sopa


def test_accumulates_and_scales_by_servings():
    recipes, pasta, sopa = _recipes()
    entries = [
        MealPlanEntry(0, "comida", 0, pasta.id, servings=4,
                      selected_ingredient_ids=[i.id for i in pasta.ingredients]),
        MealPlanEntry(1, "cena", 0, sopa.id, selected_ingredient_ids=[sopa.ingredients[0].id]),
    ]
    items = {i.name.lower(): i for i in logic.build_planner_items("2026-09-28", entries, recipes)}
    assert items["tomate"].quantity == 500  # 200*2 + 100 (misma clave nombre+unidad)
    assert items["pasta"].quantity == 200
    assert items["sal"].quantity is None  # sin cantidad, se conserva
    assert all(i.source == "planner" for i in items.values())


def test_only_selected_ingredients_count_unless_include_all():
    recipes, pasta, _ = _recipes()
    entry = MealPlanEntry(0, "comida", 0, pasta.id, selected_ingredient_ids=[pasta.ingredients[0].id])
    assert [i.name for i in logic.build_planner_items("2026-09-28", [entry], recipes)] == ["Tomate"]
    assert len(logic.build_planner_items("2026-09-28", [entry], recipes, include_all=True)) == 3


def test_planner_item_ids_are_stable():
    recipes, pasta, _ = _recipes()
    entry = MealPlanEntry(0, "comida", 0, pasta.id, selected_ingredient_ids=[pasta.ingredients[0].id])
    a = logic.build_planner_items("2026-09-28", [entry], recipes)
    b = logic.build_planner_items("2026-09-28", [entry], recipes)
    other = logic.build_planner_items("2026-10-05", [entry], recipes)
    assert a[0].id == b[0].id != other[0].id


def test_merge_keeps_manual_items_and_checked_state():
    recipes, pasta, _ = _recipes()
    entry = MealPlanEntry(0, "comida", 0, pasta.id, selected_ingredient_ids=[pasta.ingredients[0].id])
    first = logic.build_planner_items("2026-09-28", [entry], recipes)
    first[0].checked = True
    manual = ShoppingItem("Pan", checked=True, source="manual")
    merged = logic.merge_shopping_items([manual, *first], logic.build_planner_items("2026-09-28", [entry], recipes))
    assert merged[0] is manual and merged[0].checked
    assert merged[1].checked  # el estado «comprado» del planificador sobrevive


def test_compact_positions_fills_gaps():
    entries = [
        MealPlanEntry(0, "comida", 1, "b"),
        MealPlanEntry(2, "cena", 0, "c"),
    ]
    result = logic.compact_positions(entries)
    assert sorted((e.slot, e.recipe_id) for e in result) == [((0, "comida", 0), "b"), ((2, "cena", 0), "c")]


def test_set_slot_clear_promotes_second_dish():
    entries = [MealPlanEntry(0, "comida", 0, "a"), MealPlanEntry(0, "comida", 1, "b")]
    result = logic.set_slot(entries, 0, "comida", 0, None)
    assert [(e.slot, e.recipe_id) for e in result] == [((0, "comida", 0), "b")]


def test_set_slot_keeps_selection_when_same_recipe():
    entries = [MealPlanEntry(0, "comida", 0, "a", selected_ingredient_ids=["x"])]
    same = logic.set_slot(entries, 0, "comida", 0, "a", servings=3)
    assert same[0].selected_ingredient_ids == ["x"] and same[0].servings == 3
    other = logic.set_slot(same, 0, "comida", 0, "b")
    assert other[0].selected_ingredient_ids == []


def test_move_swaps_when_target_occupied():
    entries = [MealPlanEntry(0, "comida", 0, "a"), MealPlanEntry(1, "cena", 0, "b")]
    result = logic.move_slot(entries, (0, "comida", 0), (1, "cena", 0))
    assert {e.slot: e.recipe_id for e in result} == {(1, "cena", 0): "a", (0, "comida", 0): "b"}


def test_move_to_empty_slot_and_missing_source():
    entries = [MealPlanEntry(0, "comida", 0, "a")]
    result = logic.move_slot(entries, (0, "comida", 0), (3, "cena", 0))
    assert [(e.slot, e.recipe_id) for e in result] == [((3, "cena", 0), "a")]
    try:
        logic.move_slot(result, (6, "cena", 0), (0, "comida", 0))
    except KeyError:
        pass
    else:
        raise AssertionError("debía fallar")


def test_parse_quantity():
    assert logic.parse_quantity("2 kg") == (2.0, "kg")
    assert logic.parse_quantity("1,5") == (1.5, None)
    assert logic.parse_quantity("un puñado") == (None, "un puñado")
    assert logic.parse_quantity("") == (None, None)
