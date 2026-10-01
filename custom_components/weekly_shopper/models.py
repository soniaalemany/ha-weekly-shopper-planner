"""Modelo de dominio: dataclasses serializables a JSON."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


def new_id() -> str:
    return str(uuid4())


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


@dataclass
class Ingredient:
    name: str
    quantity: float | None = None
    unit: str | None = None
    category: str | None = None
    id: str = field(default_factory=new_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ingredient:
        return cls(
            id=data.get("id") or new_id(),
            name=str(data["name"]).strip(),
            quantity=_num(data.get("quantity")),
            unit=(str(data["unit"]).strip() or None) if data.get("unit") else None,
            category=(str(data["category"]).strip() or None) if data.get("category") else None,
        )


@dataclass
class Recipe:
    name: str
    servings: int = 4
    description: str | None = None
    instructions: str | None = None
    prep_minutes: int | None = None
    ingredients: list[Ingredient] = field(default_factory=list)
    id: str = field(default_factory=new_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "servings": self.servings,
            "description": self.description,
            "instructions": self.instructions,
            "prep_minutes": self.prep_minutes,
            "ingredients": [i.to_dict() for i in self.ingredients],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Recipe:
        return cls(
            id=data.get("id") or new_id(),
            name=str(data["name"]).strip(),
            servings=int(data.get("servings") or 4),
            description=data.get("description"),
            instructions=data.get("instructions"),
            prep_minutes=data.get("prep_minutes"),
            ingredients=[Ingredient.from_dict(i) for i in data.get("ingredients", [])],
        )


@dataclass
class MealPlanEntry:
    day: int  # 0 = lunes … 6 = domingo
    meal: str
    position: int
    recipe_id: str
    servings: int | None = None
    selected_ingredient_ids: list[str] = field(default_factory=list)

    @property
    def slot(self) -> tuple[int, str, int]:
        return (self.day, self.meal, self.position)

    def to_dict(self) -> dict[str, Any]:
        return {
            "day": self.day,
            "meal": self.meal,
            "position": self.position,
            "recipe_id": self.recipe_id,
            "servings": self.servings,
            "selected_ingredient_ids": list(self.selected_ingredient_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MealPlanEntry:
        return cls(
            day=int(data["day"]),
            meal=str(data["meal"]),
            position=int(data.get("position", 0)),
            recipe_id=str(data["recipe_id"]),
            servings=data.get("servings"),
            selected_ingredient_ids=list(data.get("selected_ingredient_ids", [])),
        )


@dataclass
class MealPlan:
    revision: int = 0
    entries: list[MealPlanEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"revision": self.revision, "entries": [e.to_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MealPlan:
        return cls(
            revision=int(data.get("revision", 0)),
            entries=[MealPlanEntry.from_dict(e) for e in data.get("entries", [])],
        )


@dataclass
class ShoppingItem:
    name: str
    quantity: float | None = None
    unit: str | None = None
    category: str | None = None
    checked: bool = False
    source: str = "manual"
    id: str = field(default_factory=new_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "category": self.category,
            "checked": self.checked,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShoppingItem:
        return cls(
            id=data.get("id") or new_id(),
            name=str(data["name"]).strip(),
            quantity=_num(data.get("quantity")),
            unit=data.get("unit") or None,
            category=data.get("category") or None,
            checked=bool(data.get("checked", False)),
            source=data.get("source", "manual"),
        )


@dataclass
class ShoppingList:
    revision: int = 0
    items: list[ShoppingItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"revision": self.revision, "items": [i.to_dict() for i in self.items]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShoppingList:
        return cls(
            revision=int(data.get("revision", 0)),
            items=[ShoppingItem.from_dict(i) for i in data.get("items", [])],
        )


@dataclass
class UsageEntry:
    recipe_id: str
    monday: str | None
    meal: str | None
    used_at: str  # ISO

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "monday": self.monday,
            "meal": self.meal,
            "used_at": self.used_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UsageEntry:
        return cls(
            recipe_id=data["recipe_id"],
            monday=data.get("monday"),
            meal=data.get("meal"),
            used_at=data["used_at"],
        )
