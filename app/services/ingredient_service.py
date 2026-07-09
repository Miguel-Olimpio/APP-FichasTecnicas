"""Compatibilidade com UI antiga: catálogo = cadastro mestre (ingredientes simples)."""

from __future__ import annotations

from app.config.settings import CLASSIFICACAO_INGREDIENTE_SIMPLES
from app.services.ingredient_master_service import IngredientMasterService, IngredientMasterServiceError


class IngredientService:
    def __init__(self, master_service: IngredientMasterService):
        self._master = master_service

    @property
    def master(self) -> IngredientMasterService:
        return self._master

    def list_catalog_active(self) -> list[dict]:
        return self._master.list_active_dicts()

    def add_catalog_item(
        self,
        nome: str,
        unidade_padrao: str,
        preco_unidade_padrao: float,
        preco_kg_padrao: float,
        unidade_custo_padrao: str,
    ) -> dict:
        try:
            iid = self._master.add(
                nome,
                CLASSIFICACAO_INGREDIENTE_SIMPLES,
                "Outros",
                unidade_padrao.strip() or "kg",
                unidade_custo_padrao.strip() or "kg",
                preco_kg_padrao,
                0.0,
                preco_unidade_padrao,
                "",
            )
        except IngredientMasterServiceError as exc:
            raise ValueError(str(exc)) from exc
        row = self._master.get_row(iid)
        return row or {"ingrediente_id": iid, "nome": nome}
