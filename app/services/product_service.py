"""Orquestração de fichas técnicas: validação, cálculo, persistência."""

from __future__ import annotations

import uuid
from typing import Any

from app.config.settings import (
    ENABLE_AUDIT_LOG,
    MSG_CYCLE_DEPENDENCY,
    SHEET_INGREDIENTES_FICHA,
    SHEET_PASSOS_PREPARO,
    SHEET_PRECIFICACAO,
    SHEET_PRODUTOS,
)
from app.repositories.excel_database import ExcelDatabase, ExcelSaveError, _write_sheet
from app.repositories.excel_schema import PREP_STEP_HEADERS, PRICING_HEADERS, PRODUCT_HEADERS, RECIPE_LINE_HEADERS
from app.repositories.prep_step_repository import PrepStepRepository, normalize_prep_steps
from app.repositories.pricing_repository import PricingRepository, normalize_pricing_row
from app.repositories.recipe_ingredient_repository import RecipeIngredientRepository
from app.repositories.product_repository import ProductRepository
from app.services.cycle_detector_service import get_dependent_active_product_ids, validate_no_cycle_for_save
from app.services.recipe_calculation_service import build_products_by_id_from_rows, recalc_product
from app.services.recipe_line_adapter import service_dict_to_row
from app.services.validation_service import ValidationResult, validate_ingredient_row, validate_product_for_save
from app.utils.dates import now_str
from app.utils.tipo_ficha import TIPO_FICHA_MATERIA_PRIMA, TIPO_FICHA_PRODUTO_FINAL, normalize_tipo_ficha


class ProductServiceError(Exception):
    pass


class ProductService:
    def __init__(
        self,
        db_fichas: ExcelDatabase,
        product_repo: ProductRepository,
        recipe_ingredient_repo: RecipeIngredientRepository,
        db_ingredientes: ExcelDatabase | None = None,
        prep_step_repo: PrepStepRepository | None = None,
        pricing_repo: PricingRepository | None = None,
    ):
        self._db = db_fichas
        self._db_ing = db_ingredientes
        self._products = product_repo
        self._ingredients = recipe_ingredient_repo
        self._prep_steps = prep_step_repo
        self._pricing = pricing_repo

    def list_active_products(self) -> list[dict[str, Any]]:
        return [p.to_row_dict() for p in self._products.list_active()]

    def list_materia_prima_for_composto(self, exclude_product_id: str) -> list[dict[str, Any]]:
        ex = str(exclude_product_id)
        out: list[dict[str, Any]] = []
        for p in self._products.list_active():
            row = p.to_row_dict()
            if str(row.get("produto_id")) == ex:
                continue
            if normalize_tipo_ficha(row.get("tipo_ficha")) == TIPO_FICHA_MATERIA_PRIMA:
                out.append(row)
        return out

    def get_product_row(self, product_id: str) -> dict[str, Any] | None:
        p = self._products.get_by_id_any(product_id)
        return p.to_row_dict() if p else None

    def get_ingredients(self, product_id: str) -> list[dict[str, Any]]:
        return self._ingredients.list_by_product(product_id)

    def get_prep_steps(self, product_id: str) -> list[dict[str, Any]]:
        if self._prep_steps:
            rows = self._prep_steps.list_by_product(product_id)
            if rows:
                return rows
        row = self.get_product_row(product_id)
        legacy = str((row or {}).get("modo_preparo", "") or "").strip()
        if not legacy:
            return []
        return [
            {"produto_id": str(product_id), "ordem": idx, "descricao": line.strip()}
            for idx, line in enumerate(legacy.splitlines(), start=1)
            if line.strip()
        ]

    def get_pricing(self, product_id: str) -> dict[str, Any]:
        if not self._pricing:
            return {}
        return self._pricing.get_by_product(product_id) or {}

    def recalc_draft(
        self, product: dict[str, Any], ingredients: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
        all_rows = self._products.list_all_rows()
        by_id = build_products_by_id_from_rows(all_rows)
        pid = str(product.get("produto_id", "") or "")
        if pid:
            merged = dict(by_id.get(pid, {}))
            merged.update(product)
            by_id[pid] = merged
        return recalc_product(product, ingredients, by_id)

    def validate_full(
        self, product: dict[str, Any], ingredients: list[dict[str, Any]], current_product_id: str
    ) -> ValidationResult:
        active = [r for r in self._products.list_all_rows() if _row_is_active(r)]
        res = validate_product_for_save(product, ingredients, active, current_product_id)
        all_rows = self._products.list_all_rows()
        by_id = build_products_by_id_from_rows(all_rows)
        for ing in ingredients:
            vr = validate_ingredient_row(ing, by_id)
            res.errors.extend(vr.errors)
        res.errors.extend(
            self._errors_tipo_ficha_demotion(
                str(current_product_id), product, all_rows, self._ingredients.list_all_rows()
            )
        )
        return res

    def save_product(
        self,
        product: dict[str, Any],
        ingredients: list[dict[str, Any]],
        prep_steps: list[dict[str, Any]] | list[str] | None = None,
        pricing: dict[str, Any] | None = None,
    ) -> None:
        pid = str(product.get("produto_id", "") or "")
        if not pid:
            raise ProductServiceError("produto_id ausente.")

        self._db.create_backup()
        if self._db_ing:
            self._db_ing.create_backup()

        active = [r for r in self._products.list_all_rows() if _row_is_active(r)]
        val = validate_product_for_save(product, ingredients, active, pid)
        all_rows = self._products.list_all_rows()
        by_id = build_products_by_id_from_rows(all_rows)
        for ing in ingredients:
            vr = validate_ingredient_row(ing, by_id)
            val.errors.extend(vr.errors)
        val.errors.extend(
            self._errors_tipo_ficha_demotion(pid, product, all_rows, self._ingredients.list_all_rows())
        )
        if not val.ok:
            raise ProductServiceError("\n".join(val.errors))

        all_ings_raw = self._ingredients.list_all_rows()
        if not validate_no_cycle_for_save(pid, ingredients, all_ings_raw):
            raise ProductServiceError(MSG_CYCLE_DEPENDENCY)

        pdict, ing_dicts, _warnings = recalc_product(product, ingredients, by_id)

        all_products_rows = list(all_rows)
        found = False
        for i, r in enumerate(all_products_rows):
            if str(r.get("produto_id")) == pid:
                all_products_rows[i] = pdict
                found = True
                break
        if not found:
            all_products_rows.append(pdict)

        kept_raw = [r for r in all_ings_raw if str(r.get("produto_id")) != pid]
        for ing in ing_dicts:
            kept_raw.append(service_dict_to_row(ing))

        prep_rows: list[dict[str, Any]] | None = None
        if prep_steps is not None and self._prep_steps:
            all_prep_rows = self._prep_steps.list_all_rows()
            prep_rows = [r for r in all_prep_rows if str(r.get("produto_id")) != pid]
            prep_rows.extend(normalize_prep_steps(pid, prep_steps))

        pricing_rows: list[dict[str, Any]] | None = None
        if pricing is not None and self._pricing:
            all_pricing_rows = self._pricing.list_all_rows()
            pricing_rows = [r for r in all_pricing_rows if str(r.get("produto_id")) != pid]
            pricing_rows.append(normalize_pricing_row(pid, pricing))

        try:
            wb = self._db.load_workbook_safe()
            try:
                if SHEET_PASSOS_PREPARO not in wb.sheetnames:
                    wb.create_sheet(SHEET_PASSOS_PREPARO)
                if SHEET_PRECIFICACAO not in wb.sheetnames:
                    wb.create_sheet(SHEET_PRECIFICACAO)
                _write_sheet(wb[SHEET_PRODUTOS], PRODUCT_HEADERS, all_products_rows)
                _write_sheet(wb[SHEET_INGREDIENTES_FICHA], RECIPE_LINE_HEADERS, kept_raw)
                if prep_rows is not None:
                    _write_sheet(wb[SHEET_PASSOS_PREPARO], PREP_STEP_HEADERS, prep_rows)
                if pricing_rows is not None:
                    _write_sheet(wb[SHEET_PRECIFICACAO], PRICING_HEADERS, pricing_rows)
                self._db.save_workbook_safe(wb)
            except ExcelSaveError:
                wb.close()
                raise
            except Exception:
                wb.close()
                raise
        except ExcelSaveError as exc:
            raise ProductServiceError(exc.user_message) from exc

        if ENABLE_AUDIT_LOG:
            try:
                self._db.append_audit_row(
                    {
                        "log_id": str(uuid.uuid4()),
                        "entidade": "Produto",
                        "entidade_id": pid,
                        "acao": "save",
                        "descricao": f"Salvar ficha {pdict.get('nome', '')}",
                        "data_hora": now_str(),
                    }
                )
            except Exception:
                pass

    def _errors_tipo_ficha_demotion(
        self,
        product_id: str,
        product: dict[str, Any],
        all_product_rows: list[dict[str, Any]],
        all_ingredient_rows: list[dict[str, Any]],
    ) -> list[str]:
        pid = str(product_id)
        old = next((r for r in all_product_rows if str(r.get("produto_id")) == pid), None)
        if not old:
            return []
        old_t = normalize_tipo_ficha(old.get("tipo_ficha"))
        new_t = normalize_tipo_ficha(product.get("tipo_ficha"))
        if old_t != TIPO_FICHA_MATERIA_PRIMA or new_t != TIPO_FICHA_PRODUTO_FINAL:
            return []
        deps = get_dependent_active_product_ids(pid, all_product_rows, all_ingredient_rows)
        if not deps:
            return []
        id_to_name = {str(r.get("produto_id")): str(r.get("nome", "") or "(sem nome)") for r in all_product_rows}
        names = [id_to_name.get(d, d) for d in deps]
        return [
            "Esta ficha está sendo usada como matéria-prima em outras fichas e não pode ser alterada para produto final. "
            "Fichas dependentes: "
            + ", ".join(names)
            + "."
        ]

    def soft_delete_product(self, product_id: str) -> None:
        pid = str(product_id)
        all_products = self._products.list_all_rows()
        all_ings = self._ingredients.list_all_rows()
        deps = get_dependent_active_product_ids(pid, all_products, all_ings)
        if deps:
            id_to_name = {str(r.get("produto_id")): str(r.get("nome", "") or "(sem nome)") for r in all_products}
            names = [id_to_name.get(d, d) for d in deps]
            raise ProductServiceError(
                "Não é possível excluir esta ficha porque ela está sendo usada como matéria-prima em: "
                + ", ".join(names)
                + ". Remova essas referências antes de excluir."
            )
        self._db.create_backup()
        found = False
        for r in all_products:
            if str(r.get("produto_id")) == pid:
                r["active"] = False
                r["data_atualizacao"] = now_str()
                found = True
                break
        if not found:
            raise ProductServiceError("Ficha não encontrada.")
        try:
            self._db.write_sheet(SHEET_PRODUTOS, PRODUCT_HEADERS, all_products)
        except ExcelSaveError as exc:
            raise ProductServiceError(exc.user_message) from exc

        if ENABLE_AUDIT_LOG:
            try:
                self._db.append_audit_row(
                    {
                        "log_id": str(uuid.uuid4()),
                        "entidade": "Produto",
                        "entidade_id": pid,
                        "acao": "soft_delete",
                        "descricao": "Exclusão lógica",
                        "data_hora": now_str(),
                    }
                )
            except Exception:
                pass


def _row_is_active(row: dict[str, Any]) -> bool:
    a = row.get("active")
    if a in (False, "false", "FALSE", 0, "0"):
        return False
    return True
