"""Visualização somente leitura de uma ficha."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.services.product_service import ProductService
from app.ui.window_icon import apply_window_icon
from app.utils.money import format_money_br


def show_product_readonly(master: tk.Tk, product_service: ProductService, product_id: str) -> None:
    row = product_service.get_product_row(product_id)
    if not row:
        return
    ings = product_service.get_ingredients(product_id)
    win = tk.Toplevel(master)
    apply_window_icon(win)
    win.title("Visualizar ficha técnica")
    win.geometry("720x560")
    f = ttk.Frame(win, padding=12)
    f.pack(fill="both", expand=True)
    ttk.Label(f, text=str(row.get("nome", "")), font=("Segoe UI", 14, "bold")).pack(anchor="w")
    ttk.Label(f, text=f"Categoria: {row.get('categoria', '')}").pack(anchor="w", pady=2)
    ttk.Label(
        f,
        text=f"Rendimento: {row.get('rendimento', '')} {row.get('unidade_rendimento', '')} | "
        f"Porções: {row.get('quantidade_porcoes', '')}",
    ).pack(anchor="w", pady=2)
    ttk.Label(f, text=f"Custo total: {format_money_br(row.get('custo_total'))}").pack(anchor="w", pady=2)
    ttk.Label(f, text="Ingredientes", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(12, 4))
    txt = tk.Text(f, height=16, wrap="word", state="normal")
    for ing in ings:
        txt.insert("end", f"- {ing.get('nome')} ({ing.get('tipo')}): {ing.get('quantidade')} {ing.get('unidade')}\n")
    txt.configure(state="disabled")
    txt.pack(fill="both", expand=True)
    ttk.Button(f, text="Fechar", command=win.destroy).pack(anchor="e", pady=8)
