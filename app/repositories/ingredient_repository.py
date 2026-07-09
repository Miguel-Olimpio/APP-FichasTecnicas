"""Compat: use `RecipeIngredientRepository` (aba IngredientesFicha)."""

from app.repositories.recipe_ingredient_repository import RecipeIngredientRepository

IngredientRepository = RecipeIngredientRepository

__all__ = ["IngredientRepository"]
