"""Diálogo de ingrediente (simples ou composto)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any, cast

import uuid

from app.services.recipe_calculation_service import build_products_by_id_from_rows, calc_ingredient_cost
from app.services.validation_service import find_duplicate_ingredient_warning
from app.ui.window_icon import apply_window_icon
from app.utils.numbers import to_float
from app.utils.units import (
    COST_UNIT_OPTIONS,
    INGREDIENT_TYPE_OPTIONS,
    ensure_in_options,
    get_units_for_cost_unit,
    is_valid_unit_for_cost_unit,
    normalize_cost_unit_key,
    normalize_unit,
)

if TYPE_CHECKING:
    from app.services.ingredient_service import IngredientService
    from app.services.product_service import ProductService
    from app.ui.product_editor import ProductEditorFrame


class IngredientDialog(tk.Toplevel):
    def __init__(
        self,
        master: "ProductEditorFrame",
        product_service: "ProductService",
        ingredient_service: "IngredientService",
        tipo: str = "simples",
        ingredient: dict[str, Any] | None = None,
    ):
        super().__init__(master)
        apply_window_icon(self)
        self._master = master
        self._ps = product_service
        self._ing_svc = ingredient_service
        self._tipo = tipo
        self._ingredient = ingredient
        self.title("Ingrediente")
        self.geometry("580x600")
        self.resizable(False, False)

        self.vars = {
            "nome": tk.StringVar(),
            "produto_ref_id": tk.StringVar(),
            "quantidade": tk.StringVar(),
            "unidade": tk.StringVar(value="kg"),
            "preco_unidade": tk.StringVar(value="0"),
            "preco_kg": tk.StringVar(value="0"),
            "unidade_custo": tk.StringVar(value="kg"),
        }

        prods = [p for p in self._ps.list_active_products() if str(p.get("produto_id")) != str(master.product_id)]
        self._product_name_to_id = {str(p.get("nome")): str(p.get("produto_id")) for p in prods}

        self._base_cost_var = tk.StringVar(value="")
        self._preview_var = tk.StringVar(value="—")
        self._legacy_var = tk.StringVar(value="")

        self._tipo_label_to_code = {label: code for code, label in INGREDIENT_TYPE_OPTIONS}
        self._tipo_code_to_label = {code: label for code, label in INGREDIENT_TYPE_OPTIONS}
        self._tipo_combo_labels = [label for _, label in INGREDIENT_TYPE_OPTIONS]

        self._build()
        self._load()
        self._apply_tipo_ui()
        self._apply_cost_unit_ui()
        self._register_preview_traces()
        self._update_cost_preview()

    def _current_tipo(self) -> str:
        label = self._combo_tipo.get()
        return self._tipo_label_to_code.get(label, self._tipo)

    def _cost_unit_options_for_tipo(self, tipo: str) -> list[str]:
        if tipo == "produto_composto":
            return list(COST_UNIT_OPTIONS)
        return [u for u in COST_UNIT_OPTIONS if u != "porção"]

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        self._form_frame = frame
        row = 0

        ttk.Label(frame, text="Tipo de ingrediente*").grid(row=row, column=0, sticky="w", pady=5)
        self._combo_tipo = ttk.Combobox(
            frame,
            values=self._tipo_combo_labels,
            state="readonly",
            width=36,
        )
        self._combo_tipo.grid(row=row, column=1, sticky="ew", pady=5)
        self._combo_tipo.set(self._tipo_code_to_label.get(self._tipo, INGREDIENT_TYPE_OPTIONS[0][1]))
        self._combo_tipo.bind("<<ComboboxSelected>>", self._on_tipo_selected)
        row += 1

        ttk.Label(frame, textvariable=self._legacy_var, foreground="#a60", wraplength=520).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )
        row += 1

        self._lbl_nome = ttk.Label(frame, text="Nome do ingrediente*")
        self._lbl_nome.grid(row=row, column=0, sticky="w", pady=5)
        self._entry_nome = ttk.Entry(frame, textvariable=self.vars["nome"], width=40)
        self._entry_nome.grid(row=row, column=1, sticky="ew", pady=5)
        self._row_nome = row
        row += 1

        self._btn_catalog = ttk.Button(frame, text="Usar catálogo…", command=self._pick_catalog)
        self._btn_catalog.grid(row=row, column=1, sticky="w", pady=4)
        self._row_catalog = row
        row += 1

        self._lbl_ficha = ttk.Label(frame, text="Ficha cadastrada*")
        self._lbl_ficha.grid(row=row, column=0, sticky="w", pady=5)
        self.product_combo = ttk.Combobox(
            frame, values=list(self._product_name_to_id.keys()), state="readonly", width=38
        )
        self.product_combo.grid(row=row, column=1, sticky="ew", pady=5)
        self.product_combo.bind("<<ComboboxSelected>>", self._on_product_selected)
        self._row_ficha = row
        row += 1

        self._lbl_base = ttk.Label(frame, text="Custo base da ficha (referência)")
        self._lbl_base.grid(row=row, column=0, sticky="w", pady=5)
        ttk.Label(frame, textvariable=self._base_cost_var, foreground="#064").grid(
            row=row, column=1, sticky="w", pady=5
        )
        self._row_base = row
        row += 1

        ttk.Label(frame, text="Quantidade usada*").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.vars["quantidade"], width=18).grid(
            row=row, column=1, sticky="ew", pady=5
        )
        self._row_qtd = row
        row += 1

        self._lbl_unidade = ttk.Label(frame, text="Unidade usada*")
        self._lbl_unidade.grid(row=row, column=0, sticky="w", pady=5)
        self._combo_unidade = ttk.Combobox(frame, textvariable=self.vars["unidade"], state="readonly", width=18)
        self._combo_unidade.grid(row=row, column=1, sticky="ew", pady=5)
        self._row_unidade = row
        row += 1

        self._lbl_uc = ttk.Label(frame, text="Unidade de custo*")
        self._lbl_uc.grid(row=row, column=0, sticky="w", pady=5)
        self._combo_uc = ttk.Combobox(
            frame, textvariable=self.vars["unidade_custo"], state="readonly", width=18
        )
        self._combo_uc.grid(row=row, column=1, sticky="ew", pady=5)
        self._combo_uc.bind("<<ComboboxSelected>>", self._on_cost_unit_selected)
        self._row_uc = row
        row += 1

        self._lbl_preco_un = ttk.Label(frame, text="Preço por unidade (R$)")
        self._lbl_preco_un.grid(row=row, column=0, sticky="w", pady=5)
        self._entry_preco_un = ttk.Entry(frame, textvariable=self.vars["preco_unidade"])
        self._entry_preco_un.grid(row=row, column=1, sticky="ew", pady=5)
        self._row_pu = row
        row += 1

        self._lbl_preco_kg = ttk.Label(frame, text="Preço por kg (R$)")
        self._lbl_preco_kg.grid(row=row, column=0, sticky="w", pady=5)
        self._entry_preco_kg = ttk.Entry(frame, textvariable=self.vars["preco_kg"])
        self._entry_preco_kg.grid(row=row, column=1, sticky="ew", pady=5)
        self._row_pk = row
        row += 1

        ttk.Label(frame, text="Custo estimado deste ingrediente", font=("Segoe UI", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=(8, 2)
        )
        ttk.Label(frame, textvariable=self._preview_var, foreground="#064").grid(
            row=row, column=1, sticky="w", pady=(8, 2)
        )
        self._row_preview = row
        row += 1

        ttk.Label(
            frame,
            text="Para produto composto, o custo vem da ficha referenciada conforme a unidade de custo.",
            foreground="#555",
            wraplength=520,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=8)
        self._row_hint = row
        row += 1

        actions = ttk.Frame(frame)
        actions.grid(row=row, column=0, columnspan=2, sticky="e", pady=10)
        ttk.Button(actions, text="Salvar ingrediente", command=self._save).pack(side="left", padx=5)
        ttk.Button(actions, text="Cancelar", command=self.destroy).pack(side="left", padx=5)
        frame.columnconfigure(1, weight=1)

    def _register_preview_traces(self) -> None:
        def _cb(*_a: Any) -> None:
            self.after(0, self._update_cost_preview)

        for k in ("quantidade", "unidade", "unidade_custo", "preco_unidade", "preco_kg", "nome", "produto_ref_id"):
            self.vars[k].trace_add("write", lambda *_x, _cb=_cb: _cb())

    def _products_by_id(self) -> dict[str, dict[str, Any]]:
        return cast(dict[str, dict[str, Any]], build_products_by_id_from_rows(self._ps.list_active_products()))

    def _update_cost_preview(self) -> None:
        try:
            tipo = self._current_tipo()
            cand: dict[str, Any] = {
                "tipo": tipo,
                "quantidade": to_float(self.vars["quantidade"].get()),
                "unidade": self.vars["unidade"].get().strip(),
                "unidade_custo": self.vars["unidade_custo"].get().strip(),
                "preco_kg": to_float(self.vars["preco_kg"].get()),
                "preco_unidade": to_float(self.vars["preco_unidade"].get()),
                "produto_ref_id": self.vars["produto_ref_id"].get().strip(),
            }
            cost = calc_ingredient_cost(cand, self._products_by_id())
            from app.utils.money import format_money_br

            self._preview_var.set(format_money_br(cost))
        except Exception:
            self._preview_var.set("—")

    def _on_tipo_selected(self, _event=None) -> None:
        new_tipo = self._current_tipo()
        if new_tipo == "produto_composto" and not self._product_name_to_id:
            messagebox.showwarning(
                "Atenção",
                "Não há outras fichas cadastradas para referenciar. Cadastre outra ficha antes de usar produto composto.",
            )
            self._combo_tipo.set(self._tipo_code_to_label["simples"])
            return
        self._tipo = new_tipo
        if self._tipo == "simples":
            uc = self.vars["unidade_custo"].get().strip()
            if normalize_cost_unit_key(uc) == "porção":
                self.vars["unidade_custo"].set("kg")
                self._apply_cost_unit_ui()
                messagebox.showinfo(
                    "Unidade de custo",
                    "Para ingrediente simples, a unidade de custo 'porção' não está disponível. "
                    "Ajustamos para 'kg'.",
                )
        self._apply_tipo_ui()
        self._refresh_uc_values()
        self._apply_cost_unit_ui()
        self._update_cost_preview()

    def _on_cost_unit_selected(self, _event=None) -> None:
        tipo = self._current_tipo()
        uc = self.vars["unidade_custo"].get().strip()
        if tipo == "simples" and normalize_cost_unit_key(uc) == "porção":
            messagebox.showwarning(
                "Unidade de custo",
                "Para ingrediente simples, use 'kg' ou 'un'. A unidade 'porção' é apenas para produto composto.",
            )
            self.vars["unidade_custo"].set("kg")
        self._apply_cost_unit_ui()
        self._update_cost_preview()

    def _refresh_uc_values(self) -> None:
        opts = self._cost_unit_options_for_tipo(self._current_tipo())
        cur = self.vars["unidade_custo"].get().strip()
        vals = ensure_in_options(cur, opts)
        self._combo_uc.configure(values=vals)
        if cur not in vals and cur:
            self.vars["unidade_custo"].set(vals[0] if vals else "kg")
        elif cur not in vals:
            self.vars["unidade_custo"].set(opts[0] if opts else "kg")

    def _apply_cost_unit_ui(self) -> None:
        self._refresh_uc_values()
        uc_raw = self.vars["unidade_custo"].get().strip()
        ck = normalize_cost_unit_key(uc_raw)
        tipo = self._current_tipo()

        allowed = get_units_for_cost_unit(uc_raw)
        cur_un = self.vars["unidade"].get().strip()
        vals = ensure_in_options(cur_un, allowed)
        self._combo_unidade.configure(values=vals)
        if not is_valid_unit_for_cost_unit(cur_un, uc_raw):
            self.vars["unidade"].set(vals[0] if vals else (allowed[0] if allowed else "kg"))

        if tipo == "produto_composto":
            self._entry_preco_kg.configure(state="disabled")
            self._entry_preco_un.configure(state="disabled")
            self.vars["preco_kg"].set("0")
            self.vars["preco_unidade"].set("0")
            return

        if ck == "kg":
            self._entry_preco_kg.configure(state="normal")
            self._entry_preco_un.configure(state="disabled")
            self.vars["preco_unidade"].set("0")
            self._lbl_preco_kg.configure(text="Preço por kg (R$)*")
            self._lbl_preco_un.configure(text="Preço por unidade (R$) — não aplicável")
        elif ck == "un":
            self._entry_preco_kg.configure(state="disabled")
            self._entry_preco_un.configure(state="normal")
            self.vars["preco_kg"].set("0")
            self._lbl_preco_un.configure(text="Preço por unidade (R$)*")
            self._lbl_preco_kg.configure(text="Preço por kg (R$) — não aplicável")
        elif ck == "porção":
            self._entry_preco_kg.configure(state="disabled")
            self._entry_preco_un.configure(state="disabled")
            self.vars["preco_kg"].set("0")
            self.vars["preco_unidade"].set("0")
            self._lbl_preco_un.configure(text="Preço por unidade (R$) — não aplicável (custo da ficha)")
            self._lbl_preco_kg.configure(text="Preço por kg (R$) — não aplicável (custo da ficha)")
        else:
            self._entry_preco_kg.configure(state="disabled")
            self._entry_preco_un.configure(state="disabled")
            self._lbl_preco_un.configure(text="Preço por unidade (R$)")
            self._lbl_preco_kg.configure(text="Preço por kg (R$)")

    def _apply_tipo_ui(self) -> None:
        tipo = self._current_tipo()
        if tipo == "produto_composto":
            for r in (self._row_nome, self._row_catalog):
                for w in self._form_frame.grid_slaves(row=r):
                    w.grid_remove()
            for r in (self._row_ficha, self._row_base):
                for w in self._form_frame.grid_slaves(row=r):
                    w.grid()
            self._entry_nome.configure(state="disabled")
            sel = self.product_combo.get()
            if sel and sel in self._product_name_to_id:
                self._on_product_selected()
        else:
            for r in (self._row_ficha, self._row_base):
                for w in self._form_frame.grid_slaves(row=r):
                    w.grid_remove()
            for r in (self._row_nome, self._row_catalog):
                for w in self._form_frame.grid_slaves(row=r):
                    w.grid()
            self._entry_nome.configure(state="normal")
            self.vars["produto_ref_id"].set("")
            self._base_cost_var.set("")

    def _pick_catalog(self) -> None:
        rows = self._ing_svc.list_catalog_active()
        if not rows:
            messagebox.showinfo("Catálogo", "Não há itens no catálogo. Cadastre pelo menu principal se disponível.")
            return
        win = tk.Toplevel(self)
        apply_window_icon(win)
        win.title("Catálogo de ingredientes")
        win.geometry("420x320")
        lb = tk.Listbox(win, height=12)
        lb.pack(fill="both", expand=True, padx=8, pady=8)
        for r in rows:
            lb.insert("end", str(r.get("nome", "")))

        def use() -> None:
            sel = lb.curselection()
            if not sel:
                return
            r = rows[sel[0]]
            self.vars["nome"].set(str(r.get("nome", "")))
            uc_cat = str(r.get("unidade_custo_padrao", "kg") or "kg")
            self.vars["unidade_custo"].set(uc_cat)
            self._apply_cost_unit_ui()
            un_pad = str(r.get("unidade_padrao", "") or "").strip()
            if un_pad and is_valid_unit_for_cost_unit(un_pad, self.vars["unidade_custo"].get()):
                self.vars["unidade"].set(un_pad)
            self.vars["preco_unidade"].set(str(r.get("preco_unidade_padrao", 0)))
            self.vars["preco_kg"].set(str(r.get("preco_kg_padrao", 0)))
            self._apply_cost_unit_ui()
            win.destroy()
            self._update_cost_preview()

        ttk.Button(win, text="Usar selecionado", command=use).pack(pady=6)

    def _on_product_selected(self, event=None) -> None:
        name = self.product_combo.get()
        pid = self._product_name_to_id.get(name, "")
        self.vars["nome"].set(name)
        self.vars["produto_ref_id"].set(pid)
        row = self._ps.get_product_row(pid)
        if row:
            from app.utils.money import format_money_br

            self._base_cost_var.set(
                f"kg: {format_money_br(row.get('custo_por_kg'))} | "
                f"un: {format_money_br(row.get('custo_por_unidade'))} | "
                f"porção: {format_money_br(row.get('custo_por_porcao'))}"
            )
        else:
            self._base_cost_var.set("—")
        self._update_cost_preview()

    def _legacy_warnings(self) -> None:
        msgs: list[str] = []
        uc = self.vars["unidade_custo"].get().strip()
        if uc and uc not in COST_UNIT_OPTIONS:
            msgs.append("Unidade de custo fora do padrão atual; edite para normalizar.")
        un = self.vars["unidade"].get().strip()
        allowed = get_units_for_cost_unit(uc) if uc else []
        if un and allowed and normalize_unit(un) not in {normalize_unit(x) for x in allowed}:
            msgs.append("Unidade usada fora do conjunto sugerido; confira a coerência com a unidade de custo.")
        if msgs:
            self._legacy_var.set(" ".join(msgs))
        else:
            self._legacy_var.set("")

    def _load(self) -> None:
        if not self._ingredient:
            return
        for k, var in self.vars.items():
            var.set(str(self._ingredient.get(k, "") or ""))
        t = str(self._ingredient.get("tipo", "simples") or "simples")
        self._tipo = t
        self._combo_tipo.set(self._tipo_code_to_label.get(t, INGREDIENT_TYPE_OPTIONS[0][1]))
        if t == "produto_composto":
            ref_id = str(self._ingredient.get("produto_ref_id", ""))
            for name, pid in self._product_name_to_id.items():
                if pid == ref_id:
                    self.product_combo.set(name)
                    break
            self._on_product_selected()
        uc = self.vars["unidade_custo"].get().strip()
        opts = self._cost_unit_options_for_tipo(t)
        self._combo_uc.configure(values=ensure_in_options(uc, opts))
        allowed = get_units_for_cost_unit(uc)
        un = self.vars["unidade"].get().strip()
        self._combo_unidade.configure(values=ensure_in_options(un, allowed))
        self._legacy_warnings()

    def _normalize_unidade_custo_for_save(self, uc: str) -> str:
        k = normalize_cost_unit_key(uc)
        if k == "porção":
            return "porção"
        if k == "un":
            return "un"
        if k == "kg":
            return "kg"
        return uc.strip() or "kg"

    def _save(self) -> None:
        try:
            self._tipo = self._current_tipo()
            if self._tipo == "produto_composto":
                self._on_product_selected()
                if not self.vars["produto_ref_id"].get():
                    raise ValueError("Selecione uma ficha cadastrada (produto composto).")
            else:
                if not self.vars["nome"].get().strip():
                    raise ValueError("Informe o nome do ingrediente.")

            if to_float(self.vars["quantidade"].get()) <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            uc_save = self._normalize_unidade_custo_for_save(self.vars["unidade_custo"].get())
            un_save = self.vars["unidade"].get().strip()
            if not is_valid_unit_for_cost_unit(un_save, uc_save):
                raise ValueError(
                    "A combinação de unidade de custo e unidade usada é incoerente. "
                    "Ajuste conforme as opções do formulário."
                )

            preco_kg = to_float(self.vars["preco_kg"].get())
            preco_un = to_float(self.vars["preco_unidade"].get())
            if self._tipo == "simples":
                ck = normalize_cost_unit_key(uc_save)
                if ck == "kg":
                    preco_un = 0.0
                elif ck == "un":
                    preco_kg = 0.0
                else:
                    preco_kg = 0.0
                    preco_un = 0.0
            else:
                preco_kg = 0.0
                preco_un = 0.0

            cand = {
                "ingrediente_id": self._ingredient.get("ingrediente_id") if self._ingredient else str(uuid.uuid4()),
                "produto_id": self._master.product_id,
                "nome": self.vars["nome"].get().strip(),
                "nome_normalizado": "",
                "tipo": self._tipo,
                "produto_ref_id": self.vars["produto_ref_id"].get()
                if self._tipo == "produto_composto"
                else "",
                "quantidade": to_float(self.vars["quantidade"].get()),
                "unidade": un_save,
                "preco_unidade": preco_un,
                "preco_kg": preco_kg,
                "unidade_custo": uc_save,
                "proporcao": 0,
                "custo_calculado": 0,
                "observacoes": "",
            }
            if find_duplicate_ingredient_warning(self._master._ingredients, cand):
                if not messagebox.askyesno(
                    "Possível duplicidade",
                    "Já existe ingrediente semelhante nesta ficha. Deseja adicionar mesmo assim?",
                ):
                    return

            self._master.upsert_ingredient(cand)
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
