"""Seleção de ingredientes cadastrados + ficha intermediária + atalho para cadastro mestre."""

from __future__ import annotations

import tkinter as tk
from collections import Counter
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any, Protocol

import ttkbootstrap as ttb

from app.config.settings import (
    CLASSIFICACAO_INGREDIENTE_SIMPLES,
    ORIGEM_CADASTRO_MESTRE,
    ORIGEM_FICHA_INTERMEDIARIA,
)
from app.services.ingredient_master_service import IngredientMasterService
from app.services.recipe_calculation_service import calc_ingredient_cost
from app.services.recipe_line_adapter import build_line_from_intermediate_product, build_line_from_master
from app.services.validation_service import find_duplicate_ingredient_warning
from app.ui.ingredient_master_tab import open_ingredient_master_editor
from app.ui.window_icon import apply_window_icon
from app.utils.money import format_money_br
from app.utils.numbers import to_float
from app.ui.styles import MUTED_TEXT_COLOR, SPACING_MD, SPACING_SM, SUCCESS_COLOR, configure_treeview_zebra, style_button
from app.utils.units import (
    COST_UNIT_OPTIONS,
    ensure_in_options,
    get_units_for_cost_unit,
    is_valid_unit_for_cost_unit,
    normalize_cost_unit_key,
    normalize_unit,
)

if TYPE_CHECKING:
    from app.services.ingredient_service import IngredientService
    from app.services.product_service import ProductService


class RecipeEditorHost(Protocol):
    product_id: str
    _ingredients: list[dict[str, Any]]

    def upsert_ingredient(self, ingredient: dict[str, Any]) -> None: ...
    def mark_dirty(self) -> None: ...


def _preco_display_master(row: dict[str, Any]) -> str:
    uc = normalize_cost_unit_key(row.get("unidade_custo"))
    if uc == "kg":
        return format_money_br(row.get("preco_kg")) + "/kg"
    if uc in ("l", "ml"):
        return format_money_br(row.get("preco_litro")) + "/L"
    if uc == "un":
        return format_money_br(row.get("preco_unidade")) + "/un"
    return "—"


def _base_unit_for_cost(cost_unit: object) -> str:
    key = normalize_cost_unit_key(cost_unit)
    if key == "kg":
        return "kg"
    if key in ("l", "ml"):
        return "L"
    if key == "un":
        return "un"
    if key == "porção":
        return "porção"
    allowed = get_units_for_cost_unit(cost_unit)
    return allowed[0] if allowed else ""


def _cost_unit_for_intermediate_product(row: dict[str, Any] | None) -> str:
    unit = normalize_unit((row or {}).get("unidade_rendimento"))
    if unit in ("kg", "g", "gr", "grama", "gramas", "quilo", "quilos"):
        return "kg"
    if unit in ("l", "ml", "litro", "litros", "mililitro", "mililitros"):
        return "L"
    return "un"


def _preco_display_intermediate(row: dict[str, Any]) -> str:
    cost_unit = _cost_unit_for_intermediate_product(row)
    if cost_unit == "kg":
        return format_money_br(row.get("custo_por_kg")) + "/kg"
    if cost_unit == "L":
        return format_money_br(row.get("custo_por_unidade")) + "/L"
    return format_money_br(row.get("custo_por_unidade")) + "/un"


def _help_for_cost(cost_unit: object) -> str:
    key = normalize_cost_unit_key(cost_unit)
    if key == "kg":
        return (
            "Insira a quantidade utilizada na ficha técnica.\n"
            "Exemplos:\n"
            "0,175 para 175 gramas\n"
            "1,68 para 1 quilo e 680 gramas"
        )
    if key in ("l", "ml"):
        return (
            "Insira a quantidade utilizada na ficha técnica.\n"
            "Exemplos:\n"
            "0,250 para 250 ml\n"
            "1,5 para 1 litro e 500 ml"
        )
    if key == "un":
        return (
            "Insira a quantidade utilizada na ficha técnica.\n"
            "Exemplos:\n"
            "1 para uma unidade\n"
            "0,5 para meia unidade\n"
            "2 para duas unidades"
        )
    if key == "porção":
        return "Informe a quantidade de porções utilizadas."
    return "Informe a quantidade usada nesta ficha técnica."


def open_recipe_ingredient_dialog(
    parent: tk.Widget,
    editor: RecipeEditorHost,
    product_service: "ProductService",
    master_svc: IngredientMasterService,
    ingredient_service: "IngredientService",
    ingredient: dict[str, Any] | None = None,
) -> None:
    win = tk.Toplevel(parent.winfo_toplevel())
    apply_window_icon(win)
    win.title("Editar ingrediente da ficha" if ingredient else "Adicionar novo ingrediente à ficha técnica")
    win.geometry("840x560")
    win.transient(parent.winfo_toplevel())

    selected_id: tk.StringVar = tk.StringVar(value="")
    selected_name = tk.StringVar(value="Nenhum ingrediente selecionado.")
    qty_var = tk.StringVar()
    unit_var = tk.StringVar(value="kg")
    help_var = tk.StringVar(value="")
    preview_var = tk.StringVar(value="Custo estimado: —")
    search_var = tk.StringVar()
    filter_var = tk.StringVar(value="Todos")
    master_prefix = "master:"
    intermediate_prefix = "intermediate:"

    body = ttk.Frame(win, padding=16)
    body.pack(fill="both", expand=True)
    body.columnconfigure(0, weight=1)
    body.rowconfigure(2, weight=1)

    title = "Editar ingrediente da ficha" if ingredient else "Adicionar novo ingrediente à ficha técnica"
    ttk.Label(body, text=title, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")

    top = ttk.Frame(body)
    top.grid(row=1, column=0, sticky="ew", pady=(SPACING_MD, SPACING_SM))
    top.columnconfigure(1, weight=1)
    ttk.Label(top, text="Pesquisar ingrediente").grid(row=0, column=0, sticky="w", padx=(0, SPACING_SM))
    search_entry = ttk.Entry(top, textvariable=search_var, width=34)
    search_entry.grid(row=0, column=1, sticky="ew", padx=(0, SPACING_MD))
    ttk.Label(top, text="Classificação").grid(row=0, column=2, sticky="w", padx=(0, SPACING_SM))
    filter_combo = ttk.Combobox(
        top,
        textvariable=filter_var,
        values=("Todos", "Matéria-prima", "Ingrediente simples"),
        state="readonly",
        width=18,
    )
    filter_combo.grid(row=0, column=3, sticky="w", padx=(0, SPACING_MD))

    def on_catalog_saved(saved_id: str) -> None:
        selected_id.set(master_prefix + saved_id)
        if search_var.get().strip():
            search_var.set("")
        if filter_var.get() != "Todos":
            filter_var.set("Todos")
        refresh_tree()
        iid = master_prefix + saved_id
        if tree.exists(iid):
            tree.selection_set(iid)
            tree.focus(iid)
            tree.see(iid)
            sync_for_selection()
            qty_entry.focus_set()

    def open_catalog_from_dialog() -> None:
        try:
            win.grab_release()
        except tk.TclError:
            pass
        try:
            catalog_win = open_ingredient_master_editor(
                win,
                master_svc,
                on_saved_id=on_catalog_saved,
            )
            catalog_win.grab_set()
            catalog_win.focus_set()
            catalog_win.wait_window()
        finally:
            if win.winfo_exists():
                win.grab_set()
                win.focus_set()

    btn_new = ttk.Button(
        top,
        text="Cadastrar novo ingrediente",
        command=open_catalog_from_dialog,
    )
    btn_new.grid(row=0, column=4, sticky="e")
    style_button(btn_new, "secondary")

    list_frame = ttk.Frame(body)
    list_frame.grid(row=2, column=0, sticky="nsew")
    list_frame.columnconfigure(0, weight=1)
    list_frame.rowconfigure(0, weight=1)
    cols = ("nome", "cls", "uc", "preco")
    tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=9, selectmode="browse")
    for col, text, width, anchor in [
        ("nome", "Nome", 260, "w"),
        ("cls", "Tipo/Classificação", 150, "w"),
        ("uc", "Custo por", 90, "center"),
        ("preco", "Preço", 130, "e"),
    ]:
        tree.heading(col, text=text)
        tree.column(col, width=width, anchor=anchor)
    tree.grid(row=0, column=0, sticky="nsew")
    configure_treeview_zebra(tree)
    empty_label = ttk.Label(list_frame, text="Nenhum ingrediente cadastrado.", style="Muted.TLabel")
    empty_label.grid(row=1, column=0, sticky="w", pady=(SPACING_SM, 0))

    selected_frame = ttk.LabelFrame(body, text="Ingrediente selecionado:", padding=SPACING_MD)
    selected_frame.grid(row=3, column=0, sticky="ew", pady=(SPACING_MD, 0))
    ttk.Label(selected_frame, textvariable=selected_name, font=("Segoe UI", 9, "bold")).pack(anchor="w")

    qty_frame = ttk.LabelFrame(body, text="Quantidade utilizada", padding=SPACING_MD)
    qty_frame.grid(row=4, column=0, sticky="ew", pady=(SPACING_MD, 0))
    qty_frame.columnconfigure(1, weight=1)
    ttk.Label(qty_frame, textvariable=help_var, style="Muted.TLabel", wraplength=690).grid(
        row=0,
        column=0,
        columnspan=4,
        sticky="w",
        pady=(0, SPACING_SM),
    )
    ttk.Label(qty_frame, text="Quantidade utilizada").grid(row=1, column=0, sticky="w")
    qty_entry = ttk.Entry(qty_frame, textvariable=qty_var, width=14)
    qty_entry.grid(row=1, column=1, sticky="w", padx=(SPACING_SM, SPACING_MD))
    ttk.Label(qty_frame, text="Unidade fixa").grid(row=1, column=2, sticky="w")
    unit_combo = ttk.Combobox(qty_frame, textvariable=unit_var, values=("kg",), state="readonly", width=10)
    unit_combo.grid(row=1, column=3, sticky="w", padx=(SPACING_SM, 0))
    ttk.Label(qty_frame, textvariable=preview_var, foreground=SUCCESS_COLOR, font=("Segoe UI", 9, "bold")).grid(
        row=2,
        column=0,
        columnspan=4,
        sticky="w",
        pady=(SPACING_SM, 0),
    )

    actions = ttk.Frame(body)
    actions.grid(row=5, column=0, sticky="e", pady=(SPACING_MD, 0))
    btn_insert = ttk.Button(actions, text="Inserir ingrediente na ficha técnica", state="disabled")
    btn_insert.pack(side="right", padx=(SPACING_SM, 0))
    style_button(btn_insert, "primary")
    btn_cancel = ttk.Button(actions, text="Cancelar", command=win.destroy)
    btn_cancel.pack(side="right")
    style_button(btn_cancel, "secondary")

    def selected_item() -> tuple[str, str, dict[str, Any]] | None:
        iid = selected_id.get().strip()
        if iid.startswith(master_prefix):
            raw_id = iid[len(master_prefix) :]
            row = master_svc.get_row(raw_id)
            return ("master", raw_id, row) if row else None
        if iid.startswith(intermediate_prefix):
            raw_id = iid[len(intermediate_prefix) :]
            row = product_service.get_product_row(raw_id)
            return ("intermediate", raw_id, row) if row else None
        return None

    def build_candidate(quantity: float) -> dict[str, Any] | None:
        item = selected_item()
        if not item:
            return None
        kind, raw_id, row = item
        if kind == "intermediate":
            return build_line_from_intermediate_product(
                editor.product_id,
                raw_id,
                str(row.get("nome", "")),
                quantity,
                unit_var.get().strip(),
                _cost_unit_for_intermediate_product(row),
                ingrediente_ficha_id=str((ingredient or {}).get("ingrediente_ficha_id") or ""),
            )
        return build_line_from_master(
            editor.product_id,
            row,
            quantity,
            unit_var.get().strip(),
            ingrediente_ficha_id=str((ingredient or {}).get("ingrediente_ficha_id") or ""),
        )

    def sync_for_selection() -> None:
        item = selected_item()
        if not item:
            selected_name.set("Nenhum ingrediente selecionado.")
            help_var.set("")
            preview_var.set("Custo estimado: —")
            btn_insert.configure(state="disabled")
            return
        kind, _raw_id, row = item
        selected_name.set(str(row.get("nome", "") or "(sem nome)"))
        cost_unit = _cost_unit_for_intermediate_product(row) if kind == "intermediate" else str(row.get("unidade_custo", "") or "kg")
        unit = _base_unit_for_cost(cost_unit)
        unit_var.set(unit)
        unit_combo.configure(values=(unit,))
        help_var.set(_help_for_cost(cost_unit))
        q = to_float(qty_var.get())
        if q > 0:
            try:
                cand = build_candidate(q)
                if kind == "intermediate":
                    from app.services.recipe_calculation_service import build_products_by_id_from_rows

                    by_id = build_products_by_id_from_rows(product_service.list_active_products())
                    preview_var.set(f"Custo estimado: {format_money_br(calc_ingredient_cost(cand, by_id))}")
                else:
                    preview_var.set(f"Custo estimado: {format_money_br(calc_ingredient_cost(cand, {}))}")
            except Exception:
                preview_var.set("Custo estimado: —")
            btn_insert.configure(state="normal")
        else:
            preview_var.set("Custo estimado: —")
            btn_insert.configure(state="disabled")

    def on_select(_event: object | None = None) -> None:
        sel = tree.selection()
        selected_id.set(sel[0] if sel else "")
        sync_for_selection()

    def refresh_tree(*_args: object) -> None:
        from app.ui.components import clear_tree

        clear_tree(tree)
        query = search_var.get().strip().lower()
        current_filter = filter_var.get().strip()
        rows: list[tuple[str, str, dict[str, Any]]] = []
        if current_filter in ("Todos", "Ingrediente simples"):
            for row in master_svc.list_filtered(search_var.get(), "Ingrediente simples"):
                iid = str(row.get("ingrediente_id", "") or "")
                if iid:
                    rows.append(("master", iid, row))
        if current_filter in ("Todos", "Matéria-prima"):
            for row in product_service.list_materia_prima_for_composto(str(editor.product_id)):
                nome = str(row.get("nome", "") or "")
                if query and query not in nome.lower():
                    continue
                pid = str(row.get("produto_id", "") or "")
                if pid:
                    rows.append(("intermediate", pid, row))
        for idx, (kind, raw_id, row) in enumerate(rows):
            iid = (intermediate_prefix if kind == "intermediate" else master_prefix) + raw_id
            if not iid:
                continue
            if kind == "intermediate":
                cls_label = "Matéria-prima"
                cost_unit = _cost_unit_for_intermediate_product(row)
                preco = _preco_display_intermediate(row)
            else:
                cls_label = "Ingrediente simples"
                cost_unit = row.get("unidade_custo", "")
                preco = _preco_display_master(row)
            tag = "even" if (idx + 1) % 2 == 0 else "odd"
            tree.insert(
                "",
                "end",
                iid=iid,
                tags=(tag,),
                values=(row.get("nome", ""), cls_label, cost_unit, preco),
            )
        if rows:
            empty_label.grid_remove()
        else:
            empty_label.grid()
        if selected_id.get() and tree.exists(selected_id.get()):
            tree.selection_set(selected_id.get())
            tree.focus(selected_id.get())
        else:
            selected_id.set("")
        sync_for_selection()

    def insert_selected() -> None:
        q = to_float(qty_var.get())
        cand = build_candidate(q)
        if not cand or q <= 0:
            sync_for_selection()
            return
        if find_duplicate_ingredient_warning(editor._ingredients, cand):
            if not messagebox.askyesno(
                "Duplicidade",
                "Ingrediente semelhante já existe na ficha. Adicionar mesmo assim?",
                parent=win,
            ):
                return
        editor.upsert_ingredient(cand)
        win.destroy()

    tree.bind("<<TreeviewSelect>>", on_select)
    search_var.trace_add("write", refresh_tree)
    filter_var.trace_add("write", refresh_tree)
    qty_var.trace_add("write", lambda *_: sync_for_selection())
    btn_insert.configure(command=insert_selected)
    refresh_tree()
    search_entry.focus_set()
    win.update_idletasks()
    win.grab_set()


class RecipeIngredientDialog(ttb.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        editor: RecipeEditorHost,
        product_service: "ProductService",
        master_svc: IngredientMasterService,
        ingredient_service: "IngredientService",
        ingredient: dict[str, Any] | None = None,
    ):
        title = "Editar ingrediente da ficha" if ingredient else "Adicionar novo ingrediente à ficha técnica"
        super().__init__(
            title=title,
            size=(840, 560),
            transient=parent.winfo_toplevel(),
        )
        apply_window_icon(self)
        self._editor = editor
        self._ps = product_service
        self._master = master_svc
        self._ing_svc = ingredient_service
        self._ingredient = ingredient
        self._editing_id = str(
            (ingredient or {}).get("ingrediente_ficha_id") or (ingredient or {}).get("ingrediente_id") or ""
        )
        self._sel_master_id: str | None = None
        self._inter_label_to_pid: dict[str, str] = {}

        self._mode = tk.StringVar(value="Ingrediente cadastrado")
        self._search = tk.StringVar()
        self._filter = tk.StringVar(value="Todos")
        self._qty = tk.StringVar()
        self._unit = tk.StringVar(value="kg")
        self._inter_cost_unit = tk.StringVar(value="kg")
        self._preview = tk.StringVar(value="Custo estimado: —")
        self._help = tk.StringVar(value=_help_for_cost("kg"))
        self._selected_text = tk.StringVar(value="Nenhum ingrediente selecionado.")

        self.grab_set()

        self._build()
        self._load_initial(ingredient)
        self._refresh_master_tree()
        self._refresh_intermediate_combo()
        self._sync_mode()
        self._trace_preview()

    def _build(self) -> None:
        outer = ttb.Frame(self, padding=SPACING_MD)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        title = "Editar ingrediente da ficha" if self._ingredient else "Adicionar novo ingrediente à ficha técnica"
        ttb.Label(outer, text=title, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")

        top = ttb.Frame(outer)
        top.grid(row=1, column=0, sticky="ew", pady=(SPACING_MD, SPACING_SM))
        top.columnconfigure(3, weight=1)
        ttb.Label(top, text="Tipo:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self._mode_combo = ttb.Combobox(
            top,
            textvariable=self._mode,
            values=("Ingrediente cadastrado", "Ficha intermediária"),
            state="readonly",
            width=24,
        )
        self._mode_combo.grid(row=0, column=1, sticky="w", padx=(0, SPACING_MD))
        self._mode_combo.bind("<<ComboboxSelected>>", lambda _e: self._sync_mode())
        self._btn_new = ttb.Button(top, text="Cadastrar novo ingrediente", command=self._open_catalog)
        self._btn_new.grid(row=0, column=2, sticky="w")
        style_button(self._btn_new, "secondary")

        self._master_frame = ttb.Frame(outer)
        self._master_frame.grid(row=2, column=0, sticky="nsew")
        self._master_frame.columnconfigure(0, weight=1)
        self._master_frame.rowconfigure(1, weight=1)

        filters = ttb.Frame(self._master_frame)
        filters.grid(row=0, column=0, sticky="ew", pady=(0, SPACING_SM))
        filters.columnconfigure(1, weight=1)
        ttb.Label(filters, text="Pesquisar ingrediente:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttb.Entry(filters, textvariable=self._search, width=30).grid(row=0, column=1, sticky="ew", padx=(0, SPACING_MD))
        self._search.trace_add("write", lambda *_: self._refresh_master_tree())
        ttb.Label(filters, text="Classificação:").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self._filter_combo = ttb.Combobox(
            filters,
            textvariable=self._filter,
            values=("Todos", "Ingrediente simples", "Matéria-prima"),
            state="readonly",
            width=18,
        )
        self._filter_combo.grid(row=0, column=3, sticky="w")
        self._filter.trace_add("write", lambda *_: self._refresh_master_tree())

        cols = ("nome", "cls", "uc", "preco")
        self._master_tree = ttb.Treeview(self._master_frame, columns=cols, show="headings", height=8)
        for c, text, width, anchor in [
            ("nome", "Nome", 260, "w"),
            ("cls", "Classificação", 140, "w"),
            ("uc", "Custo por", 90, "center"),
            ("preco", "Preço cadastrado", 130, "e"),
        ]:
            self._master_tree.heading(c, text=text)
            self._master_tree.column(c, width=width, anchor=anchor)
        self._master_tree.grid(row=1, column=0, sticky="nsew")
        configure_treeview_zebra(self._master_tree)
        self._master_tree.bind("<<TreeviewSelect>>", self._on_master_selected)
        self._empty_master_label = ttb.Label(
            self._master_frame,
            text="Nenhum ingrediente cadastrado. Cadastre um ingrediente antes de inserir na ficha técnica.",
            style="Muted.TLabel",
        )
        self._empty_master_label.grid(row=2, column=0, sticky="w", pady=(SPACING_SM, 0))

        self._inter_frame = ttb.Frame(outer)
        self._inter_frame.grid(row=2, column=0, sticky="nsew")
        self._inter_frame.columnconfigure(1, weight=1)
        ttb.Label(self._inter_frame, text="Ficha intermediária:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self._combo_inter = ttb.Combobox(self._inter_frame, state="readonly", width=52)
        self._combo_inter.grid(row=0, column=1, sticky="ew")
        self._combo_inter.bind("<<ComboboxSelected>>", lambda _e: self._sync_unit_for_selection())
        ttb.Label(self._inter_frame, text="Unidade de uso:").grid(row=1, column=0, sticky="w", pady=(SPACING_SM, 0))
        self._combo_inter_cost = ttb.Combobox(
            self._inter_frame,
            textvariable=self._inter_cost_unit,
            values=("kg", "L", "un"),
            state="disabled",
            width=14,
        )
        self._combo_inter_cost.grid(row=1, column=1, sticky="w", pady=(SPACING_SM, 0))
        self._empty_inter_label = ttb.Label(
            self._inter_frame,
            text="Nenhuma ficha intermediária disponível.",
            style="Muted.TLabel",
        )
        self._empty_inter_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(SPACING_SM, 0))

        self._selected_frame = ttb.Labelframe(outer, text="Ingrediente selecionado", padding=SPACING_MD)
        self._selected_frame.grid(row=3, column=0, sticky="ew", pady=(SPACING_MD, 0))
        ttb.Label(
            self._selected_frame,
            textvariable=self._selected_text,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self._usage_frame = ttb.Labelframe(outer, text="Quantidade usada nesta ficha", padding=SPACING_MD)
        self._usage_frame.grid(row=4, column=0, sticky="ew", pady=(SPACING_MD, 0))
        self._usage_frame.columnconfigure(1, weight=1)
        ttb.Label(self._usage_frame, text="Quantidade utilizada:").grid(row=0, column=0, sticky="w")
        ttb.Entry(self._usage_frame, textvariable=self._qty, width=14).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(6, SPACING_MD),
        )
        ttb.Label(self._usage_frame, text="Unidade fixa:").grid(row=0, column=2, sticky="w")
        self._unit_combo = ttb.Combobox(
            self._usage_frame,
            textvariable=self._unit,
            values=("kg",),
            state="readonly",
            width=12,
        )
        self._unit_combo.grid(row=0, column=3, sticky="w", padx=(6, 0))
        ttb.Label(self._usage_frame, textvariable=self._help, style="Muted.TLabel", wraplength=680).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(SPACING_SM, 0)
        )
        ttb.Label(
            self._usage_frame,
            textvariable=self._preview,
            foreground=SUCCESS_COLOR,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(SPACING_SM, 0))

        actions = ttb.Frame(outer)
        actions.grid(row=5, column=0, sticky="e", pady=(SPACING_MD, 0))
        self._btn_add = ttb.Button(
            actions,
            text="Salvar ingrediente na ficha" if self._ingredient else "Inserir ingrediente na ficha técnica",
            command=self._save,
            state="disabled",
        )
        self._btn_add.pack(side="right", padx=(SPACING_SM, 0))
        style_button(self._btn_add, "primary")
        btn_cancel = ttb.Button(actions, text="Cancelar", command=self.destroy)
        btn_cancel.pack(side="right")
        style_button(btn_cancel, "secondary")

    def _trace_preview(self) -> None:
        def _sync(*_a: object) -> None:
            self.after(0, self._sync_insert_state)

        self._qty.trace_add("write", _sync)
        self._unit.trace_add("write", _sync)

    def _load_initial(self, ingredient: dict[str, Any] | None) -> None:
        if not ingredient:
            return
        if str(ingredient.get("origem_linha", "") or "") == ORIGEM_FICHA_INTERMEDIARIA or ingredient.get("produto_ref_id"):
            self._mode.set("Ficha intermediária")
            self._inter_cost_unit.set(str(ingredient.get("unidade_custo", "") or "kg"))
        else:
            self._mode.set("Ingrediente cadastrado")
            self._sel_master_id = str(ingredient.get("ingrediente_cadastro_id", "") or "")
        self._qty.set(str(ingredient.get("quantidade", "") or "1"))
        self._unit.set(str(ingredient.get("unidade", "") or "kg"))

    def _sync_mode(self) -> None:
        if self._mode.get() == "Ficha intermediária":
            self._master_frame.grid_remove()
            self._inter_frame.grid()
            self._btn_new.configure(state="disabled")
        else:
            self._inter_frame.grid_remove()
            self._master_frame.grid()
            self._btn_new.configure(state="normal")
        self._sync_unit_for_selection()

    def _sync_unit_for_selection(self) -> None:
        if self._mode.get() == "Ficha intermediária":
            self._inter_cost_unit.set(self._intermediate_cost_unit())
        cost_unit = self._current_cost_unit()
        unit = _base_unit_for_cost(cost_unit)
        vals = (unit,) if unit else tuple(get_units_for_cost_unit(cost_unit))
        self._unit_combo.configure(values=vals)
        if unit:
            self._unit.set(unit)
        self._help.set(_help_for_cost(cost_unit))
        self._sync_quantity_area()
        self._sync_insert_state()

    def _sync_quantity_area(self) -> None:
        has_selection = bool(self._candidate())
        if has_selection:
            self._usage_frame.grid()
        else:
            self._usage_frame.grid_remove()

    def _current_cost_unit(self) -> str:
        if self._mode.get() == "Ficha intermediária":
            return self._inter_cost_unit.get().strip() or "kg"
        row = self._selected_master_row()
        return str(row.get("unidade_custo", "") or "kg") if row else "kg"

    def _selected_intermediate_row(self) -> dict[str, Any] | None:
        label = self._combo_inter.get()
        pid = self._inter_label_to_pid.get(label, "")
        return self._ps.get_product_row(pid) if pid else None

    def _intermediate_cost_unit(self) -> str:
        return _cost_unit_for_intermediate_product(self._selected_intermediate_row())

    def _sync_selected_text(self) -> None:
        cand = self._candidate()
        if not cand:
            self._selected_text.set("Nenhum ingrediente selecionado.")
            return
        self._selected_text.set(str(cand.get("nome", "") or "(sem nome)"))

    def _can_insert(self) -> bool:
        cand = self._candidate()
        return bool(cand) and bool(self._qty.get().strip()) and to_float(self._qty.get()) > 0

    def _sync_insert_state(self) -> None:
        self._sync_selected_text()
        self._refresh_preview()
        self._btn_add.configure(state=("normal" if self._can_insert() else "disabled"))

    def _selected_master_row(self) -> dict[str, Any] | None:
        if not self._sel_master_id:
            return None
        return self._master.get_row(self._sel_master_id)

    def _refresh_master_tree(self) -> None:
        from app.ui.components import clear_tree

        selected = self._sel_master_id
        clear_tree(self._master_tree)
        rows = self._master.list_filtered(self._search.get(), self._filter.get())
        for idx, r in enumerate(rows):
            iid = str(r.get("ingrediente_id", "") or "")
            if not iid:
                continue
            cls = str(r.get("classificacao", ""))
            cls_l = "Ingrediente cadastrado" if cls == CLASSIFICACAO_INGREDIENTE_SIMPLES else "Matéria-prima"
            tag = "even" if (idx + 1) % 2 == 0 else "odd"
            self._master_tree.insert(
                "",
                "end",
                iid=iid,
                tags=(tag,),
                values=(r.get("nome", ""), cls_l, r.get("unidade_custo", ""), _preco_display_master(r)),
            )
        if selected and self._master_tree.exists(selected):
            self._master_tree.selection_set(selected)
            self._master_tree.focus(selected)
            self._master_tree.see(selected)
        if rows:
            self._empty_master_label.grid_remove()
        else:
            if self._search.get().strip():
                self._empty_master_label.configure(text="Nenhum ingrediente encontrado para a pesquisa.")
            else:
                self._empty_master_label.configure(
                    text="Nenhum ingrediente cadastrado. Cadastre um ingrediente antes de inserir na ficha técnica."
                )
            self._empty_master_label.grid()

    def _refresh_intermediate_combo(self) -> None:
        prods = self._ps.list_materia_prima_for_composto(str(self._editor.product_id))
        bases = [str(p.get("nome") or "").strip() or "(sem nome)" for p in prods]
        cnt = Counter(bases)
        labels: list[str] = []
        self._inter_label_to_pid = {}
        for p in prods:
            pid = str(p.get("produto_id"))
            base = str(p.get("nome") or "").strip() or "(sem nome)"
            label = f"{base} · {pid[:8]}" if cnt[base] > 1 else base
            labels.append(label)
            self._inter_label_to_pid[label] = pid
        self._combo_inter.configure(values=labels)
        current_ref = str((self._ingredient or {}).get("produto_ref_id", "") or "")
        if current_ref:
            for label, pid in self._inter_label_to_pid.items():
                if pid == current_ref:
                    self._combo_inter.set(label)
                    break
        elif labels:
            self._combo_inter.set(labels[0])
        else:
            self._combo_inter.set("")
        if labels:
            self._empty_inter_label.grid_remove()
        else:
            self._empty_inter_label.grid()
        self._sync_unit_for_selection()

    def _on_master_selected(self, _event: object | None = None) -> None:
        sel = self._master_tree.selection()
        self._sel_master_id = sel[0] if sel else None
        self._sync_unit_for_selection()

    def _open_catalog(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        win = open_ingredient_master_editor(self, self._master, on_saved=self._after_catalog_saved)
        try:
            win.wait_window()
        finally:
            if self.winfo_exists():
                self.grab_set()
                self.focus_set()

    def _after_catalog_saved(self) -> None:
        self._refresh_master_tree()
        self._sync_mode()

    def _candidate(self) -> dict[str, Any] | None:
        q = to_float(self._qty.get())
        if self._mode.get() == "Ficha intermediária":
            label = self._combo_inter.get()
            pid = self._inter_label_to_pid.get(label, "")
            row = self._selected_intermediate_row()
            if not row:
                return None
            cost_unit = _cost_unit_for_intermediate_product(row)
            self._inter_cost_unit.set(cost_unit)
            return build_line_from_intermediate_product(
                self._editor.product_id,
                pid,
                str(row.get("nome", "")),
                q,
                self._unit.get().strip(),
                cost_unit,
                ingrediente_ficha_id=self._editing_id,
            )
        row = self._selected_master_row()
        if not row:
            return None
        return build_line_from_master(
            self._editor.product_id,
            row,
            q,
            self._unit.get().strip(),
            ingrediente_ficha_id=self._editing_id,
        )

    def _refresh_preview(self) -> None:
        cand = self._candidate()
        if not cand:
            self._preview.set("Custo estimado: —")
            return
        try:
            if self._mode.get() == "Ficha intermediária":
                from app.services.recipe_calculation_service import build_products_by_id_from_rows

                by_id = build_products_by_id_from_rows(self._ps.list_active_products())
                cost = calc_ingredient_cost(cand, by_id)
            else:
                cost = calc_ingredient_cost(cand, {})
            self._preview.set(f"Custo estimado: {format_money_br(cost)}")
        except Exception:
            self._preview.set("Custo estimado: —")

    def _validate(self, cand: dict[str, Any] | None) -> bool:
        if self._mode.get() == "Ingrediente cadastrado" and not self._sel_master_id:
            messagebox.showwarning("Seleção", "Selecione um ingrediente cadastrado.", parent=self)
            return False
        if self._mode.get() == "Ficha intermediária" and not cand:
            messagebox.showwarning("Seleção", "Selecione uma ficha intermediária.", parent=self)
            return False
        q_text = self._qty.get().strip()
        if not q_text:
            messagebox.showwarning("Validação", "Informe a quantidade usada na receita.", parent=self)
            return False
        q = to_float(q_text)
        if q <= 0:
            messagebox.showwarning("Validação", "Informe quantidade maior que zero.", parent=self)
            return False
        if cand and not is_valid_unit_for_cost_unit(cand.get("unidade"), cand.get("unidade_custo")):
            messagebox.showerror("Validação", "Unidade usada incompatível com a unidade de custo.", parent=self)
            return False
        return True

    def _save(self) -> None:
        cand = self._candidate()
        if not self._validate(cand) or cand is None:
            return
        if find_duplicate_ingredient_warning(self._editor._ingredients, cand):
            if not messagebox.askyesno("Duplicidade", "Ingrediente semelhante já existe na ficha. Adicionar mesmo assim?", parent=self):
                return
        self._editor.upsert_ingredient(cand)
        self.destroy()


class RecipeIngredientsPanel(ttb.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        editor: RecipeEditorHost,
        product_service: "ProductService",
        master_svc: IngredientMasterService,
        ingredient_service: "IngredientService" | None = None,
    ):
        super().__init__(parent, padding=SPACING_MD)
        self._editor = editor
        self._ps = product_service
        self._master = master_svc
        self._ing_svc = ingredient_service
        self._editing_id: str | None = None
        self._sub = ttb.Notebook(self)
        self._sub.pack(fill="both", expand=True)

        self._tab_base = ttb.Frame(self._sub, padding=SPACING_MD)
        self._tab_inter = ttb.Frame(self._sub, padding=SPACING_MD)
        self._tab_new = ttb.Frame(self._sub, padding=SPACING_MD)
        self._sub.add(self._tab_base, text="Ingrediente cadastrado")
        self._sub.add(self._tab_inter, text="Ficha intermediária")
        self._sub.add(self._tab_new, text="Cadastrar novo ingrediente")

        self._search_m = tk.StringVar()
        self._filt_m = tk.StringVar(value="Todos")
        self._qty_m = tk.StringVar(value="1")
        self._un_m = tk.StringVar(value="kg")
        self._preview_m = tk.StringVar(value="—")
        self._selected_master_name = tk.StringVar(value="Nenhum ingrediente selecionado")
        self._sel_master_id: str | None = None

        r0 = ttb.Frame(self._tab_base)
        r0.pack(fill="x")
        ttb.Label(r0, text="Pesquisar:").pack(side="left")
        ttb.Entry(r0, textvariable=self._search_m, width=28).pack(side="left", padx=4)
        self._search_m.trace_add("write", lambda *_: self._refresh_master_tree())
        ttb.Label(r0, text="Classificação").pack(side="left", padx=(12, 0))
        ttb.Combobox(
            r0,
            textvariable=self._filt_m,
            values=("Todos", "Ingrediente simples", "Matéria-prima"),
            state="readonly",
            width=18,
        ).pack(side="left", padx=4)
        self._filt_m.trace_add("write", lambda *_: self._refresh_master_tree())

        cols = ("nome", "cls", "uc", "preco", "ativo")
        self._tree_m = ttb.Treeview(self._tab_base, columns=cols, show="headings", height=7)
        for c, t, w in [
            ("nome", "Nome", 200),
            ("cls", "Classificação", 120),
            ("uc", "Un. custo", 70),
            ("preco", "Preço", 100),
            ("ativo", "Ativo", 50),
        ]:
            self._tree_m.heading(c, text=t)
            self._tree_m.column(c, width=w)
        self._tree_m.pack(fill="both", expand=True, pady=6)
        configure_treeview_zebra(self._tree_m)
        self._tree_m.bind("<<TreeviewSelect>>", self._on_sel_master)

        usage = ttb.Labelframe(self._tab_base, text="Uso do ingrediente nesta ficha", padding=SPACING_MD)
        usage.pack(fill="x", pady=(0, 4))
        usage.columnconfigure(1, weight=1)
        ttb.Label(usage, text="Ingrediente selecionado:").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttb.Label(
            usage,
            textvariable=self._selected_master_name,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=1, columnspan=4, sticky="w", padx=(6, 0), pady=(0, 6))
        ttb.Label(usage, text="Quantidade usada na receita:").grid(row=1, column=0, sticky="w")
        ttb.Entry(usage, textvariable=self._qty_m, width=14).grid(row=1, column=1, sticky="w", padx=(6, 16))
        ttb.Label(usage, text="Unidade:").grid(row=1, column=2, sticky="w")
        self._combo_un_m = ttb.Combobox(usage, textvariable=self._un_m, width=12, state="readonly")
        self._combo_un_m.grid(row=1, column=3, sticky="w", padx=(6, 16))
        self._btn_add_master = ttb.Button(
            usage,
            text="Adicionar ingrediente à ficha",
            command=self._add_master_line,
        )
        self._btn_add_master.grid(row=1, column=4, sticky="e")
        style_button(self._btn_add_master, "primary")
        ttb.Label(
            usage,
            textvariable=self._preview_m,
            foreground=SUCCESS_COLOR,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=2, column=1, columnspan=4, sticky="w", padx=(6, 0), pady=(6, 0))

        self._inter_labels: list[str] = []
        self._inter_label_to_pid: dict[str, str] = {}
        self._combo_inter: ttb.Combobox | None = None
        self._qty_i = tk.StringVar(value="1")
        self._un_i = tk.StringVar(value="kg")
        self._uc_i = tk.StringVar(value="kg")
        self._preview_i = tk.StringVar(value="—")

        ttb.Label(
            self._tab_inter,
            text="Semi-acabado produzido internamente (outra ficha técnica). Não confunde com ingrediente comprado.",
            wraplength=640,
            foreground=MUTED_TEXT_COLOR,
        ).pack(anchor="w", pady=4)
        ri = ttb.Frame(self._tab_inter)
        ri.pack(fill="x")
        ttb.Label(ri, text="Ficha").pack(side="left")
        self._combo_inter = ttb.Combobox(ri, state="readonly", width=48)
        self._combo_inter.pack(side="left", padx=6, fill="x", expand=True)
        self._combo_inter.bind("<<ComboboxSelected>>", lambda e: self._refresh_inter_preview())
        ri2 = ttb.Labelframe(self._tab_inter, text="Uso da ficha intermediária nesta ficha", padding=SPACING_MD)
        ri2.pack(fill="x", pady=6)
        ri2.columnconfigure(1, weight=1)
        ttb.Label(ri2, text="Quantidade usada na receita:").grid(row=0, column=0, sticky="w")
        ttb.Entry(ri2, textvariable=self._qty_i, width=14).grid(row=0, column=1, sticky="w", padx=(6, 16))
        ttb.Label(ri2, text="Unidade:").grid(row=0, column=2, sticky="w")
        self._combo_un_i = ttb.Combobox(ri2, textvariable=self._un_i, width=12, state="readonly")
        self._combo_un_i.grid(row=0, column=3, sticky="w", padx=(6, 16))
        ttb.Label(ri2, text="Unidade de custo:").grid(row=0, column=4, sticky="w")
        self._combo_uc_i = ttb.Combobox(
            ri2,
            textvariable=self._uc_i,
            values=list(COST_UNIT_OPTIONS),
            width=10,
            state="readonly",
        )
        self._combo_uc_i.grid(row=0, column=5, sticky="w", padx=(6, 16))
        self._combo_uc_i.bind("<<ComboboxSelected>>", lambda e: self._on_inter_cost_unit_changed())
        self._btn_add_inter = ttb.Button(ri2, text="Adicionar à ficha", command=self._add_inter_line)
        self._btn_add_inter.grid(row=0, column=6, sticky="e")
        style_button(self._btn_add_inter, "primary")
        ttb.Label(ri2, textvariable=self._preview_i, foreground=SUCCESS_COLOR, font=("Segoe UI", 10, "bold")).grid(
            row=1, column=1, columnspan=6, sticky="w", padx=(6, 0), pady=(6, 0)
        )

        new_box = ttb.Frame(self._tab_new)
        new_box.pack(fill="both", expand=True)
        self._btn_open_new_master = ttb.Button(
            new_box,
            text="Cadastrar novo ingrediente",
            command=self._open_new_ingredient_dialog,
        )
        self._btn_open_new_master.pack(anchor="center", pady=SPACING_MD)
        style_button(self._btn_open_new_master, "primary")

        self._refresh_master_tree()
        self._refresh_intermediate_combo()
        self._sync_inter_units()
        self._trace_preview_master()
        self._trace_preview_inter()

    def _trace_preview_master(self) -> None:
        def _u(*_a: object) -> None:
            self.after(0, self._update_preview_master)

        self._qty_m.trace_add("write", _u)
        self._un_m.trace_add("write", _u)

    def _trace_preview_inter(self) -> None:
        def _u(*_a: object) -> None:
            self.after(0, self._refresh_inter_preview)

        self._qty_i.trace_add("write", _u)
        self._un_i.trace_add("write", _u)

    def _sync_inter_units(self) -> None:
        allowed = get_units_for_cost_unit(self._uc_i.get().strip())
        cur = self._un_i.get().strip()
        vals = ensure_in_options(cur, allowed)
        self._combo_un_i.configure(values=vals)
        if not is_valid_unit_for_cost_unit(cur, self._uc_i.get().strip()) and allowed:
            self._un_i.set(allowed[0])

    def _on_inter_cost_unit_changed(self) -> None:
        self._sync_inter_units()
        self._refresh_inter_preview()

    def _on_sel_master(self, _e=None) -> None:
        sel = self._tree_m.selection()
        self._sel_master_id = None
        if not sel:
            self._selected_master_name.set("Nenhum ingrediente selecionado")
            self._update_preview_master()
            return
        iid = sel[0]
        self._sel_master_id = iid
        row = self._master.get_row(iid)
        if row:
            self._selected_master_name.set(str(row.get("nome", "") or "(sem nome)"))
            uc = str(row.get("unidade_custo", "kg"))
            allowed = get_units_for_cost_unit(uc)
            cur = self._un_m.get().strip()
            vals = ensure_in_options(cur, allowed)
            self._combo_un_m.configure(values=vals)
            if not is_valid_unit_for_cost_unit(cur, uc) and allowed:
                self._un_m.set(allowed[0])
        else:
            self._selected_master_name.set("Nenhum ingrediente selecionado")
        self._update_preview_master()

    def _update_preview_master(self) -> None:
        if not self._sel_master_id:
            self._preview_m.set("—")
            return
        row = self._master.get_row(self._sel_master_id)
        if not row:
            self._preview_m.set("—")
            return
        try:
            cand = build_line_from_master(
                self._editor.product_id,
                row,
                to_float(self._qty_m.get()),
                self._un_m.get().strip(),
                ingrediente_ficha_id=self._editing_id,
            )
            cost = calc_ingredient_cost(cand, {})
            self._preview_m.set(f"Custo estimado: {format_money_br(cost)}")
        except Exception:
            self._preview_m.set("—")

    def _refresh_master_tree(self) -> None:
        from app.ui.components import clear_tree

        clear_tree(self._tree_m)
        for idx, r in enumerate(self._master.list_filtered(self._search_m.get(), self._filt_m.get())):
            iid = str(r.get("ingrediente_id", ""))
            if not iid:
                continue
            cls = str(r.get("classificacao", ""))
            cls_l = "Ingrediente cadastrado" if cls == CLASSIFICACAO_INGREDIENTE_SIMPLES else "Matéria-prima"
            tag = "even" if (idx + 1) % 2 == 0 else "odd"
            self._tree_m.insert(
                "",
                "end",
                iid=iid,
                tags=(tag,),
                values=(
                    r.get("nome", ""),
                    cls_l,
                    r.get("unidade_custo", ""),
                    _preco_display_master(r),
                    "Ativo" if r.get("active", True) else "Inativo",
                ),
            )

    def _refresh_intermediate_combo(self) -> None:
        prods = self._ps.list_materia_prima_for_composto(str(self._editor.product_id))
        bases = [str(p.get("nome") or "").strip() or "(sem nome)" for p in prods]
        cnt = Counter(bases)
        labels: list[str] = []
        self._inter_label_to_pid = {}
        for p in prods:
            pid = str(p.get("produto_id"))
            base = str(p.get("nome") or "").strip() or "(sem nome)"
            label = f"{base} · {pid[:8]}" if cnt[base] > 1 else base
            labels.append(label)
            self._inter_label_to_pid[label] = pid
        self._inter_labels = labels
        if self._combo_inter:
            self._combo_inter.configure(values=labels)
            if labels:
                self._combo_inter.set(labels[0])
            else:
                self._combo_inter.set("")
        self._refresh_inter_preview()

    def _refresh_inter_preview(self) -> None:
        if not self._combo_inter:
            return
        label = self._combo_inter.get()
        pid = self._inter_label_to_pid.get(label, "")
        row = self._ps.get_product_row(pid) if pid else None
        if not row:
            self._preview_i.set("—")
            return
        try:
            cand = build_line_from_intermediate_product(
                self._editor.product_id,
                pid,
                str(row.get("nome", "")),
                to_float(self._qty_i.get()),
                self._un_i.get().strip(),
                self._uc_i.get().strip(),
                ingrediente_ficha_id=self._editing_id,
            )
            by = self._ps.list_active_products()
            from app.services.recipe_calculation_service import build_products_by_id_from_rows

            cost = calc_ingredient_cost(cand, build_products_by_id_from_rows(by))
            self._preview_i.set(f"Custo estimado: {format_money_br(cost)}")
        except Exception:
            self._preview_i.set("—")

    def _add_master_line(self) -> None:
        if not self._sel_master_id:
            messagebox.showwarning("Atenção", "Selecione um ingrediente cadastrado.")
            return
        row = self._master.get_row(self._sel_master_id)
        if not row:
            return
        q = to_float(self._qty_m.get())
        un = self._un_m.get().strip()
        uc = str(row.get("unidade_custo", "") or "")
        if q <= 0:
            messagebox.showwarning("Validação", "Informe quantidade maior que zero.")
            return
        if not is_valid_unit_for_cost_unit(un, uc):
            messagebox.showerror("Validação", "Unidade usada incompatível com a unidade de custo do ingrediente.")
            return
        cand = build_line_from_master(
            self._editor.product_id, row, q, un, ingrediente_ficha_id=self._editing_id
        )
        if find_duplicate_ingredient_warning(self._editor._ingredients, cand):
            if not messagebox.askyesno("Duplicidade", "Ingrediente semelhante já existe na ficha. Adicionar mesmo assim?"):
                return
        self._editor.upsert_ingredient(cand)
        self._clear_form()

    def _add_inter_line(self) -> None:
        label = self._combo_inter.get() if self._combo_inter else ""
        pid = self._inter_label_to_pid.get(label, "")
        if not pid:
            messagebox.showwarning("Atenção", "Não há ficha intermediária disponível ou selecione uma.")
            return
        row = self._ps.get_product_row(pid)
        if not row:
            return
        q = to_float(self._qty_i.get())
        un = self._un_i.get().strip()
        uc = self._uc_i.get().strip()
        if q <= 0:
            messagebox.showwarning("Validação", "Informe quantidade maior que zero.")
            return
        if not is_valid_unit_for_cost_unit(un, uc):
            messagebox.showerror("Validação", "Unidade usada incompatível com a unidade de custo.")
            return
        cand = build_line_from_intermediate_product(
            self._editor.product_id,
            pid,
            str(row.get("nome", "")),
            q,
            un,
            uc,
            ingrediente_ficha_id=self._editing_id,
        )
        if find_duplicate_ingredient_warning(self._editor._ingredients, cand):
            if not messagebox.askyesno("Duplicidade", "Referência semelhante já existe na ficha. Adicionar mesmo assim?"):
                return
        self._editor.upsert_ingredient(cand)
        self._clear_form()

    def _on_new_master_saved(self) -> None:
        self._refresh_master_tree()
        self._sub.select(self._tab_base)

    def _open_new_ingredient_dialog(self) -> None:
        open_ingredient_master_editor(self.winfo_toplevel(), self._master, on_saved=self._on_new_master_saved)

    def refresh_materia_prima_list(self) -> None:
        self._refresh_intermediate_combo()

    def _clear_form(self) -> None:
        self._editing_id = None
        self._qty_m.set("1")
        self._qty_i.set("1")
        self._sel_master_id = None
        if self._tree_m.selection():
            self._tree_m.selection_remove(self._tree_m.selection())
        self._selected_master_name.set("Nenhum ingrediente selecionado")
        self._preview_m.set("—")
        self._preview_i.set("—")

    def add_current_selection(self) -> None:
        current = self._sub.select()
        if current == str(self._tab_inter):
            self._add_inter_line()
            return
        if current == str(self._tab_new):
            self._open_new_ingredient_dialog()
            return
        self._add_master_line()

    def load_ingredient(self, ing: dict[str, Any]) -> None:
        self._editing_id = str(ing.get("ingrediente_ficha_id") or ing.get("ingrediente_id") or "")
        o = str(ing.get("origem_linha", "") or "")
        if o == ORIGEM_FICHA_INTERMEDIARIA:
            self._sub.select(1)
            ref = str(ing.get("produto_ref_id", "") or "")
            for lab, pid in self._inter_label_to_pid.items():
                if pid == ref and self._combo_inter:
                    self._combo_inter.set(lab)
                    break
            self._qty_i.set(str(ing.get("quantidade", "")))
            self._un_i.set(str(ing.get("unidade", "") or ""))
            self._uc_i.set(str(ing.get("unidade_custo", "") or ""))
            self._sync_inter_units()
            self._refresh_inter_preview()
        else:
            self._sub.select(0)
            mid = str(ing.get("ingrediente_cadastro_id", "") or "")
            if mid:
                self._tree_m.selection_set(mid)
                self._tree_m.focus(mid)
                self._sel_master_id = mid
            self._qty_m.set(str(ing.get("quantidade", "")))
            self._un_m.set(str(ing.get("unidade", "") or ""))
            self._on_sel_master()

    def set_read_only(self, ro: bool) -> None:
        def walk(w: tk.Widget) -> None:
            for c in w.winfo_children():
                if isinstance(c, ttb.Treeview):
                    try:
                        c.configure(selectmode=("none" if ro else "browse"))
                    except tk.TclError:
                        pass
                    continue
                if isinstance(c, ttb.Notebook):
                    walk(c)
                    continue
                if isinstance(c, ttb.Button):
                    try:
                        c.configure(state=("disabled" if ro else "normal"))
                    except tk.TclError:
                        pass
                elif isinstance(c, ttb.Entry):
                    try:
                        c.configure(state=("disabled" if ro else "normal"))
                    except tk.TclError:
                        pass
                elif isinstance(c, ttb.Combobox):
                    try:
                        c.configure(state=("disabled" if ro else "readonly"))
                    except tk.TclError:
                        pass
                walk(c)

        walk(self)
