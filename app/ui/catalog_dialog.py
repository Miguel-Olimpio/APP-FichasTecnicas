"""Cadastro rápido no catálogo global de ingredientes."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox

import ttkbootstrap as ttb

from app.config.settings import CLASSIFICACAO_INGREDIENTE_SIMPLES
from app.services.ingredient_service import IngredientService
from app.ui.styles import SPACING_MD, configure_treeview_zebra, style_button
from app.ui.window_icon import apply_window_icon
from app.utils.money import format_money_br
from app.utils.numbers import to_float
from app.utils.units import normalize_cost_unit_key


UNIT_COST_OPTIONS = ("kg", "L", "saco", "unidade", "cartela")


def cost_help_text(unit_choice: str) -> str:
    choice = (unit_choice or "").strip()
    if choice == "kg":
        return (
            "Informe o preço por 1 kg do ingrediente.\n"
            "Exemplo: se a muçarela custa R$ 50,00 por kg, informe 50,00."
        )
    if choice == "L":
        return (
            "Informe o preço por 1 litro do ingrediente.\n"
            "Exemplo: se o leite custa R$ 6,00 por litro, informe 6,00."
        )
    if choice == "saco":
        return (
            "Informe o preço total do saco e o peso total em kg.\n"
            "Exemplo: se o saco de arroz custa R$ 20,00 e possui 5 kg, "
            "o sistema salvará o custo como R$ 4,00 por kg."
        )
    if choice == "unidade":
        return (
            "Informe o preço de uma unidade.\n"
            "Exemplo: se uma unidade custa R$ 3,50, informe 3,50."
        )
    if choice == "cartela":
        return (
            "Informe o preço total da cartela e a quantidade de unidades.\n"
            "Exemplo: se a cartela com 10 ovos custa R$ 10,00, "
            "o sistema salvará o custo como R$ 1,00 por unidade."
        )
    return ""


def _positive_value(raw: object, empty_message: str, invalid_message: str) -> float:
    if not str(raw or "").strip():
        raise ValueError(empty_message)
    value = to_float(raw)
    if value <= 0:
        raise ValueError(invalid_message)
    return value


def catalog_cost_for_save(unit_choice: str, price_text: str, quantity_text: str = "") -> tuple[str, str, float, float, float]:
    choice = (unit_choice or "").strip()
    if choice == "kg":
        price = _positive_value(price_text, "Informe o preço por kg.", "O preço por kg deve ser maior que zero.")
        return "kg", "kg", price, 0.0, 0.0
    if choice == "L":
        price = _positive_value(price_text, "Informe o preço por litro.", "O preço por litro deve ser maior que zero.")
        return "L", "L", 0.0, price, 0.0
    if choice == "saco":
        price = _positive_value(price_text, "Informe o preço do saco.", "O preço do saco deve ser maior que zero.")
        weight = _positive_value(
            quantity_text,
            "Informe o peso do saco em kg.",
            "O peso do saco em kg deve ser maior que zero.",
        )
        return "kg", "kg", price / weight, 0.0, 0.0
    if choice == "unidade":
        price = _positive_value(
            price_text,
            "Informe o preço da unidade.",
            "O preço da unidade deve ser maior que zero.",
        )
        return "un", "un", 0.0, 0.0, price
    if choice == "cartela":
        price = _positive_value(
            price_text,
            "Informe o preço da cartela.",
            "O preço da cartela deve ser maior que zero.",
        )
        quantity = _positive_value(
            quantity_text,
            "Informe a quantidade de unidades na cartela.",
            "A quantidade de unidades na cartela deve ser maior que zero.",
        )
        return "un", "un", 0.0, 0.0, price / quantity
    raise ValueError("Selecione uma unidade de custo válida.")


def open_catalog_dialog(
    master: tk.Misc,
    ingredient_service: IngredientService,
    on_saved: Callable[[], None] | None = None,
    on_saved_id: Callable[[str], None] | None = None,
    close_on_saved: bool = False,
) -> ttb.Toplevel:
    win = ttb.Toplevel(
        title="Catálogo de ingredientes",
        size=(640, 540),
        transient=master.winfo_toplevel(),
    )
    apply_window_icon(win)

    outer = ttb.Frame(win, padding=SPACING_MD)
    outer.pack(fill="both", expand=True)
    ttb.Label(outer, text="Itens do cadastro mestre", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, SPACING_MD))
    top = ttb.Frame(outer)
    top.pack(fill="both", expand=True)

    cols = ("nome", "uc", "preco", "ativo")
    tree = ttb.Treeview(top, columns=cols, show="headings", height=10)
    for c, t, w in [
        ("nome", "Nome", 240),
        ("uc", "Unidade de custo", 110),
        ("preco", "Preço base", 120),
        ("ativo", "Ativo", 50),
    ]:
        tree.heading(c, text=t)
        tree.column(c, width=w)
    tree.pack(fill="both", expand=True)
    configure_treeview_zebra(tree)

    def refresh() -> None:
        from app.ui.components import clear_tree

        clear_tree(tree)
        for idx, r in enumerate(ingredient_service.list_catalog_active()):
            uc = normalize_cost_unit_key(r.get("unidade_custo"))
            if uc == "kg":
                preco = format_money_br(r.get("preco_kg")) + "/kg"
            elif uc in ("l", "ml"):
                preco = format_money_br(r.get("preco_litro")) + "/L"
            elif uc == "un":
                preco = format_money_br(r.get("preco_unidade")) + "/un"
            else:
                preco = "—"
            tag = "even" if (idx + 1) % 2 == 0 else "odd"
            tree.insert(
                "",
                "end",
                tags=(tag,),
                values=(
                    r.get("nome", ""),
                    r.get("unidade_custo", ""),
                    preco,
                    "Ativo" if r.get("active", True) else "Inativo",
                ),
            )

    refresh()

    form = ttb.Labelframe(outer, text="Novo item no cadastro mestre", padding=SPACING_MD)
    form.pack(fill="x", pady=(SPACING_MD, 0))
    v_nome = tk.StringVar()
    v_uc = tk.StringVar(value="kg")
    v_price = tk.StringVar()
    v_quantity = tk.StringVar()
    v_help = tk.StringVar(value=cost_help_text(v_uc.get()))

    r0 = ttb.Frame(form)
    r0.pack(fill="x")
    ttb.Label(r0, text="Nome*").pack(side="left")
    entry_nome = ttb.Entry(r0, textvariable=v_nome, width=36)
    entry_nome.pack(side="left", padx=6)
    r1 = ttb.Frame(form)
    r1.pack(fill="x", pady=4)
    ttb.Label(r1, text="Unidade de custo*").pack(side="left")
    combo_uc = ttb.Combobox(r1, textvariable=v_uc, values=UNIT_COST_OPTIONS, width=12, state="readonly")
    combo_uc.pack(side="left", padx=6)

    price_frame = ttb.Frame(form)
    price_frame.pack(fill="x", pady=4)
    price_label = ttb.Label(price_frame, text="Preço por kg*")
    price_label.grid(row=0, column=0, sticky="w")
    price_entry = ttb.Entry(price_frame, textvariable=v_price, width=14)
    price_entry.grid(row=0, column=1, sticky="w", padx=6)
    quantity_label = ttb.Label(price_frame, text="Peso do saco em kg*")
    quantity_entry = ttb.Entry(price_frame, textvariable=v_quantity, width=14)
    help_label = ttb.Label(form, textvariable=v_help, style="Muted.TLabel", wraplength=560, justify="left")
    help_label.pack(fill="x", pady=(4, 0))

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
            quantity_label.grid(row=0, column=2, sticky="w", padx=(12, 0))
            quantity_entry.grid(row=0, column=3, sticky="w", padx=6)
        elif choice == "unidade":
            price_label.configure(text="Preço da unidade*")
        elif choice == "cartela":
            price_label.configure(text="Preço da cartela*")
            quantity_label.configure(text="Quantidade de unidades na cartela*")
            quantity_label.grid(row=0, column=2, sticky="w", padx=(12, 0))
            quantity_entry.grid(row=0, column=3, sticky="w", padx=6)

    v_uc.trace_add("write", apply_cost_fields)
    apply_cost_fields()

    def add() -> None:
        nome = v_nome.get().strip()
        if not nome:
            messagebox.showwarning("Validação", "Informe o nome.", parent=win)
            return
        try:
            unidade_padrao, uc_save, pk, pl, pu = catalog_cost_for_save(
                v_uc.get(),
                v_price.get(),
                v_quantity.get(),
            )
            new_id = ingredient_service.master.add(
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
            messagebox.showinfo("Cadastro", "Ingrediente adicionado ao cadastro mestre.", parent=win)
            v_nome.set("")
            v_price.set("")
            v_quantity.set("")
            refresh()
            if on_saved:
                on_saved()
            if on_saved_id:
                on_saved_id(new_id)
            if close_on_saved:
                win.destroy()
        except ValueError as exc:
            messagebox.showwarning("Validação", str(exc), parent=win)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc), parent=win)

    btn_add = ttb.Button(form, text="Salvar ingrediente", command=add)
    btn_add.pack(anchor="e", pady=6)
    style_button(btn_add, "primary")
    bf = ttb.Frame(outer)
    bf.pack(fill="x", pady=SPACING_MD)
    btn_close = ttb.Button(bf, text="Fechar", command=win.destroy)
    btn_close.pack(side="right")
    style_button(btn_close, "secondary")
    win.after(50, entry_nome.focus_set)
    return win
