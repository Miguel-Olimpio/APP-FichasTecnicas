"""CRUD e regras do cadastro mestre de ingredientes."""

from __future__ import annotations

import uuid
from typing import Any

from app.config.settings import CLASSIFICACAO_INGREDIENTE_SIMPLES, CLASSIFICACAO_MATERIA_PRIMA
from app.models.ingredient_master import IngredientMaster
from app.repositories.ingredient_master_repository import IngredientMasterRepository
from app.utils.dates import now_str
from app.utils.filenames import normalize_name_key
from app.utils.numbers import to_float
from app.utils.units import normalize_cost_unit_key


class IngredientMasterServiceError(Exception):
    pass


class IngredientMasterService:
    def __init__(self, repo: IngredientMasterRepository):
        self._repo = repo

    def list_active_dicts(self) -> list[dict[str, Any]]:
        return [m.to_row_dict() for m in self._repo.list_active()]

    def list_filtered(self, search: str, classificacao: str | None) -> list[dict[str, Any]]:
        q = (search or "").strip().lower()
        cf = (classificacao or "").strip()
        out: list[dict[str, Any]] = []
        for m in self._repo.list_active():
            d = m.to_row_dict()
            if q and q not in str(d.get("nome", "")).lower():
                continue
            if cf and cf != "Todos":
                if cf == "Ingrediente simples" and d.get("classificacao") != CLASSIFICACAO_INGREDIENTE_SIMPLES:
                    continue
                if cf == "Matéria-prima" and d.get("classificacao") != CLASSIFICACAO_MATERIA_PRIMA:
                    continue
            out.append(d)
        return out

    def get_row(self, ingrediente_id: str) -> dict[str, Any] | None:
        m = self._repo.get_by_id(ingrediente_id)
        return m.to_row_dict() if m else None

    def validate_new_or_update(
        self,
        nome: str,
        classificacao: str,
        categoria: str,
        unidade_padrao: str,
        unidade_custo: str,
        preco_kg: float,
        preco_litro: float,
        preco_unidade: float,
        exclude_id: str | None = None,
    ) -> list[str]:
        errs: list[str] = []
        if not nome.strip():
            errs.append("Nome é obrigatório.")
        if not classificacao.strip():
            errs.append("Classificação é obrigatória.")
        if not unidade_padrao.strip():
            errs.append("Unidade padrão é obrigatória.")
        if not unidade_custo.strip():
            errs.append("Unidade de custo é obrigatória.")
        ck = normalize_cost_unit_key(unidade_custo)
        if ck == "kg" and preco_kg <= 0:
            errs.append("Informe preço por kg maior que zero.")
        if ck in ("l", "ml") and preco_litro <= 0:
            errs.append("Informe preço por litro maior que zero.")
        if ck == "un" and preco_unidade <= 0:
            errs.append("Informe preço por unidade maior que zero.")
        if ck == "porção":
            errs.append("No cadastro mestre use kg, L ou un como unidade de custo.")
        nn = normalize_name_key(nome)
        existing = self._repo.find_by_nome_normalizado(nn)
        if existing and str(existing.ingrediente_id) != str(exclude_id or ""):
            errs.append("Já existe ingrediente com esse nome (nome normalizado duplicado).")
        return errs

    def add(
        self,
        nome: str,
        classificacao: str,
        categoria: str,
        unidade_padrao: str,
        unidade_custo: str,
        preco_kg: float,
        preco_litro: float,
        preco_unidade: float,
        observacoes: str,
    ) -> str:
        errs = self.validate_new_or_update(
            nome, classificacao, categoria, unidade_padrao, unidade_custo, preco_kg, preco_litro, preco_unidade
        )
        if errs:
            raise IngredientMasterServiceError("\n".join(errs))
        mid = str(uuid.uuid4())
        rows = self._repo.list_all_rows()
        ck = normalize_cost_unit_key(unidade_custo)
        pk, pl, pu = preco_kg, preco_litro, preco_unidade
        if ck == "kg":
            pl, pu = 0.0, 0.0
        elif ck in ("l", "ml"):
            pk, pu = 0.0, 0.0
        elif ck == "un":
            pk, pl = 0.0, 0.0
        row = {
            "ingrediente_id": mid,
            "nome": nome.strip(),
            "nome_normalizado": normalize_name_key(nome),
            "classificacao": classificacao.strip(),
            "categoria": (categoria or "Outros").strip(),
            "unidade_padrao": unidade_padrao.strip(),
            "unidade_custo": unidade_custo.strip(),
            "preco_kg": pk,
            "preco_litro": pl,
            "preco_unidade": pu,
            "observacoes": observacoes or "",
            "data_criacao": now_str(),
            "data_atualizacao": now_str(),
            "active": True,
        }
        rows.append(row)
        self._repo.save_all(rows)
        return mid

    def update(self, ingrediente_id: str, **fields: Any) -> None:
        rows = self._repo.list_all_rows()
        found = False
        for i, r in enumerate(rows):
            if str(r.get("ingrediente_id")) != str(ingrediente_id):
                continue
            found = True
            merged = dict(r)
            for k, v in fields.items():
                if k in merged and v is not None:
                    merged[k] = v
            merged["data_atualizacao"] = now_str()
            rows[i] = merged
            break
        if not found:
            raise IngredientMasterServiceError("Ingrediente não encontrado.")
        m = IngredientMaster.from_row_dict(rows[i])
        d = m.to_row_dict()
        errs = self.validate_new_or_update(
            str(d.get("nome", "")),
            str(d.get("classificacao", "")),
            str(d.get("categoria", "")),
            str(d.get("unidade_padrao", "")),
            str(d.get("unidade_custo", "")),
            to_float(d.get("preco_kg")),
            to_float(d.get("preco_litro")),
            to_float(d.get("preco_unidade")),
            exclude_id=ingrediente_id,
        )
        if errs:
            raise IngredientMasterServiceError("\n".join(errs))
        self._repo.save_all(rows)

    def soft_delete(self, ingrediente_id: str) -> None:
        rows = self._repo.list_all_rows()
        for r in rows:
            if str(r.get("ingrediente_id")) == str(ingrediente_id):
                r["active"] = False
                r["data_atualizacao"] = now_str()
                self._repo.save_all(rows)
                return
        raise IngredientMasterServiceError("Ingrediente não encontrado.")
