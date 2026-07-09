"""Aba de gestão do cadastro mestre (banco_ingredientes)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox

import ttkbootstrap as ttb

from app.config.settings import (
    CLASSIFICACAO_INGREDIENTE_SIMPLES,
)
from app.services.ingredient_master_service import IngredientMasterService, IngredientMasterServiceError
from app.ui.catalog_dialog import UNIT_COST_OPTIONS, catalog_cost_for_save, cost_help_text
from app.ui.components import clear_tree, section_header
from app.ui.styles import SPACING_LG, SPACING_MD, SPACING_SM, configure_treeview_zebra, style_button
from app.ui.window_icon import apply_window_icon
from app.utils.money import format_money_br
from app.utils.units import normalize_cost_unit_key


def _preco_resumo(row: dict) -> str:
    uc = normalize_cost_unit_key(row.get("unidade_custo"))
    if uc == "kg":
        return format_money_br(row.get("preco_kg")) + "/kg"
    if uc in ("l", "ml"):
        return format_money_br(row.get("preco_litro")) + "/L"
    if uc == "un":
        return format_money_br(row.get("preco_unidade")) + "/un"
    return "—"


def open_ingredient_master_editor(
    parent: tk.Widget,
    master_svc: IngredientMasterService,
    existing_id: str | None = None,
    on_saved: Callable[[], None] | None = None,
    on_saved_id: Callable[[str], None] | None = None,
) -> ttb.Toplevel:
    top = ttb.Toplevel(parent)
    apply_window_icon(top)
    top.title("Ingrediente" if existing_id else "Novo ingrediente")
    top.geometry("630x405")
    top.transient(parent.winfo_toplevel())
    top.grab_set()

    row = master_svc.get_row(existing_id) if existing_id else None
    v_nome = tk.StringVar(value=str(row.get("nome", "")) if row else "")

    def unit_choice_from_row(data: dict | None) -> str:
        ck = normalize_cost_unit_key((data or {}).get("unidade_custo"))
        if ck in ("l", "ml"):
            return "L"
        if ck == "un":
            return "unidade"
        return "kg"

    def price_from_row(data: dict | None) -> str:
        if not data:
            return ""
        ck = normalize_cost_unit_key(data.get("unidade_custo"))
        if ck in ("l", "ml"):
            return str(data.get("preco_litro", "") or "")
        if ck == "un":
            return str(data.get("preco_unidade", "") or "")
        return str(data.get("preco_kg", "") or "")

    v_uc = tk.StringVar(value=unit_choice_from_row(row))
    v_price = tk.StringVar(value=price_from_row(row))
    v_quantity = tk.StringVar()
    v_help = tk.StringVar(value=cost_help_text(v_uc.get()))

    frm = ttb.Frame(top, padding=SPACING_MD)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(1, weight=1)

    r = 0
    ttb.Label(frm, text="Nome*").grid(row=r, column=0, sticky="w", pady=4)
    entry_nome = ttb.Entry(frm, textvariable=v_nome, width=46)
    entry_nome.grid(row=r, column=1, sticky="ew", pady=4)
    r += 1
    ttb.Label(frm, text="Unidade de custo*").grid(row=r, column=0, sticky="w", pady=4)
    ttb.Combobox(
        frm,
        textvariable=v_uc,
        values=UNIT_COST_OPTIONS,
        state="readonly",
        width=14,
    ).grid(row=r, column=1, sticky="w", pady=4)
    r += 1
    price_label = ttb.Label(frm, text="Preço por kg*")
    price_label.grid(row=r, column=0, sticky="w", pady=4)
    ttb.Entry(frm, textvariable=v_price, width=14).grid(row=r, column=1, sticky="w", pady=4)
    r += 1
    quantity_label = ttb.Label(frm, text="Peso do saco em kg*")
    quantity_entry = ttb.Entry(frm, textvariable=v_quantity, width=14)
    quantity_row = r
    r += 1

    help_label = ttb.Label(frm, textvariable=v_help, style="Muted.TLabel", wraplength=560, justify="left")
    help_label.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(SPACING_SM, SPACING_MD))
    r += 1

    def apply_cost_fields(*_a: object) -> None:
        choice = v_uc.get().strip()
        v_help.set(cost_help_text(choice))
        quantity_label.grid_remove()
        quantity_entry.grid_remove()
        if choice == "kg":
            price_label.configure(text="Preço por kg*")
        elif choice == "L":
            price_label.configure(text="Preço por litro*")
        elif choice == "saco":
            price_label.configure(text="Preço do saco*")
            quantity_label.configure(text="Peso do saco em kg*")
            quantity_label.grid(row=quantity_row, column=0, sticky="w", pady=4)
            quantity_entry.grid(row=quantity_row, column=1, sticky="w", pady=4)
        elif choice == "unidade":
            price_label.configure(text="Preço da unidade*")
        elif choice == "cartela":
            price_label.configure(text="Preço da cartela*")
            quantity_label.configure(text="Quantidade de unidades na cartela*")
            quantity_label.grid(row=quantity_row, column=0, sticky="w", pady=4)
            quantity_entry.grid(row=quantity_row, column=1, sticky="w", pady=4)

    v_uc.trace_add("write", apply_cost_fields)
    apply_cost_fields()

    def save() -> None:
        nome = v_nome.get().strip()
        if not nome:
            messagebox.showwarning("Validação", "Informe o nome.", parent=top)
            return
        try:
            unidade_padrao, uc_save, pk, pl, pu = catalog_cost_for_save(
                v_uc.get(),
                v_price.get(),
                v_quantity.get(),
            )
            if existing_id:
                master_svc.update(
                    existing_id,
                    nome=nome,
                    classificacao=str((row or {}).get("classificacao", "") or CLASSIFICACAO_INGREDIENTE_SIMPLES),
                    categoria=str((row or {}).get("categoria", "") or "Outros"),
                    unidade_padrao=unidade_padrao,
                    unidade_custo=uc_save,
                    preco_kg=pk,
                    preco_litro=pl,
                    preco_unidade=pu,
                    observacoes=str((row or {}).get("observacoes", "") or ""),
                )
                saved_id = existing_id
                messagebox.showinfo("Guardado", "Ingrediente atualizado.", parent=top)
            else:
                saved_id = master_svc.add(
                    nome,
                    CLASSIFICACAO_INGREDIENTE_SIMPLES,
                    "Outros",
                    unidade_padrao,
                    uc_save,
                    pk,
                    pl,
                    pu,
                    "",
                )
                messagebox.showinfo("Guardado", "Ingrediente criado no cadastro mestre.", parent=top)
            top.destroy()
            if on_saved:
                on_saved()
            if on_saved_id:
                on_saved_id(saved_id)
        except ValueError as exc:
            messagebox.showwarning("Validação", str(exc), parent=top)
        except IngredientMasterServiceError as exc:
            messagebox.showerror("Não foi possível salvar", str(exc), parent=top)

    bf = ttb.Frame(frm)
    bf.grid(row=r, column=0, columnspan=2, sticky="e", pady=(SPACING_MD, 0))
    bs = ttb.Button(bf, text="Salvar ingrediente", command=save)
    bs.pack(side="right", padx=4)
    style_button(bs, "primary")
    bc = ttb.Button(bf, text="Cancelar", command=top.destroy)
    bc.pack(side="right", padx=4)
    style_button(bc, "secondary")
    top.after(50, entry_nome.focus_set)
    return top


class IngredientMasterTab(ttb.Frame):
    def __init__(self, parent: tk.Widget, master_svc: IngredientMasterService):
        super().__init__(parent, padding=SPACING_MD)
        self._m = master_svc
        self._search = tk.StringVar()
        self._filt = tk.StringVar(value="Todos")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._build()

    def refresh(self) -> None:
        self._fill_tree()

    def _build(self) -> None:
        sh = section_header(
            self,
            "Ingredientes cadastrados",
            "Gerencie ingredientes utilizados nas fichas técnicas.",
        )
        sh.grid(row=0, column=0, sticky="ew", pady=(0, SPACING_LG))

        top = ttb.Frame(self)
        top.grid(row=1, column=0, sticky="ew", pady=(0, SPACING_MD))
        top.columnconfigure(1, weight=1)
        ttb.Label(top, text="Buscar por nome").grid(row=0, column=0, sticky="w", padx=(0, SPACING_SM))
        ttb.Entry(top, textvariable=self._search, width=28).grid(row=0, column=1, sticky="ew", padx=(0, SPACING_MD))
        self._search.trace_add("write", lambda *_: self._fill_tree())
        btn_ref = ttb.Button(top, text="Atualizar", command=self._fill_tree)
        btn_ref.grid(row=0, column=2, sticky="e")
        style_button(btn_ref, "secondary")

        cols = ("nome", "uc", "preco", "atualizado", "status")
        self.tree = ttb.Treeview(self, columns=cols, show="headings", height=14, selectmode="browse")
        for c, t, w, a in [
            ("nome", "Nome", 260, "w"),
            ("uc", "Unidade de custo", 120, "w"),
            ("preco", "Preço", 130, "e"),
            ("atualizado", "Atualizado em", 120, "w"),
            ("status", "Status", 70, "w"),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=a)
        self.tree.grid(row=2, column=0, sticky="nsew", pady=(0, SPACING_MD))
        configure_treeview_zebra(self.tree)
        self.tree.bind("<Double-1>", lambda _e: self._edit_selected())

        bot = ttb.Frame(self)
        bot.grid(row=3, column=0, sticky="ew")
        b1 = ttb.Button(bot, text="Novo ingrediente", command=self._new_dialog)
        b1.pack(side="left", padx=(0, SPACING_SM))
        style_button(b1, "primary")
        b2 = ttb.Button(bot, text="Editar selecionado", command=self._edit_selected)
        b2.pack(side="left", padx=(0, SPACING_SM))
        style_button(b2, "secondary")
        b3 = ttb.Button(bot, text="Inativar", command=self._inativar)
        b3.pack(side="left", padx=(0, SPACING_SM))
        style_button(b3, "danger")

        self._fill_tree()

    def _fill_tree(self) -> None:
        clear_tree(self.tree)
        for idx, r in enumerate(self._m.list_filtered(self._search.get(), self._filt.get())):
            iid = str(r.get("ingrediente_id", "") or "")
            if not iid:
                continue
            tag = "even" if (idx + 1) % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                iid=iid,
                tags=(tag,),
                values=(
                    r.get("nome", ""),
                    r.get("unidade_custo", ""),
                    _preco_resumo(r),
                    r.get("data_atualizacao", "") or "—",
                    "Ativo" if r.get("active", True) else "Inativo",
                ),
            )

    def _selected_id(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _new_dialog(self) -> None:
        self._open_editor(None)

    def _edit_selected(self) -> None:
        iid = self._selected_id()
        if not iid:
            messagebox.showwarning("Seleção", "Selecione um ingrediente na tabela para editar.")
            return
        self._open_editor(iid)

    def _inativar(self) -> None:
        iid = self._selected_id()
        if not iid:
            messagebox.showwarning("Seleção", "Selecione um ingrediente para inativar.")
            return
        if not messagebox.askyesno(
            "Confirmar inativação",
            "Inativar este ingrediente no cadastro mestre? Ele deixará de aparecer nas pesquisas de novas fichas.",
        ):
            return
        try:
            self._m.soft_delete(iid)
            messagebox.showinfo("Concluído", "Ingrediente inativado.")
            self._fill_tree()
        except IngredientMasterServiceError as exc:
            messagebox.showerror("Não foi possível inativar", str(exc))

    def _open_editor(self, existing_id: str | None) -> None:
        open_ingredient_master_editor(self, self._m, existing_id, on_saved=self._fill_tree)
