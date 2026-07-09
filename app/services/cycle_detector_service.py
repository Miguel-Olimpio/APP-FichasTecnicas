"""Detecção de ciclos em dependências de produtos compostos."""

from __future__ import annotations

from typing import Any

from app.models.enums import IngredienteTipo


def _as_service_ing(ing: dict[str, Any]) -> dict[str, Any]:
    if str(ing.get("origem_linha", "") or "").strip() and "nome_ingrediente" in ing:
        from app.services.recipe_line_adapter import row_to_service_dict

        return row_to_service_dict(ing)
    return ing


def _is_composto_line(ing: dict[str, Any]) -> bool:
    s = _as_service_ing(ing)
    return str(s.get("tipo")) == IngredienteTipo.PRODUTO_COMPOSTO.value


def build_adjacency(
    all_ingredient_rows: list[dict[str, Any]],
    exclude_product_id: str | None = None,
    override_edges: list[tuple[str, str]] | None = None,
) -> dict[str, set[str]]:
    """Mapa produto_id -> conjunto de produto_ref_id (compostos)."""
    adj: dict[str, set[str]] = {}
    override_edges = override_edges or []
    for parent, child in override_edges:
        adj.setdefault(parent, set()).add(child)
    for ing in all_ingredient_rows:
        s = _as_service_ing(ing)
        if not _is_composto_line(s):
            continue
        parent = str(s.get("produto_id", "") or "")
        child = str(s.get("produto_ref_id", "") or "")
        if not child:
            continue
        if exclude_product_id and parent == str(exclude_product_id):
            continue
        adj.setdefault(parent, set()).add(child)
    return adj


def _dfs_reachable(adj: dict[str, set[str]], start: str, target: str, visited: set[str] | None = None) -> bool:
    if start == target:
        return True
    visited = visited or set()
    if start in visited:
        return False
    visited.add(start)
    for nxt in adj.get(start, ()):
        if _dfs_reachable(adj, nxt, target, visited):
            return True
    return False


def would_create_cycle(
    product_id: str,
    proposed_ref_id: str,
    all_ingredient_rows: list[dict[str, Any]],
    current_product_ingredient_rows: list[dict[str, Any]],
) -> bool:
    """True se adicionar aresta product_id -> proposed_ref_id fecha ciclo voltando a product_id."""
    pid = str(product_id)
    ref = str(proposed_ref_id)
    if not ref or ref == pid:
        return True
    override: list[tuple[str, str]] = []
    for ing in current_product_ingredient_rows:
        s = _as_service_ing(ing)
        if not _is_composto_line(s):
            continue
        p = str(s.get("produto_id", "") or "")
        c = str(s.get("produto_ref_id", "") or "")
        if p == pid and c:
            override.append((p, c))
    if (pid, ref) not in override:
        override.append((pid, ref))
    adj = build_adjacency(all_ingredient_rows, exclude_product_id=pid, override_edges=override)
    return _dfs_reachable(adj, ref, pid)


def validate_no_cycle_for_save(
    product_id: str,
    ingredient_rows_for_product: list[dict[str, Any]],
    all_ingredient_rows: list[dict[str, Any]],
) -> bool:
    """Verifica se o conjunto de refs compostas da ficha cria ciclo envolvendo product_id."""
    pid = str(product_id)
    refs: list[str] = []
    for ing in ingredient_rows_for_product:
        s = _as_service_ing(ing)
        if _is_composto_line(s) and s.get("produto_ref_id"):
            refs.append(str(s.get("produto_ref_id", "") or ""))
    for ref in refs:
        if would_create_cycle(pid, ref, all_ingredient_rows, ingredient_rows_for_product):
            return False
    return True


def get_dependent_active_product_ids(
    product_id: str,
    all_product_rows: list[dict[str, Any]],
    all_ingredient_rows: list[dict[str, Any]],
) -> list[str]:
    """IDs de fichas ativas que referenciam product_id como composto."""
    active_ids = {
        str(r.get("produto_id"))
        for r in all_product_rows
        if str(r.get("produto_id"))
        and r.get("active") not in (False, "false", "FALSE", 0, "0")
    }
    pid = str(product_id)
    deps: set[str] = set()
    for ing in all_ingredient_rows:
        s = _as_service_ing(ing)
        if not _is_composto_line(s):
            continue
        if str(s.get("produto_ref_id")) != pid:
            continue
        parent = str(s.get("produto_id", "") or "")
        if parent in active_ids:
            deps.add(parent)
    return sorted(deps)
