"""Ponto de entrada da aplicaÃ§Ã£o (lÃ³gica de arranque)."""

from __future__ import annotations

from tkinter import messagebox

import ttkbootstrap as ttb

from app.config.paths import (
    ensure_legacy_database_copied,
    ensure_legacy_ingredients_copied,
    get_app_data_dir,
    get_backups_dir,
    get_data_dir,
    get_database_path,
    get_ingredients_database_path,
    get_pdfs_dir,
    is_packaged,
)
from app.config.settings import APP_TITLE
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import FICHAS_SHEETS_CONFIG, MASTER_SHEETS_CONFIG
from app.repositories.ingredient_master_repository import IngredientMasterRepository
from app.repositories.migration_split_workbooks import run_split_workbook_migration
from app.repositories.prep_step_repository import PrepStepRepository
from app.repositories.pricing_repository import PricingRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.recipe_ingredient_repository import RecipeIngredientRepository
from app.services.ingredient_master_service import IngredientMasterService
from app.services.ingredient_service import IngredientService
from app.services.product_service import ProductService
from app.ui.main_window import MainWindow
from app.ui.styles import apply_app_theme
from app.ui.window_icon import apply_window_icon, set_windows_app_id


def main() -> None:
    ensure_legacy_database_copied()
    ensure_legacy_ingredients_copied()

    db_fichas = ExcelDatabase(get_database_path(), FICHAS_SHEETS_CONFIG, "banco_fichas", get_backups_dir())
    db_fichas.ensure_database()

    db_ing = ExcelDatabase(
        get_ingredients_database_path(),
        MASTER_SHEETS_CONFIG,
        "banco_ingredientes",
        get_backups_dir(),
    )
    db_ing.ensure_database()

    mig_warns = run_split_workbook_migration(db_fichas, db_ing)
    if mig_warns:
        messagebox.showinfo("MigraÃ§Ã£o de dados", "\n".join(mig_warns))

    product_repo = ProductRepository(db_fichas)
    recipe_repo = RecipeIngredientRepository(db_fichas)
    prep_repo = PrepStepRepository(db_fichas)
    pricing_repo = PricingRepository(db_fichas)
    master_repo = IngredientMasterRepository(db_ing)

    master_svc = IngredientMasterService(master_repo)
    product_service = ProductService(db_fichas, product_repo, recipe_repo, db_ing, prep_repo, pricing_repo)
    ingredient_service = IngredientService(master_svc)

    set_windows_app_id()
    root = ttb.Window(themename="litera", title=APP_TITLE)
    apply_window_icon(root)
    apply_app_theme(root)
    MainWindow(root, product_service, ingredient_service, master_svc)
    root.geometry("1280x800")
    root.minsize(1200, 750)
    root.place_window_center()
    root.mainloop()


if __name__ == "__main__":
    main()

