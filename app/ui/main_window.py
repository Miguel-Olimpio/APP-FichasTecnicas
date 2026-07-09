"""Janela principal: sidebar, dashboard, fichas, ingredientes, cadastro, barra de estado."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import ttkbootstrap as ttb
from ttkbootstrap.constants import OUTLINE, PRIMARY, SECONDARY

from app.config.paths import get_database_path, get_ingredients_database_path, get_labels_dir
from app.config.settings import APP_TITLE
from app.models.ingredient import Ingredient, ingredient_to_pdf_line
from app.models.product import Product, product_to_public_pdf_dict
from app.models.pdf_payload import build_pdf_payload_from_public_dict
from app.pdf.label_pdf import build_ingredient_label_payload, generate_ingredient_label_pdf
from app.services.ingredient_master_service import IngredientMasterService
from app.services.ingredient_service import IngredientService
from app.services.pdf_service import generate_pdf
from app.services.product_service import ProductService
from app.services.validation_service import validate_product_for_save
from app.ui.components import clear_tree, create_empty_state, create_metric_card, section_header
from app.ui.ingredient_master_tab import IngredientMasterTab
from app.ui.product_editor import ProductEditorFrame
from app.ui.styles import SPACING_LG, SPACING_MD, SPACING_SM, SPACING_XL, configure_treeview_zebra, style_button
from app.utils.money import format_money_br
from app.utils.numbers import to_float
from app.utils.open_file_location import prompt_open_generated_file
from app.utils.tipo_ficha import (
    TIPO_FICHA_MATERIA_PRIMA,
    TIPO_FICHA_PRODUTO_FINAL,
    normalize_tipo_ficha,
    tipo_ficha_label,
)


class MainWindow(ttb.Frame):
    def __init__(
        self,
        master: tk.Misc,
        product_service: ProductService,
        ingredient_service: IngredientService,
        master_service: IngredientMasterService,
    ):
        super().__init__(master, padding=0)
        self._ps = product_service
        self._ing_svc = ingredient_service
        self._master_svc = master_service
        self._products: list[dict] = []
        self.search_var = tk.StringVar()
        self._filter_tipo = tk.StringVar(value="Todos")
        self._editor_title = tk.StringVar(value="")
        self._status_var = tk.StringVar(value="Pronto.")
        self._paths_var = tk.StringVar(value="")
        self._nav_keys = ("dashboard", "fichas", "ingredientes", "cadastro")
        self._nav_buttons: dict[str, ttb.Button] = {}
        self._current_section = "dashboard"
        self._dash_v_fichas = tk.StringVar(value="0")
        self._dash_v_pf = tk.StringVar(value="0")
        self._dash_v_mp = tk.StringVar(value="0")
        self._dash_v_ing = tk.StringVar(value="0")
        self._dash_v_last = tk.StringVar(value="—")
        self._dash_v_avg = tk.StringVar(value="—")

        self.pack(fill="both", expand=True)
        self._build()
        self.refresh_products()
        self._refresh_dashboard()

    def _on_product_list_refreshed(self) -> None:
        self.refresh_products()
        self._refresh_dashboard()

    def _on_product_saved(self, product_id: str) -> None:
        self.search_var.set("")
        self._filter_tipo.set("Todos")
        self._nav_to("fichas")
        self.refresh_products()
        self._refresh_dashboard()
        if product_id and self.tree.exists(product_id):
            self.tree.selection_set(product_id)
            self.tree.focus(product_id)
            self.tree.see(product_id)
        self._set_status("Ficha salva e lista atualizada.")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)

    def _build(self) -> None:
        master = self.winfo_toplevel()
        master.title(APP_TITLE)

        fp = Path(get_database_path())
        ip = Path(get_ingredients_database_path())
        self._paths_var.set(f"Fichas: {fp}  |  Ingredientes: {ip}")

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        side = ttb.Frame(self, padding=(SPACING_MD, SPACING_LG), width=218, style="Sidebar.TFrame")
        side.grid(row=0, column=0, sticky="ns")
        side.grid_propagate(False)

        ttb.Label(side, text="Fichas Técnicas", style="SidebarTitle.TLabel").pack(anchor="w", pady=(0, 2))
        ttb.Label(side, text="Alimentícias", style="SidebarSub.TLabel").pack(anchor="w", pady=(0, SPACING_LG))

        nav_labels = [
            ("dashboard", "Dashboard"),
            ("fichas", "Fichas técnicas"),
            ("ingredientes", "Ingredientes"),
        ]
        for key, label in nav_labels:
            b = ttb.Button(side, text=label, command=lambda k=key: self._nav_to(k), width=21)
            b.pack(fill="x", pady=(0, SPACING_SM))
            self._nav_buttons[key] = b

        ttb.Frame(side, style="Sidebar.TFrame").pack(fill="both", expand=True)
        credit = ttb.Frame(side, style="SidebarCredit.TFrame")
        credit.pack(fill="x", side="bottom")
        ttb.Separator(credit, orient="horizontal").pack(fill="x", pady=(0, SPACING_MD))
        ttb.Label(credit, text="Desenvolvido por", style="SidebarCredit.TLabel").pack(anchor="w")
        ttb.Label(credit, text="Miguel Olimpio", style="SidebarCreditName.TLabel").pack(anchor="w", pady=(2, 0))
        ttb.Label(
            credit,
            text="Agente Local de Inovação",
            style="SidebarCredit.TLabel",
            wraplength=180,
        ).pack(anchor="w", pady=(2, 0))

        content_host = ttb.Frame(self, padding=(SPACING_LG, SPACING_MD))
        content_host.grid(row=0, column=1, sticky="nsew")
        content_host.columnconfigure(0, weight=1)
        content_host.rowconfigure(0, weight=1)

        self._frm_dashboard = ttb.Frame(content_host)
        self._frm_fichas = ttb.Frame(content_host)
        self._frm_ingredientes = ttb.Frame(content_host)
        self._frm_cadastro = ttb.Frame(content_host)

        for f in (self._frm_dashboard, self._frm_fichas, self._frm_ingredientes, self._frm_cadastro):
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_dashboard(self._frm_dashboard)
        self._build_fichas(self._frm_fichas)

        self._master_tab = IngredientMasterTab(self._frm_ingredientes, self._master_svc)
        self._master_tab.pack(fill="both", expand=True)

        hdr = ttb.Label(self._frm_cadastro, textvariable=self._editor_title, font=("Segoe UI", 10, "bold"))
        hdr.pack(anchor="w", pady=(0, SPACING_SM))
        self._editor = ProductEditorFrame(
            self._frm_cadastro,
            self._ps,
            self._ing_svc,
            self._master_svc,
            on_list_refresh=self._on_product_list_refreshed,
            on_title=self._editor_title.set,
            on_dirty_change=self._on_editor_dirty,
            on_cancel=self._back_to_list_tab,
            on_saved=self._on_product_saved,
            on_status=self._set_status,
        )
        self._editor.pack(fill="both", expand=True)

        status_bar = ttb.Frame(self, padding=(SPACING_MD, SPACING_SM))
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttb.Label(status_bar, textvariable=self._status_var).pack(side="left")
        ttb.Label(status_bar, textvariable=self._paths_var, font=("Segoe UI", 8), foreground="#64748B").pack(
            side="right", padx=(SPACING_MD, 0)
        )

        self._nav_to("dashboard", initial=True)

    def _update_nav_styles(self) -> None:
        for key, btn in self._nav_buttons.items():
            if key == self._current_section:
                btn.configure(bootstyle=PRIMARY)
            else:
                btn.configure(bootstyle=(SECONDARY, OUTLINE))

    def _nav_to(self, key: str, initial: bool = False) -> None:
        if key not in self._nav_keys:
            return
        self._current_section = key
        self._update_nav_styles()
        if key == "dashboard":
            self._frm_dashboard.tkraise()
            if not initial:
                self._refresh_dashboard()
        elif key == "fichas":
            self._frm_fichas.tkraise()
            self.refresh_products()
            self._set_status("Lista de fichas técnicas.")
        elif key == "ingredientes":
            self._frm_ingredientes.tkraise()
            self._master_tab.refresh()
            self._set_status("Ingredientes cadastrados.")
        else:
            self._frm_cadastro.tkraise()
            self._set_status("Cadastro da ficha técnica.")

    def _build_dashboard(self, parent: ttb.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        for r in range(3):
            parent.rowconfigure(r, weight=0)

        sh = section_header(
            parent,
            "Dashboard",
            "Resumo dos dados locais. Os valores refletem apenas fichas e ingredientes ativos.",
        )
        sh.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, SPACING_LG))

        cards_spec = [
            (1, 0, "Fichas técnicas", "Total cadastradas", self._dash_v_fichas),
            (1, 1, "Produtos finais", "Tipo produto final", self._dash_v_pf),
            (1, 2, "Matérias-primas / intermediários", "Tipo matéria-prima", self._dash_v_mp),
            (2, 0, "Ingredientes cadastrados", "Cadastro mestre ativo", self._dash_v_ing),
            (2, 1, "Última ficha atualizada", "Data na planilha", self._dash_v_last),
            (2, 2, "Custo médio (fichas)", "Média do custo total quando > 0", self._dash_v_avg),
        ]
        for row, col, title, desc, var in cards_spec:
            card = create_metric_card(parent, title, desc, var)
            card.grid(row=row, column=col, sticky="nsew", padx=SPACING_SM, pady=SPACING_SM)

    def _refresh_dashboard(self) -> None:
        products = self._ps.list_active_products()
        ings = self._master_svc.list_active_dicts()
        n = len(products)
        n_pf = sum(1 for p in products if normalize_tipo_ficha(p.get("tipo_ficha")) == TIPO_FICHA_PRODUTO_FINAL)
        n_mp = sum(1 for p in products if normalize_tipo_ficha(p.get("tipo_ficha")) == TIPO_FICHA_MATERIA_PRIMA)
        dates = [str(p.get("data_atualizacao") or "") for p in products if str(p.get("data_atualizacao") or "").strip()]
        last = max(dates) if dates else "—"
        costs = [to_float(p.get("custo_total")) for p in products]
        pos = [c for c in costs if c and c > 0]
        avg_txt = format_money_br(sum(pos) / len(pos)) if pos else "—"

        self._dash_v_fichas.set(str(n))
        self._dash_v_pf.set(str(n_pf))
        self._dash_v_mp.set(str(n_mp))
        self._dash_v_ing.set(str(len(ings)))
        self._dash_v_last.set(last or "—")
        self._dash_v_avg.set(avg_txt)

    def _build_fichas(self, parent: ttb.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)

        sh = section_header(
            parent,
            "Fichas técnicas",
            "Consulte, edite e gere PDFs das fichas cadastradas.",
        )
        sh.grid(row=0, column=0, sticky="ew", pady=(0, SPACING_LG))

        toolbar = ttb.Frame(parent)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, SPACING_MD))
        toolbar.columnconfigure(3, weight=1)

        self._btn_new = ttb.Button(toolbar, text="Nova ficha técnica", command=self._new)
        self._btn_new.grid(row=0, column=0, padx=(0, SPACING_SM))
        style_button(self._btn_new, "primary")

        self._btn_refresh = ttb.Button(toolbar, text="Atualizar", command=self._on_refresh_fichas)
        self._btn_refresh.grid(row=0, column=1, padx=(0, SPACING_SM))
        style_button(self._btn_refresh, "secondary")

        ttb.Label(toolbar, text="Buscar").grid(row=0, column=2, sticky="w", padx=(SPACING_MD, SPACING_SM))
        ent = ttb.Entry(toolbar, textvariable=self.search_var, width=32)
        ent.grid(row=0, column=3, sticky="ew", padx=(0, SPACING_MD))
        ent.bind("<KeyRelease>", lambda _e: self.refresh_products())

        ttb.Label(toolbar, text="Tipo").grid(row=0, column=4, sticky="w", padx=(SPACING_MD, SPACING_SM))
        self._combo_filtro = ttb.Combobox(
            toolbar,
            textvariable=self._filter_tipo,
            values=("Todos", "Produto final", "Matéria-prima / intermediário"),
            state="readonly",
            width=26,
        )
        self._combo_filtro.grid(row=0, column=5, sticky="w")
        self._combo_filtro.bind("<<ComboboxSelected>>", lambda _e: self.refresh_products())

        self._list_inner = ttb.Frame(parent)
        self._list_inner.grid(row=3, column=0, sticky="nsew", pady=(0, SPACING_SM))
        self._list_inner.columnconfigure(0, weight=1)
        self._list_inner.rowconfigure(0, weight=1)

        cols = ("nome", "tipo", "categoria", "rendimento", "custo_total", "custo_un", "atualizacao", "status")
        self.tree = ttb.Treeview(self._list_inner, columns=cols, show="headings", selectmode="browse")
        headings = [
            ("nome", "Nome", 220),
            ("tipo", "Tipo", 140),
            ("categoria", "Categoria", 120),
            ("rendimento", "Rendimento", 120),
            ("custo_total", "Custo total", 100),
            ("custo_un", "Custo / unidade", 110),
            ("atualizacao", "Atualizado em", 130),
            ("status", "Status", 70),
        ]
        for c, t, w in headings:
            self.tree.heading(c, text=t)
            anchor = "e" if c in ("custo_total", "custo_un") else "w"
            self.tree.column(c, width=w, anchor=anchor)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _e: self._edit())
        configure_treeview_zebra(self.tree)

        self._empty_placeholder = ttb.Frame(self._list_inner)
        self._empty_placeholder.grid(row=1, column=0, sticky="ew", pady=SPACING_MD)

        bottom = ttb.Frame(parent)
        bottom.grid(row=4, column=0, sticky="ew", pady=(SPACING_LG, 0))
        self._btn_view = ttb.Button(bottom, text="Visualizar", command=self._view)
        self._btn_view.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_view, "secondary")
        self._btn_edit = ttb.Button(bottom, text="Editar", command=self._edit)
        self._btn_edit.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_edit, "secondary")
        self._btn_delete = ttb.Button(bottom, text="Excluir", command=self._delete)
        self._btn_delete.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_delete, "danger")
        self._btn_pdf = ttb.Button(bottom, text="Gerar PDF", command=self._pdf)
        self._btn_pdf.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_pdf, "success")
        self._btn_label = ttb.Button(bottom, text="Gerar etiqueta", command=self._label)
        self._btn_label.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_label, "secondary")

    def _on_refresh_fichas(self) -> None:
        self._set_status("Atualizando lista…")
        self.refresh_products()
        self._set_status("Lista atualizada.")

    def _on_editor_dirty(self, _dirty: bool) -> None:
        pass

    def _back_to_list_tab(self) -> None:
        self._nav_to("fichas")
        self.refresh_products()

    def refresh_products(self) -> None:
        self._products = self._ps.list_active_products()
        q = self.search_var.get().strip().lower()
        fv = self._filter_tipo.get()
        clear_tree(self.tree)
        shown = 0
        for p in self._products:
            nome = str(p.get("nome") or "")
            cat = str(p.get("categoria") or "")
            if q and q not in nome.lower() and q not in cat.lower():
                continue
            tf = normalize_tipo_ficha(p.get("tipo_ficha"))
            if fv == "Produto final" and tf != TIPO_FICHA_PRODUTO_FINAL:
                continue
            if fv == "Matéria-prima / intermediário" and tf != TIPO_FICHA_MATERIA_PRIMA:
                continue
            shown += 1
            tag = "even" if shown % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                iid=str(p.get("produto_id")),
                tags=(tag,),
                values=(
                    nome,
                    tipo_ficha_label(p.get("tipo_ficha")),
                    cat,
                    f"{p.get('rendimento', '')} {p.get('unidade_rendimento', '')}".strip(),
                    format_money_br(p.get("custo_total")),
                    format_money_br(p.get("custo_por_unidade")),
                    p.get("data_atualizacao", ""),
                    "Ativa",
                ),
            )

        for w in self._empty_placeholder.winfo_children():
            w.destroy()

        if not self._products:
            create_empty_state(
                self._empty_placeholder,
                "Nenhuma ficha técnica cadastrada",
                "Comece criando a sua primeira ficha técnica. Pode alterar os dados mais tarde.",
                action_text="Nova ficha técnica",
                command=self._new,
            ).pack(fill="x")
            self._empty_placeholder.grid()
        elif shown == 0:
            create_empty_state(
                self._empty_placeholder,
                "Nenhum resultado",
                "Nenhuma ficha corresponde à busca ou ao filtro. Ajuste os critérios ou clique em Atualizar.",
                action_text="Limpar filtro",
                command=self._reset_fichas_filter,
            ).pack(fill="x")
            self._empty_placeholder.grid()
        else:
            self._empty_placeholder.grid_remove()

    def _reset_fichas_filter(self) -> None:
        self.search_var.set("")
        self._filter_tipo.set("Todos")
        self.refresh_products()

    def _selected_id(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            self._set_status("Selecione uma ficha na tabela para usar esta ação.")
            return None
        return sel[0]

    def _new(self) -> None:
        self._editor.start_new()
        self._nav_to("cadastro")

    def _edit(self) -> None:
        pid = self._selected_id()
        if pid:
            self._editor.load_product(pid, read_only=False)
            self._nav_to("cadastro")

    def _view(self) -> None:
        pid = self._selected_id()
        if pid:
            self._editor.load_product(pid, read_only=True)
            self._nav_to("cadastro")

    def _delete(self) -> None:
        pid = self._selected_id()
        if not pid:
            return
        row = self._ps.get_product_row(pid)
        if not row:
            return
        nome = str(row.get("nome", "") or "(sem nome)")
        if not messagebox.askyesno(
            "Confirmar exclusão",
            "Tem certeza de que deseja excluir esta ficha técnica?\n\n"
            f"Ficha: {nome}\n"
            "A exclusão é lógica: a ficha deixa de aparecer na lista.",
        ):
            return
        try:
            self._ps.soft_delete_product(pid)
            self._set_status("Ficha excluída com sucesso.")
            messagebox.showinfo("Excluída", "A ficha técnica foi excluída da lista (exclusão lógica).")
            self.refresh_products()
            self._refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Não foi possível excluir", str(exc))

    def _pdf(self) -> None:
        pid = self._selected_id()
        if not pid:
            return
        row = self._ps.get_product_row(pid)
        if not row:
            return
        ings = self._ps.get_ingredients(pid)
        val = validate_product_for_save(row, ings, self._ps.list_active_products(), pid)
        if not val.ok:
            messagebox.showerror(
                "PDF indisponível",
                "Não foi possível gerar o PDF. Corrija os seguintes pontos e tente novamente:\n\n"
                + "\n".join(val.errors),
            )
            return
        p = Product.from_row_dict(row)
        pub = product_to_public_pdf_dict(p)
        pub["passos_preparo"] = self._ps.get_prep_steps(pid)
        lines = [ingredient_to_pdf_line(Ingredient.from_row_dict(i)) for i in ings]
        payload = build_pdf_payload_from_public_dict(pub, lines)
        path = generate_pdf(payload)
        self._set_status(f"PDF gerado: {path}")
        prompt_open_generated_file(self, path, title="PDF gerado")

    def _label(self) -> None:
        pid = self._selected_id()
        if not pid:
            return
        row = self._ps.get_product_row(pid)
        if not row:
            return
        ingredients = self._ps.get_ingredients(pid)
        prep_steps = self._ps.get_prep_steps(pid)
        payload = build_ingredient_label_payload(
            row,
            ingredients,
            prep_steps,
            nested_ingredient_resolver=self._ps.get_ingredients,
        )
        path = generate_ingredient_label_pdf(payload, get_labels_dir())
        self._set_status(f"Etiqueta gerada: {path}")
        prompt_open_generated_file(self, path, title="Etiqueta gerada")
