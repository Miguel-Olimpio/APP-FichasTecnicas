"""Editor de ficha técnica embutido (ttkbootstrap + sub-abas)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable

import ttkbootstrap as ttb

import uuid

from app.config.paths import get_labels_dir
from app.models.ingredient import Ingredient, ingredient_to_pdf_line
from app.models.product import Product, product_to_public_pdf_dict
from app.models.pdf_payload import build_pdf_payload_from_public_dict
from app.pdf.label_pdf import build_ingredient_label_payload, generate_ingredient_label_pdf
from app.services.pricing_service import STATUS_ABAIXO, STATUS_PREJUIZO, STATUS_SAUDAVEL, calculate_pricing
from app.services.product_service import ProductService, ProductServiceError
from app.services.validation_service import validate_product_for_save
from app.ui.components import clear_tree
from app.ui.recipe_ingredients_panel import open_recipe_ingredient_dialog
from app.ui.styles import (
    BACKGROUND,
    BORDER_COLOR,
    DANGER_COLOR,
    MUTED_TEXT_COLOR,
    PRIMARY_COLOR,
    PRIMARY_DARK,
    SPACING_LG,
    SPACING_MD,
    SPACING_SM,
    SUCCESS_COLOR,
    SURFACE,
    SURFACE_ALT,
    TEXT_COLOR,
    WARNING_COLOR,
    configure_treeview_zebra,
    style_button,
)
from app.utils.dates import now_str
from app.utils.money import format_money_br
from app.utils.numbers import to_float
from app.utils.open_file_location import prompt_open_generated_file
from app.utils.tipo_ficha import tipo_ficha_from_label, tipo_ficha_label, tipo_ficha_options
from app.utils.units import (
    PRODUCT_CATEGORIES,
    YIELD_UNIT_OPTIONS,
    ensure_in_options,
    is_volume_unit,
    is_yield_unit_count_or_portion,
)

if TYPE_CHECKING:
    from app.services.ingredient_master_service import IngredientMasterService
    from app.services.ingredient_service import IngredientService


PRICING_BG = "#F4F8FF"
PRICING_CARD_BG = SURFACE
PRICING_CARD_ALT_BG = SURFACE_ALT
SCROLLBAR_CONTENT_GAP = SPACING_LG


class ProductEditorFrame(ttb.Frame):
    """Formulário completo da ficha com sub-abas; integra lista de ingredientes e painel embutido."""

    def __init__(
        self,
        parent: tk.Widget,
        product_service: ProductService,
        ingredient_service: "IngredientService",
        master_service: "IngredientMasterService",
        on_list_refresh: Callable[[], None],
        on_title: Callable[[str], None],
        on_dirty_change: Callable[[bool], None],
        on_cancel: Callable[[], None],
        on_saved: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ):
        super().__init__(parent)
        self._ps = product_service
        self._ing_svc = ingredient_service
        self._master_svc = master_service
        self._on_list_refresh = on_list_refresh
        self._on_title = on_title
        self._on_dirty_change = on_dirty_change
        self._on_cancel = on_cancel
        self._on_saved = on_saved or (lambda _product_id: None)
        self._on_status = on_status or (lambda _msg: None)

        self.product_id = str(uuid.uuid4())
        self._is_new = True
        self._read_only = False
        self._ingredients: list[dict] = []
        self._product_row: dict | None = None
        self._dirty = False
        self._suppress_dirty = False
        self._qty_edit_entry: ttb.Entry | None = None
        self._qty_edit_iid: str | None = None
        self._prep_step_rows: list[dict[str, tk.Widget]] = []
        self._steps_container: ttb.Frame | None = None
        self._steps_canvas: tk.Canvas | None = None
        self._steps_window_id: int | None = None
        self._pricing_canvas: tk.Canvas | None = None
        self._pricing_window_id: int | None = None
        self._btn_add_step: ttb.Button | None = None
        self._legacy_observacoes = ""
        self._pricing_product_snapshot: dict | None = None
        self._pricing_status_label: tk.Label | None = None

        self._calc_warning = tk.StringVar(value="")
        self._cv_total = tk.StringVar(value="—")
        self._cv_unit = tk.StringVar(value="—")
        self._cv_porc = tk.StringVar(value="—")
        self._cv_kg = tk.StringVar(value="—")
        self._ing_total_var = tk.StringVar(value="Custo total dos ingredientes: —")
        self._pricing_vars = {
            "embalagem_unitaria": tk.StringVar(),
            "gas_energia_outros_unitario": tk.StringVar(),
            "custo_entrega_propria": tk.StringVar(),
            "custo_entrega_aplicativo": tk.StringVar(),
            "taxa_cartao_percentual": tk.StringVar(),
            "taxa_aplicativo_percentual": tk.StringVar(),
            "margem_desejada_percentual": tk.StringVar(),
            "preco_atual_venda": tk.StringVar(),
        }
        self._pricing_ficha_vars = {
            "nome": tk.StringVar(value="—"),
            "categoria": tk.StringVar(value="—"),
            "custo_total_ingredientes": tk.StringVar(value="—"),
            "rendimento": tk.StringVar(value="—"),
            "unidade_rendimento": tk.StringVar(value="—"),
            "custo_materia_prima_unitario": tk.StringVar(value="—"),
        }
        self._pricing_result_vars = {
            "custo_total_base": tk.StringVar(value="—"),
            "custo_materia_prima_unitario": tk.StringVar(value="—"),
            "custo_complementar": tk.StringVar(value="—"),
            "preco_ideal": tk.StringVar(value="—"),
            "preco_presencial": tk.StringVar(value="—"),
            "preco_entrega": tk.StringVar(value="—"),
            "preco_app": tk.StringVar(value="—"),
            "preco_atual": tk.StringVar(value="—"),
            "lucro_estimado": tk.StringVar(value="—"),
            "margem_estimada": tk.StringVar(value="—"),
            "lucro_real": tk.StringVar(value="—"),
            "margem_real": tk.StringVar(value="—"),
            "cmv": tk.StringVar(value="—"),
            "cmv_real": tk.StringVar(value="—"),
            "markup": tk.StringVar(value="—"),
            "diferenca": tk.StringVar(value="—"),
            "diferenca_valor": tk.StringVar(value="—"),
            "diferenca_percentual": tk.StringVar(value="—"),
            "status_financeiro": tk.StringVar(value="—"),
        }
        self._pricing_alert_var = tk.StringVar(value="")
        self._build()
        for var in self._pricing_vars.values():
            var.trace_add("write", lambda *_a, _s=self: _s._on_pricing_input_changed())

    def mark_dirty(self) -> None:
        if self._suppress_dirty or self._read_only:
            return
        if not self._dirty:
            self._dirty = True
            self._on_dirty_change(True)

    def _set_clean(self) -> None:
        self._dirty = False
        self._on_dirty_change(False)

    def _build(self) -> None:
        self._top_bar = ttb.Frame(self)
        self._top_bar.pack(fill="x", padx=SPACING_MD, pady=(SPACING_MD, SPACING_SM))
        self._btn_save = ttb.Button(self._top_bar, text="Salvar ficha", command=self._save)
        self._btn_save.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_save, "primary")
        self._btn_pdf = ttb.Button(self._top_bar, text="Gerar PDF", command=self._pdf)
        self._btn_pdf.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_pdf, "success")
        self._btn_label = ttb.Button(
            self._top_bar,
            text="Gerar etiqueta de ingredientes",
            command=self._label_pdf,
        )
        self._btn_label.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_label, "secondary")
        self._btn_cancel = ttb.Button(self._top_bar, text="Cancelar", command=self._cancel)
        self._btn_cancel.pack(side="right")
        style_button(self._btn_cancel, "secondary")

        self._nb = ttb.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=SPACING_MD, pady=SPACING_SM)

        self._tab_dados = tab_dados = ttb.Frame(self._nb, padding=SPACING_MD)
        self._tab_ings = tab_ings = ttb.Frame(self._nb, padding=SPACING_MD)
        self._tab_prep = tab_prep = ttb.Frame(self._nb, padding=SPACING_MD)
        self._tab_cost = tab_cost = ttb.Frame(self._nb, padding=SPACING_MD)
        self._tab_pricing = tab_pricing = ttb.Frame(self._nb, padding=SPACING_MD)
        self._nb.add(tab_dados, text="Dados gerais")
        self._nb.add(tab_ings, text="Ingredientes")
        self._nb.add(tab_prep, text="Preparo e observações")
        self._nb.add(tab_cost, text="Custos")
        self._nb.add(tab_pricing, text="Precificação/Lucro")

        self.vars = {
            "nome": tk.StringVar(),
            "categoria": tk.StringVar(value="Outros"),
            "rendimento": tk.StringVar(),
            "unidade_rendimento": tk.StringVar(value="un"),
            "quantidade_porcoes": tk.StringVar(value="1"),
        }
        for k in self.vars:
            self.vars[k].trace_add("write", lambda *_a, _s=self: _s._on_product_input_changed())

        data = ttb.Labelframe(tab_dados, text="Dados gerais da ficha", padding=SPACING_MD)
        data.pack(fill="both", expand=True)
        ttb.Label(
            data,
            text="Campos marcados com * são obrigatórios.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, SPACING_MD))

        rows = [
            ("Nome do produto*", "nome", 1, 0),
            ("Categoria*", "categoria", 1, 2),
            ("Tipo da ficha técnica*", "tipo_ficha_ui", 2, 0),
            ("Quantidade de rendimento*", "rendimento", 4, 0),
            ("Unidade de rendimento*", "unidade_rendimento", 4, 2),
            ("Quantidade de porções*", "quantidade_porcoes", 5, 0),
        ]
        self._combo_categoria = None
        self._combo_unidade_rendimento = None
        self._combo_tipo_ficha: ttb.Combobox | None = None
        ttb.Label(
            data,
            text="Rendimento da receita",
            font=("Segoe UI", 10, "bold"),
            foreground=PRIMARY_COLOR,
        ).grid(row=3, column=0, columnspan=4, sticky="w", padx=5, pady=(SPACING_MD, SPACING_SM))
        for text, key, row, col in rows:
            ttb.Label(data, text=text).grid(row=row, column=col, sticky="w", padx=5, pady=4)
            if key == "categoria":
                cat_vals = ensure_in_options(self.vars["categoria"].get(), PRODUCT_CATEGORIES)
                self._combo_categoria = ttb.Combobox(
                    data, textvariable=self.vars["categoria"], values=cat_vals, state="readonly", width=30
                )
                self._combo_categoria.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=4)
            elif key == "tipo_ficha_ui":
                self._combo_tipo_ficha = ttb.Combobox(
                    data, values=tipo_ficha_options(), state="readonly", width=42
                )
                self._combo_tipo_ficha.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=4)
                self._combo_tipo_ficha.set(tipo_ficha_options()[0])
                self._combo_tipo_ficha.bind("<<ComboboxSelected>>", lambda _e: self.mark_dirty())
            elif key == "unidade_rendimento":
                self._combo_unidade_rendimento = ttb.Combobox(
                    data,
                    textvariable=self.vars["unidade_rendimento"],
                    values=YIELD_UNIT_OPTIONS,
                    state="readonly",
                    width=30,
                )
                self._combo_unidade_rendimento.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=4)
            else:
                ttb.Entry(data, textvariable=self.vars[key], width=32).grid(
                    row=row, column=col + 1, sticky="ew", padx=5, pady=4
                )
        ttb.Label(
            data,
            text="Informe quanto essa ficha técnica rende ao final do preparo. Exemplos: 1 kg de massa, 2 L de molho ou 30 unidades.",
            style="Muted.TLabel",
            wraplength=680,
        ).grid(row=6, column=0, columnspan=4, sticky="w", padx=5, pady=(SPACING_SM, SPACING_MD))
        ttb.Label(
            data,
            text="Somente fichas marcadas como matéria-prima / produto intermediário poderão ser usadas como ingrediente de outras fichas.",
            style="Muted.TLabel",
            wraplength=680,
        ).grid(row=7, column=0, columnspan=4, sticky="w", padx=5, pady=SPACING_LG)
        data.columnconfigure(1, weight=1)
        data.columnconfigure(3, weight=1)

        tab_ings.columnconfigure(0, weight=1)
        tab_ings.rowconfigure(3, weight=1)

        ttb.Label(tab_ings, text="Ingredientes", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, SPACING_SM)
        )

        btns = ttb.Frame(tab_ings)
        btns.grid(row=1, column=0, sticky="ew", pady=(0, SPACING_SM))
        self._btn_add_ing = ttb.Button(
            btns,
            text="Adicionar novo ingrediente à ficha técnica",
            command=self._add_ing,
        )
        self._btn_add_ing.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_add_ing, "primary")
        self._btn_edit_ing = ttb.Button(btns, text="Editar quantidade", command=self._begin_quantity_edit)
        self._btn_edit_ing.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_edit_ing, "secondary")
        self._btn_rem = ttb.Button(btns, text="Remover ingrediente selecionado", command=self._remove_ing)
        self._btn_rem.pack(side="left", padx=(0, SPACING_SM))
        style_button(self._btn_rem, "danger")

        self._empty_ing_label = ttb.Label(
            tab_ings,
            text="Nenhum ingrediente adicionado à ficha técnica.",
            style="Muted.TLabel",
        )
        self._empty_ing_label.grid(row=2, column=0, sticky="w", pady=(0, SPACING_SM))

        cols = ("nome", "tipo", "q", "un", "custo")
        self.ing_tree = ttb.Treeview(tab_ings, columns=cols, show="headings", height=12)
        for c, t, w, anchor in [
            ("nome", "Nome do ingrediente", 280, "w"),
            ("tipo", "Tipo", 140, "w"),
            ("q", "Quantidade usada", 120, "e"),
            ("un", "Unidade", 90, "center"),
            ("custo", "Custo calculado", 130, "e"),
        ]:
            self.ing_tree.heading(c, text=t)
            self.ing_tree.column(c, width=w, anchor=anchor)
        self.ing_tree.grid(row=3, column=0, sticky="nsew")
        self.ing_tree.bind("<Double-1>", self._begin_quantity_edit)
        self.ing_tree.bind("<<TreeviewSelect>>", self._on_ing_tree_select)
        configure_treeview_zebra(self.ing_tree)

        footer = ttb.Frame(tab_ings)
        footer.grid(row=4, column=0, sticky="ew", pady=(SPACING_MD, 0))
        ttb.Label(footer, textvariable=self._ing_total_var, font=("Segoe UI", 10, "bold"), foreground=PRIMARY_COLOR).pack(
            side="right"
        )

        tab_prep.columnconfigure(0, weight=1)
        tab_prep.rowconfigure(0, weight=1)

        lf_steps = ttb.Labelframe(tab_prep, text="Passo a passo do preparo", padding=SPACING_MD)
        lf_steps.grid(row=0, column=0, sticky="nsew")
        lf_steps.columnconfigure(0, weight=1)
        lf_steps.rowconfigure(1, weight=1)

        steps_header = ttb.Frame(lf_steps)
        steps_header.grid(row=0, column=0, sticky="ew", pady=(0, SPACING_SM))
        self._btn_add_step = ttb.Button(steps_header, text="Adicionar passo", command=self._add_prep_step)
        self._btn_add_step.pack(side="left")
        style_button(self._btn_add_step, "primary")

        steps_area = ttb.Frame(lf_steps)
        steps_area.grid(row=1, column=0, sticky="nsew")
        steps_area.columnconfigure(0, weight=1)
        steps_area.rowconfigure(0, weight=1)

        self._steps_canvas = tk.Canvas(steps_area, highlightthickness=0, borderwidth=0, background=BACKGROUND)
        self._steps_canvas.grid(row=0, column=0, sticky="nsew")
        steps_scroll = ttb.Scrollbar(steps_area, orient="vertical", command=self._steps_canvas.yview)
        steps_scroll.grid(row=0, column=1, sticky="ns", padx=(SPACING_SM, 0))
        self._steps_canvas.configure(yscrollcommand=steps_scroll.set)

        self._steps_container = ttb.Frame(self._steps_canvas)
        self._steps_window_id = self._steps_canvas.create_window((0, 0), window=self._steps_container, anchor="nw")
        self._steps_container.columnconfigure(0, weight=1)
        self._steps_container.bind(
            "<Configure>",
            lambda _e: self._steps_canvas.configure(scrollregion=self._steps_canvas.bbox("all"))
            if self._steps_canvas is not None
            else None,
        )
        self._steps_canvas.bind("<Configure>", self._on_steps_canvas_configure)
        self._bind_mousewheel_recursive(self._steps_canvas, self._on_steps_mousewheel)
        self._bind_mousewheel_recursive(self._steps_container, self._on_steps_mousewheel)

        warn = ttb.Label(tab_cost, textvariable=self._calc_warning, foreground=WARNING_COLOR, wraplength=720)
        warn.pack(anchor="w", pady=(0, SPACING_MD))

        cards = ttb.Frame(tab_cost)
        cards.pack(fill="both", expand=True)
        for c in range(2):
            cards.columnconfigure(c, weight=1)
        cards.rowconfigure(0, weight=1)
        cards.rowconfigure(1, weight=1)

        self._cost_card(
            cards,
            "Custo total",
            self._cv_total,
            "Soma dos custos calculados dos ingredientes da ficha.",
            0,
            0,
        )
        self._cost_card(
            cards,
            "Custo por unidade",
            self._cv_unit,
            "Custo total dividido pelo rendimento informado.",
            0,
            1,
        )
        self._cost_card(
            cards,
            "Custo por porção",
            self._cv_porc,
            "Baseado na quantidade de porções informada nos dados gerais.",
            1,
            0,
        )
        self._cost_card(
            cards,
            "Custo por kg",
            self._cv_kg,
            "Quando o rendimento estiver em massa (ex.: kg ou g).",
            1,
            1,
        )

        self._btn_recalc = ttb.Button(tab_cost, text="Recalcular custos", command=self._refresh_tree)
        self._btn_recalc.pack(anchor="w", pady=SPACING_LG)
        style_button(self._btn_recalc, "secondary")

        self._build_pricing_tab(tab_pricing)

    def _build_pricing_tab(self, parent: ttb.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        self._pricing_canvas = tk.Canvas(parent, highlightthickness=0, borderwidth=0, background=PRICING_BG)
        self._pricing_canvas.grid(row=0, column=0, sticky="nsew")
        pricing_scroll = ttb.Scrollbar(parent, orient="vertical", command=self._pricing_canvas.yview)
        pricing_scroll.grid(row=0, column=1, sticky="ns", padx=(SPACING_SM, 0))
        self._pricing_canvas.configure(yscrollcommand=pricing_scroll.set)

        content = ttb.Frame(self._pricing_canvas)
        self._pricing_window_id = self._pricing_canvas.create_window((0, 0), window=content, anchor="nw")
        content.columnconfigure(0, weight=1)
        content.bind(
            "<Configure>",
            lambda _e: self._pricing_canvas.configure(scrollregion=self._pricing_canvas.bbox("all"))
            if self._pricing_canvas is not None
            else None,
        )
        self._pricing_canvas.bind("<Configure>", self._on_pricing_canvas_configure)
        self._bind_mousewheel_recursive(self._pricing_canvas, self._on_pricing_mousewheel)

        ficha = ttb.Labelframe(content, text="Dados da ficha técnica", padding=SPACING_MD)
        ficha.grid(row=0, column=0, sticky="ew", pady=(0, SPACING_MD))
        ficha.columnconfigure(1, weight=1)
        for row, (label, key) in enumerate(
            [
                ("Nome do produto", "nome"),
                ("Categoria", "categoria"),
                ("Custo total dos ingredientes", "custo_total_ingredientes"),
                ("Rendimento", "rendimento"),
                ("Unidade de rendimento", "unidade_rendimento"),
                ("Custo por unidade de rendimento", "custo_materia_prima_unitario"),
            ]
        ):
            ttb.Label(ficha, text=label).grid(row=row, column=0, sticky="w", pady=3)
            ttb.Label(ficha, textvariable=self._pricing_ficha_vars[key], font=("Segoe UI", 10, "bold")).grid(
                row=row, column=1, sticky="w", padx=(SPACING_MD, 0), pady=3
            )

        suggested = ttb.Labelframe(content, text="Precificação sugerida", padding=SPACING_MD)
        suggested.grid(row=1, column=0, sticky="ew", pady=(0, SPACING_MD))
        suggested.columnconfigure(0, weight=1)
        suggested.columnconfigure(1, weight=1)

        manual = ttb.Frame(suggested)
        manual.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING_MD))
        manual.columnconfigure(1, weight=1)
        suggested_fields = [
            ("Custo de embalagem por unidade", "embalagem_unitaria", ""),
            ("Custo de gás/energia/outros por unidade", "gas_energia_outros_unitario", ""),
            ("Taxa de cartão", "taxa_cartao_percentual", "%"),
            ("Taxa de aplicativo (%)", "taxa_aplicativo_percentual", "%"),
            ("Margem desejada sobre o custo", "margem_desejada_percentual", "%"),
        ]
        for row, (label, key, suffix) in enumerate(suggested_fields):
            ttb.Label(manual, text=label).grid(row=row, column=0, sticky="w", pady=3)
            entry = ttb.Entry(manual, textvariable=self._pricing_vars[key], width=18)
            entry.grid(row=row, column=1, sticky="ew", padx=(SPACING_MD, SPACING_SM), pady=3)
            if suffix:
                ttb.Label(manual, text=suffix).grid(row=row, column=2, sticky="w", pady=3)

        suggested_results = ttb.Frame(suggested)
        suggested_results.grid(row=0, column=1, sticky="nsew")
        for col in range(2):
            suggested_results.columnconfigure(col, weight=1)
        suggested_cards = [
            ("Custo da matéria-prima por unidade", "custo_materia_prima_unitario"),
            ("Custo complementar", "custo_complementar"),
            ("Custo total base", "custo_total_base"),
            ("Preço sugerido de venda", "preco_ideal"),
            ("Lucro estimado por unidade", "lucro_estimado"),
            ("Margem estimada", "margem_estimada"),
            ("CMV", "cmv"),
            ("Markup", "markup"),
        ]
        for idx, (title, key) in enumerate(suggested_cards):
            self._pricing_card(suggested_results, title, self._pricing_result_vars[key], idx // 2, idx % 2)

        scenarios = ttb.Labelframe(content, text="Cenários de preço de venda", padding=SPACING_MD)
        scenarios.grid(row=2, column=0, sticky="ew", pady=(0, SPACING_MD))
        scenarios.columnconfigure(0, weight=1)
        ttb.Label(
            scenarios,
            text="Os valores abaixo representam sugestões de preço para diferentes cenários de venda.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, SPACING_SM))

        delivery_field = ttb.Frame(scenarios)
        delivery_field.grid(row=1, column=0, sticky="ew", pady=(0, SPACING_SM))
        delivery_field.columnconfigure(1, weight=1)
        ttb.Label(delivery_field, text="Custo de entrega própria por unidade").grid(row=0, column=0, sticky="w", pady=3)
        ttb.Entry(
            delivery_field,
            textvariable=self._pricing_vars["custo_entrega_propria"],
            width=18,
        ).grid(row=0, column=1, sticky="w", padx=(SPACING_MD, 0), pady=3)
        ttb.Label(delivery_field, text="Custo de entrega pelo aplicativo por unidade").grid(
            row=1,
            column=0,
            sticky="w",
            pady=3,
        )
        ttb.Entry(
            delivery_field,
            textvariable=self._pricing_vars["custo_entrega_aplicativo"],
            width=18,
        ).grid(row=1, column=1, sticky="w", padx=(SPACING_MD, 0), pady=3)

        scenario_cards = ttb.Frame(scenarios)
        scenario_cards.grid(row=2, column=0, sticky="ew")
        for col in range(3):
            scenario_cards.columnconfigure(col, weight=1)
        self._pricing_scenario_card(
            scenario_cards,
            "Venda presencial",
            self._pricing_result_vars["preco_presencial"],
            "Sem taxas. Usa custo total base e margem desejada.",
            0,
        )
        self._pricing_scenario_card(
            scenario_cards,
            "Venda com entrega própria",
            self._pricing_result_vars["preco_entrega"],
            "Considera custo total base, entrega própria e margem desejada.",
            1,
        )
        self._pricing_scenario_card(
            scenario_cards,
            "Venda via aplicativo",
            self._pricing_result_vars["preco_app"],
            "Considera custo total base, entrega pelo aplicativo, margem e taxa do app.",
            2,
        )

        comparison = ttb.Labelframe(content, text="Comparação com preço atual", padding=SPACING_MD)
        comparison.grid(row=3, column=0, sticky="ew")
        comparison.columnconfigure(0, weight=1)
        comparison.columnconfigure(1, weight=2)
        ttb.Label(
            comparison,
            text="Preço atual é apenas para análise comparativa e não altera o preço sugerido.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, SPACING_SM))

        current_fields = ttb.Frame(comparison)
        current_fields.grid(row=1, column=0, sticky="nsew", padx=(0, SPACING_MD))
        current_fields.columnconfigure(1, weight=1)
        for row, (label, key) in enumerate(
            [
                ("Preço atual de venda", "preco_atual_venda"),
            ]
        ):
            ttb.Label(current_fields, text=label).grid(row=row, column=0, sticky="w", pady=3)
            ttb.Entry(current_fields, textvariable=self._pricing_vars[key], width=18).grid(
                row=row,
                column=1,
                sticky="ew",
                padx=(SPACING_MD, 0),
                pady=3,
            )

        comparison_results = ttb.Frame(comparison)
        comparison_results.grid(row=1, column=1, sticky="nsew")
        for col in range(3):
            comparison_results.columnconfigure(col, weight=1)
        comparison_cards = [
            ("Preço atual", "preco_atual"),
            ("Lucro real", "lucro_real"),
            ("Margem real", "margem_real"),
            ("CMV real", "cmv_real"),
            ("Diferença em valor", "diferenca_valor"),
            ("Diferença percentual", "diferenca_percentual"),
            ("Status financeiro", "status_financeiro"),
        ]
        for idx, (title, key) in enumerate(comparison_cards):
            label = self._pricing_card(comparison_results, title, self._pricing_result_vars[key], idx // 3, idx % 3)
            if key == "status_financeiro":
                self._pricing_status_label = label
        ttb.Label(content, textvariable=self._pricing_alert_var, foreground=WARNING_COLOR, wraplength=920).grid(
            row=4,
            column=0,
            sticky="w",
            pady=(SPACING_MD, 0),
        )
        self._bind_mousewheel_recursive(content, self._on_pricing_mousewheel)

    def _pricing_card(self, parent: tk.Widget, title: str, value_var: tk.StringVar, row: int, col: int) -> tk.Label:
        card = tk.Frame(
            parent,
            background=PRICING_CARD_BG,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            bd=0,
        )
        card.grid(row=row, column=col, sticky="nsew", padx=SPACING_SM, pady=SPACING_SM)
        card.columnconfigure(0, weight=1)
        tk.Label(
            card,
            text=title,
            background=PRICING_CARD_BG,
            foreground=MUTED_TEXT_COLOR,
            font=("Segoe UI", 8),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=SPACING_MD, pady=(SPACING_SM, 0))
        value = tk.Label(
            card,
            textvariable=value_var,
            background=PRICING_CARD_BG,
            foreground=PRIMARY_COLOR,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        value.grid(row=1, column=0, sticky="ew", padx=SPACING_MD, pady=(SPACING_SM, SPACING_MD))
        return value

    def _pricing_scenario_card(
        self,
        parent: tk.Widget,
        title: str,
        value_var: tk.StringVar,
        description: str,
        col: int,
    ) -> None:
        card = tk.Frame(
            parent,
            background=PRICING_CARD_ALT_BG,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            bd=0,
        )
        card.grid(row=0, column=col, sticky="nsew", padx=SPACING_SM, pady=SPACING_SM)
        card.columnconfigure(0, weight=1)
        tk.Label(
            card,
            text=title,
            background=PRICING_CARD_ALT_BG,
            foreground=PRIMARY_DARK,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=SPACING_MD, pady=(SPACING_MD, SPACING_SM))
        tk.Label(
            card,
            textvariable=value_var,
            background=PRICING_CARD_ALT_BG,
            foreground=PRIMARY_COLOR,
            font=("Segoe UI", 15, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=SPACING_MD)
        tk.Label(
            card,
            text=description,
            background=PRICING_CARD_ALT_BG,
            foreground=TEXT_COLOR,
            font=("Segoe UI", 8),
            wraplength=230,
            justify="left",
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=SPACING_MD, pady=(SPACING_SM, SPACING_MD))

    def _cost_card(self, parent: tk.Widget, title: str, value_var: tk.StringVar, hint: str, row: int, col: int) -> None:
        card = ttb.Frame(parent, style="Card.TFrame", padding=SPACING_MD)
        card.grid(row=row, column=col, sticky="nsew", padx=SPACING_SM, pady=SPACING_SM)
        ttb.Label(card, text=title, style="Muted.TLabel").pack(anchor="w")
        ttb.Label(card, textvariable=value_var, font=("Segoe UI", 12, "bold"), foreground=PRIMARY_COLOR).pack(
            anchor="w", pady=(SPACING_SM, 0)
        )
        ttb.Label(card, text=hint, style="Muted.TLabel", wraplength=320).pack(anchor="w", pady=(SPACING_SM, 0))

    def _on_ing_tree_select(self, _event: object | None = None) -> None:
        self._sync_ing_buttons()

    def _sync_ing_buttons(self) -> None:
        selected = bool(self.ing_tree.selection())
        state = "disabled" if self._read_only or not selected else "normal"
        self._btn_edit_ing.configure(state=state)
        self._btn_rem.configure(state=state)

    def _on_product_input_changed(self) -> None:
        self.mark_dirty()
        self.after(0, self._refresh_pricing)

    def _on_pricing_input_changed(self) -> None:
        self.mark_dirty()
        self.after(0, self._refresh_pricing)

    def _on_pricing_canvas_configure(self, event: tk.Event) -> None:
        if self._pricing_canvas is not None and self._pricing_window_id is not None:
            self._pricing_canvas.itemconfigure(
                self._pricing_window_id,
                width=max(event.width - SCROLLBAR_CONTENT_GAP, 1),
            )

    def _on_pricing_mousewheel(self, event: tk.Event) -> str:
        return self._scroll_canvas_with_mousewheel(self._pricing_canvas, event)

    def _bind_mousewheel_recursive(self, widget: tk.Widget, handler: Callable[[tk.Event], str]) -> None:
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(sequence, handler)
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child, handler)

    def _scroll_canvas_with_mousewheel(self, canvas: tk.Canvas | None, event: tk.Event) -> str:
        if canvas is None:
            return "break"
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            raw_delta = getattr(event, "delta", 0)
            delta = int(-1 * (raw_delta / 120)) if raw_delta else 0
            if delta == 0 and raw_delta:
                delta = -1 if raw_delta > 0 else 1
        if delta:
            canvas.yview_scroll(delta, "units")
        return "break"

    def _collect_pricing_manual(self) -> dict:
        return {key: var.get().strip() for key, var in self._pricing_vars.items()}

    def _clear_pricing(self) -> None:
        for var in self._pricing_vars.values():
            var.set("")

    def _load_pricing(self, row: dict | None) -> None:
        data = row or {}
        for key, var in self._pricing_vars.items():
            value = data.get(key, "")
            if key == "custo_entrega_propria" and value in (None, ""):
                value = data.get("custo_entrega_unitario", "")
            var.set("" if value is None else str(value))

    def _refresh_pricing(self, product: dict | None = None) -> None:
        if product is None:
            if self._pricing_product_snapshot is not None:
                product = dict(self._pricing_product_snapshot)
            else:
                try:
                    product, _ings, _warns = self._ps.recalc_draft(self._collect_product(), list(self._ingredients))
                except Exception:
                    product = self._collect_product()
        self._pricing_product_snapshot = dict(product)
        manual = self._collect_pricing_manual()
        calc = calculate_pricing(product, manual)

        self._pricing_ficha_vars["nome"].set(str(product.get("nome", "") or "—"))
        self._pricing_ficha_vars["categoria"].set(str(product.get("categoria", "") or "—"))
        self._pricing_ficha_vars["custo_total_ingredientes"].set(self._format_money_or_dash(product.get("custo_total")))
        self._pricing_ficha_vars["rendimento"].set(str(product.get("rendimento", "") or "—"))
        self._pricing_ficha_vars["unidade_rendimento"].set(str(product.get("unidade_rendimento", "") or "—"))
        self._pricing_ficha_vars["custo_materia_prima_unitario"].set(
            self._format_money_or_dash(calc.get("custo_materia_prima_unitario"))
        )

        self._pricing_result_vars["custo_materia_prima_unitario"].set(
            self._format_money_or_dash(calc.get("custo_materia_prima_unitario"))
        )
        self._pricing_result_vars["custo_complementar"].set(self._format_money_or_dash(calc.get("custo_complementar")))
        self._pricing_result_vars["custo_total_base"].set(self._format_money_or_dash(calc.get("custo_total_base")))
        self._pricing_result_vars["preco_ideal"].set(self._format_money_or_dash(calc.get("preco_ideal")))
        self._pricing_result_vars["preco_presencial"].set(self._format_money_or_dash(calc.get("preco_presencial")))
        self._pricing_result_vars["preco_entrega"].set(self._format_money_or_dash(calc.get("preco_entrega")))
        self._pricing_result_vars["preco_app"].set(self._format_money_or_dash(calc.get("preco_app")))
        self._pricing_result_vars["preco_atual"].set(self._format_money_or_dash(calc.get("preco_atual_venda")))
        self._pricing_result_vars["lucro_estimado"].set(self._format_money_or_dash(calc.get("lucro_estimado")))
        self._pricing_result_vars["margem_estimada"].set(self._format_percent_or_dash(calc.get("margem_estimada")))
        self._pricing_result_vars["lucro_real"].set(self._format_money_or_dash(calc.get("lucro_real")))
        self._pricing_result_vars["margem_real"].set(self._format_percent_or_dash(calc.get("margem_real")))
        self._pricing_result_vars["cmv"].set(self._format_percent_or_dash(calc.get("cmv")))
        self._pricing_result_vars["cmv_real"].set(self._format_percent_or_dash(calc.get("cmv_real")))
        self._pricing_result_vars["markup"].set(self._format_markup(calc.get("markup")))
        self._pricing_result_vars["diferenca"].set(self._format_difference(calc))
        self._pricing_result_vars["diferenca_valor"].set(self._format_money_or_dash(calc.get("diferenca_valor")))
        self._pricing_result_vars["diferenca_percentual"].set(
            self._format_percent_or_dash(calc.get("diferenca_percentual"))
        )
        status = str(calc.get("status_financeiro") or "")
        self._pricing_result_vars["status_financeiro"].set(status or "Preço atual não informado")
        self._sync_pricing_status_color(status)
        self._pricing_alert_var.set(" | ".join(calc.get("alerts", [])))

    def _pricing_row_for_save(self, product: dict) -> dict:
        manual = self._collect_pricing_manual()
        calc = calculate_pricing(product, manual)
        return {
            "produto_id": self.product_id,
            "embalagem_unitaria": to_float(manual.get("embalagem_unitaria")),
            "gas_energia_outros_unitario": to_float(manual.get("gas_energia_outros_unitario")),
            "custo_entrega_unitario": to_float(manual.get("custo_entrega_propria")),
            "custo_entrega_propria": to_float(manual.get("custo_entrega_propria")),
            "custo_entrega_aplicativo": to_float(manual.get("custo_entrega_aplicativo")),
            "taxa_cartao_percentual": to_float(manual.get("taxa_cartao_percentual")),
            "taxa_aplicativo_percentual": to_float(manual.get("taxa_aplicativo_percentual")),
            "margem_desejada_percentual": to_float(manual.get("margem_desejada_percentual")),
            "preco_atual_venda": self._optional_float(manual.get("preco_atual_venda")),
            "canal_venda": "",
            "preco_ideal": self._round_or_blank(calc.get("preco_ideal")),
            "lucro_estimado": self._round_or_blank(calc.get("lucro_estimado")),
            "margem_estimada": self._round_or_blank(calc.get("margem_estimada"), 6),
            "lucro_real": self._round_or_blank(calc.get("lucro_real")),
            "margem_real": self._round_or_blank(calc.get("margem_real"), 6),
            "cmv": self._round_or_blank(calc.get("cmv"), 6),
            "markup": self._round_or_blank(calc.get("markup"), 6),
            "status_financeiro": str(calc.get("status_financeiro") or ""),
            "data_atualizacao": now_str(),
        }

    def _sync_pricing_status_color(self, status: str) -> None:
        if not self._pricing_status_label:
            return
        color = PRIMARY_COLOR
        if status == STATUS_SAUDAVEL:
            color = SUCCESS_COLOR
        elif status == STATUS_ABAIXO:
            color = WARNING_COLOR
        elif status == STATUS_PREJUIZO:
            color = DANGER_COLOR
        self._pricing_status_label.configure(foreground=color)

    def _format_money_or_dash(self, value: object) -> str:
        if value in (None, ""):
            return "—"
        return format_money_br(value)

    def _format_percent_or_dash(self, value: object) -> str:
        if value in (None, ""):
            return "—"
        pct = to_float(value) * 100
        return f"{pct:.1f}%".replace(".", ",")

    def _format_markup(self, value: object) -> str:
        if value in (None, ""):
            return "—"
        return f"{to_float(value):.2f}x".replace(".", ",")

    def _format_difference(self, calc: dict) -> str:
        value = calc.get("diferenca_valor")
        pct = calc.get("diferenca_percentual")
        if value in (None, "") or pct in (None, ""):
            return "—"
        return f"{format_money_br(value)} ({self._format_percent_or_dash(pct)})"

    def _round_or_blank(self, value: object, digits: int = 4) -> float | str:
        if value in (None, ""):
            return ""
        return round(to_float(value), digits)

    def _optional_float(self, value: object) -> float | str:
        if not str(value or "").strip():
            return ""
        return to_float(value)

    def _on_text_modified(self, event: tk.Event) -> None:
        w = event.widget
        if isinstance(w, tk.Text):
            w.edit_modified(False)
        self.mark_dirty()

    def _on_steps_canvas_configure(self, event: tk.Event) -> None:
        if self._steps_canvas is not None and self._steps_window_id is not None:
            self._steps_canvas.itemconfigure(
                self._steps_window_id,
                width=max(event.width - SCROLLBAR_CONTENT_GAP, 1),
            )

    def _on_steps_mousewheel(self, event: tk.Event) -> str:
        return self._scroll_canvas_with_mousewheel(self._steps_canvas, event)

    def _current_prep_steps(self) -> list[str]:
        steps: list[str] = []
        for row in self._prep_step_rows:
            widget = row.get("text")
            if isinstance(widget, tk.Text):
                steps.append(widget.get("1.0", "end").strip())
        return steps

    def _render_prep_steps(self, steps: list[str] | None = None) -> None:
        if self._steps_container is None:
            return
        values = list(self._current_prep_steps() if steps is None else steps)
        for child in self._steps_container.winfo_children():
            child.destroy()
        self._prep_step_rows = []
        for idx, text_value in enumerate(values):
            row = ttb.Frame(self._steps_container)
            row.grid(row=idx, column=0, sticky="ew", pady=(0, SPACING_SM))
            row.columnconfigure(1, weight=1)

            ttb.Label(row, text=f"{idx + 1}º -", width=5).grid(row=0, column=0, sticky="nw", padx=(0, SPACING_SM))
            text = tk.Text(row, height=2, wrap="word", font=("Segoe UI", 10))
            text.insert("1.0", text_value)
            text.grid(row=0, column=1, sticky="ew", padx=(0, SPACING_SM))
            text.bind("<<Modified>>", self._on_text_modified)

            btns = ttb.Frame(row)
            btns.grid(row=0, column=2, sticky="ne")
            btn_up = ttb.Button(btns, text="Subir", width=8, command=lambda i=idx: self._move_prep_step(i, -1))
            btn_up.pack(side="left", padx=(0, SPACING_SM))
            btn_down = ttb.Button(btns, text="Descer", width=8, command=lambda i=idx: self._move_prep_step(i, 1))
            btn_down.pack(side="left", padx=(0, SPACING_SM))
            btn_remove = ttb.Button(btns, text="Remover", width=9, command=lambda i=idx: self._remove_prep_step(i))
            btn_remove.pack(side="left")
            style_button(btn_up, "secondary")
            style_button(btn_down, "secondary")
            style_button(btn_remove, "danger")

            self._prep_step_rows.append(
                {
                    "frame": row,
                    "text": text,
                    "up": btn_up,
                    "down": btn_down,
                    "remove": btn_remove,
                }
            )
        self._sync_prep_step_buttons()
        self._bind_mousewheel_recursive(self._steps_container, self._on_steps_mousewheel)
        if self._steps_canvas is not None:
            self._steps_canvas.configure(scrollregion=self._steps_canvas.bbox("all"))

    def _set_prep_steps(self, steps: list[str]) -> None:
        self._render_prep_steps(steps)

    def _add_prep_step(self) -> None:
        if self._read_only:
            return
        steps = self._current_prep_steps()
        steps.append("")
        self._render_prep_steps(steps)
        if self._prep_step_rows:
            widget = self._prep_step_rows[-1].get("text")
            if isinstance(widget, tk.Text):
                widget.focus_set()
        self.mark_dirty()

    def _remove_prep_step(self, index: int) -> None:
        if self._read_only:
            return
        steps = self._current_prep_steps()
        if 0 <= index < len(steps):
            del steps[index]
            self._render_prep_steps(steps)
            self.mark_dirty()

    def _move_prep_step(self, index: int, delta: int) -> None:
        if self._read_only:
            return
        steps = self._current_prep_steps()
        target = index + delta
        if not (0 <= index < len(steps) and 0 <= target < len(steps)):
            return
        steps[index], steps[target] = steps[target], steps[index]
        self._render_prep_steps(steps)
        self.mark_dirty()

    def _sync_prep_step_buttons(self) -> None:
        state = "disabled" if self._read_only else "normal"
        if self._btn_add_step is not None:
            self._btn_add_step.configure(state=state)
        for idx, row in enumerate(self._prep_step_rows):
            text = row.get("text")
            if isinstance(text, tk.Text):
                text.configure(state=state)
            up = row.get("up")
            down = row.get("down")
            remove = row.get("remove")
            if isinstance(up, ttb.Button):
                up.configure(state=("disabled" if self._read_only or idx == 0 else "normal"))
            if isinstance(down, ttb.Button):
                down.configure(state=("disabled" if self._read_only or idx == len(self._prep_step_rows) - 1 else "normal"))
            if isinstance(remove, ttb.Button):
                remove.configure(state=state)

    def _prep_steps_for_save(self) -> list[str] | None:
        steps = self._current_prep_steps()
        if not steps:
            return []
        empty_indexes = [idx + 1 for idx, text in enumerate(steps) if not text.strip()]
        if empty_indexes:
            messagebox.showwarning(
                "Validação",
                "Preencha ou remova o passo vazio antes de salvar: "
                + ", ".join(str(i) for i in empty_indexes)
                + ".",
            )
            self._nb.select(self._tab_prep)
            first_empty = empty_indexes[0] - 1
            if 0 <= first_empty < len(self._prep_step_rows):
                widget = self._prep_step_rows[first_empty].get("text")
                if isinstance(widget, tk.Text):
                    widget.focus_set()
            return None
        return [text.strip() for text in steps]

    def _apply_read_only(self, ro: bool) -> None:
        self._read_only = ro
        for tab in (self._tab_dados, self._tab_ings, self._tab_prep, self._tab_cost, self._tab_pricing):
            self._set_frame_readonly(tab, ro)
        self._btn_add_ing.configure(state=("disabled" if ro else "normal"))
        self.ing_tree.configure(selectmode=("none" if ro else "browse"))
        self._sync_ing_buttons()
        self._sync_prep_step_buttons()
        st = "disabled" if ro else "normal"
        for b in (self._btn_save, self._btn_pdf):
            b.configure(state=st)

    def _set_frame_readonly(self, frame: tk.Widget, ro: bool) -> None:
        for c in frame.winfo_children():
            if isinstance(c, (ttb.Entry, tk.Text)):
                try:
                    c.configure(state=("disabled" if ro else "normal"))
                except tk.TclError:
                    pass
            elif isinstance(c, ttb.Combobox):
                try:
                    c.configure(state=("disabled" if ro else "readonly"))
                except tk.TclError:
                    pass
            elif isinstance(c, (ttb.Frame, ttb.Labelframe, tk.Canvas)):
                self._set_frame_readonly(c, ro)

    def start_new(self) -> None:
        self._suppress_dirty = True
        self.product_id = str(uuid.uuid4())
        self._is_new = True
        self._product_row = None
        self._ingredients = []
        self._read_only = False
        self.vars["nome"].set("")
        self.vars["categoria"].set("Outros")
        self.vars["rendimento"].set("")
        self.vars["unidade_rendimento"].set("un")
        self.vars["quantidade_porcoes"].set("1")
        self._legacy_observacoes = ""
        self._pricing_product_snapshot = None
        self._clear_pricing()
        if self._combo_tipo_ficha:
            self._combo_tipo_ficha.set(tipo_ficha_options()[0])
        self._set_prep_steps([])
        if self._combo_categoria:
            self._combo_categoria.configure(values=ensure_in_options(self.vars["categoria"].get(), PRODUCT_CATEGORIES))
        if self._combo_unidade_rendimento:
            self._combo_unidade_rendimento.configure(values=YIELD_UNIT_OPTIONS)
        self._refresh_tree()
        self._refresh_pricing()
        self._suppress_dirty = False
        self._set_clean()
        self._nb.select(0)
        self._on_title("Nova ficha técnica")
        self._apply_read_only(False)

    def load_product(self, product_id: str, read_only: bool = False) -> None:
        self._suppress_dirty = True
        self.product_id = str(product_id)
        self._is_new = False
        self._product_row = self._ps.get_product_row(product_id)
        self._ingredients = self._ps.get_ingredients(product_id) if self._product_row else []
        if not self._product_row:
            self._suppress_dirty = False
            return
        for k, var in self.vars.items():
            if k in self._product_row:
                var.set(self._product_row.get(k, "") or "")
        if self._combo_tipo_ficha:
            self._combo_tipo_ficha.set(tipo_ficha_label(self._product_row.get("tipo_ficha")))
        prep_rows = self._ps.get_prep_steps(product_id)
        self._set_prep_steps([str(r.get("descricao", "") or "") for r in prep_rows])
        self._load_pricing(self._ps.get_pricing(product_id))
        self._legacy_observacoes = str(self._product_row.get("observacoes", "") or "")
        if self._combo_categoria:
            cat = self.vars["categoria"].get()
            self._combo_categoria.configure(values=ensure_in_options(cat, PRODUCT_CATEGORIES))
        if self._combo_unidade_rendimento:
            self._combo_unidade_rendimento.configure(values=YIELD_UNIT_OPTIONS)
        self._refresh_tree()
        self._refresh_pricing()
        self._suppress_dirty = False
        self._set_clean()
        self._nb.select(0)
        nome = str(self._product_row.get("nome", "") or "")
        self._on_title("Editando ficha técnica: " + nome if not read_only else "Visualizar: " + nome)
        self._apply_read_only(read_only)

    def try_cancel(self) -> bool:
        """Retorna True se pode voltar à lista (cancelou ou não havia alterações)."""
        if self._dirty:
            if not messagebox.askyesno(
                "Alterações não salvas",
                "Existem alterações não salvas. Deseja sair mesmo assim?",
            ):
                return False
        self._set_clean()
        return True

    def _cancel(self) -> None:
        if self.try_cancel():
            self._on_cancel()

    def _collect_product(self) -> dict:
        creation = self._product_row.get("data_criacao") if self._product_row else now_str()
        tf = tipo_ficha_from_label(self._combo_tipo_ficha.get()) if self._combo_tipo_ficha else "produto_final"
        return {
            "produto_id": self.product_id,
            "nome": self.vars["nome"].get().strip(),
            "nome_normalizado": "",
            "categoria": self.vars["categoria"].get().strip(),
            "tipo_ficha": tf,
            "rendimento": to_float(self.vars["rendimento"].get()),
            "unidade_rendimento": self.vars["unidade_rendimento"].get().strip(),
            "quantidade_porcoes": to_float(self.vars["quantidade_porcoes"].get()),
            "tempo_preparo": "",
            "temperatura": "",
            "modo_preparo": "\n".join(text.strip() for text in self._current_prep_steps() if text.strip()),
            "observacoes": self._legacy_observacoes,
            "custo_total": 0,
            "custo_por_unidade": 0,
            "custo_por_porcao": 0,
            "custo_por_kg": 0,
            "data_criacao": creation,
            "data_atualizacao": now_str(),
            "active": True,
        }

    def _ingredient_display_name(self, ing: dict) -> str:
        n = str(ing.get("nome", "") or "").strip()
        if n:
            return n
        if str(ing.get("tipo", "")) == "produto_composto":
            ref = str(ing.get("produto_ref_id", "") or "")
            if ref:
                row = self._ps.get_product_row(ref)
                if row:
                    return str(row.get("nome", "") or "").strip() or f"(ficha {ref[:8]}…)"
                return f"(ficha ausente: {ref[:8]}…)" if len(ref) > 8 else "(ficha ausente)"
        return "(sem nome)"

    def _refresh_tree(self) -> None:
        self._cancel_quantity_edit()
        p = self._collect_product()
        p2, ings, warns = self._ps.recalc_draft(p, list(self._ingredients))
        self._ingredients = ings
        clear_tree(self.ing_tree)
        for idx, ing in enumerate(self._ingredients):
            tipo_lbl = (
                "Ficha intermediária" if ing.get("tipo") == "produto_composto" else "Ingrediente cadastrado"
            )
            line_id = str(ing.get("ingrediente_ficha_id") or ing.get("ingrediente_id") or "")
            tag = "even" if (idx + 1) % 2 == 0 else "odd"
            self.ing_tree.insert(
                "",
                "end",
                iid=line_id,
                tags=(tag,),
                values=(
                    self._ingredient_display_name(ing),
                    tipo_lbl,
                    ing.get("quantidade", ""),
                    ing.get("unidade", ""),
                    format_money_br(ing.get("custo_calculado")),
                ),
            )
        self._cv_total.set(format_money_br(p2.get("custo_total")))
        self._ing_total_var.set(f"Custo total dos ingredientes: {format_money_br(p2.get('custo_total'))}")
        self._cv_unit.set(format_money_br(p2.get("custo_por_unidade")))
        self._cv_porc.set(format_money_br(p2.get("custo_por_porcao")))
        ur = p.get("unidade_rendimento", "")
        if is_volume_unit(ur):
            self._cv_kg.set("Não aplicável")
        elif is_yield_unit_count_or_portion(ur):
            self._cv_kg.set("Não aplicável")
        else:
            self._cv_kg.set(format_money_br(p2.get("custo_por_kg")))
        self._calc_warning.set(" | ".join(warns) if warns else "")
        if self._ingredients:
            self._empty_ing_label.grid_remove()
        else:
            self._empty_ing_label.grid()
        self._sync_ing_buttons()
        self._pricing_product_snapshot = dict(p2)
        self._refresh_pricing(p2)

    def _add_ing(self) -> None:
        if self._read_only:
            return
        open_recipe_ingredient_dialog(
            self,
            self,
            self._ps,
            self._master_svc,
            self._ing_svc,
        )

    def _cancel_quantity_edit(self) -> None:
        if self._qty_edit_entry is not None:
            self._qty_edit_entry.destroy()
        self._qty_edit_entry = None
        self._qty_edit_iid = None

    def _selected_ingredient(self) -> dict | None:
        sel = self.ing_tree.selection()
        if not sel:
            return None
        iid = sel[0]
        return next(
            (
                i
                for i in self._ingredients
                if str(i.get("ingrediente_ficha_id") or i.get("ingrediente_id")) == iid
            ),
            None,
        )

    def _begin_quantity_edit(self, _event: object | None = None) -> None:
        if self._read_only:
            return
        event_y = getattr(_event, "y", None)
        if event_y is not None:
            row_id = self.ing_tree.identify_row(event_y)
            if row_id:
                self.ing_tree.selection_set(row_id)
                self.ing_tree.focus(row_id)
        sel = self.ing_tree.selection()
        if not sel:
            return
        iid = sel[0]
        ing = self._selected_ingredient()
        if not ing:
            return
        bbox = self.ing_tree.bbox(iid, "q")
        if not bbox:
            return
        self._cancel_quantity_edit()
        x, y, width, height = bbox
        entry = ttb.Entry(self.ing_tree, width=12)
        entry.insert(0, str(ing.get("quantidade", "") or ""))
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        entry.selection_range(0, "end")
        self._qty_edit_entry = entry
        self._qty_edit_iid = iid
        entry.bind("<Return>", lambda _e: self._commit_quantity_edit(entry, iid))
        entry.bind("<Escape>", lambda _e: self._cancel_quantity_edit())
        entry.bind("<FocusOut>", lambda _e: self._commit_quantity_edit(entry, iid))

    def _commit_quantity_edit(self, entry: ttb.Entry, iid: str) -> str:
        if self._qty_edit_entry is not entry:
            return "break"
        raw = entry.get().strip()
        if not raw:
            messagebox.showwarning("Validação", "Informe a quantidade usada na receita.")
            entry.focus_set()
            return "break"
        q = to_float(raw)
        if q <= 0:
            messagebox.showwarning("Validação", "Informe quantidade maior que zero.")
            entry.focus_set()
            return "break"
        for ing in self._ingredients:
            if str(ing.get("ingrediente_ficha_id") or ing.get("ingrediente_id")) == str(iid):
                ing["quantidade"] = q
                break
        self._cancel_quantity_edit()
        self.mark_dirty()
        self._refresh_tree()
        if self.ing_tree.exists(iid):
            self.ing_tree.selection_set(iid)
            self.ing_tree.focus(iid)
        return "break"

    def _remove_ing(self) -> None:
        self._cancel_quantity_edit()
        sel = self.ing_tree.selection()
        if not sel:
            messagebox.showwarning("Seleção", "Selecione um ingrediente na tabela.")
            return
        if not messagebox.askyesno(
            "Confirmar",
            "Tem certeza de que deseja remover este ingrediente da ficha?",
        ):
            return
        iid = sel[0]
        self._ingredients = [
            i for i in self._ingredients if str(i.get("ingrediente_ficha_id") or i.get("ingrediente_id")) != str(iid)
        ]
        self.mark_dirty()
        self._refresh_tree()

    def upsert_ingredient(self, ingredient: dict) -> None:
        iid = str(ingredient.get("ingrediente_ficha_id") or ingredient.get("ingrediente_id") or "")
        for idx, it in enumerate(self._ingredients):
            if str(it.get("ingrediente_ficha_id") or it.get("ingrediente_id")) == iid:
                self._ingredients[idx] = ingredient
                break
        else:
            self._ingredients.append(ingredient)
        self.mark_dirty()
        self._refresh_tree()

    def _save(self) -> None:
        if self._read_only:
            return
        prep_steps = self._prep_steps_for_save()
        if prep_steps is None:
            return
        p = self._collect_product()
        val = self._ps.validate_full(p, self._ingredients, self.product_id)
        if not val.ok:
            messagebox.showerror(
                "Não foi possível salvar",
                "Não foi possível salvar a ficha. Corrija os campos indicados:\n\n" + "\n".join(val.errors),
            )
            return
        try:
            p2, ings, _ = self._ps.recalc_draft(p, self._ingredients)
            pricing_row = self._pricing_row_for_save(p2)
            self._ps.save_product(p2, ings, prep_steps, pricing_row)
            self._product_row = p2
            self._ingredients = ings
            self._on_list_refresh()
            messagebox.showinfo("Salvo", "Ficha técnica salva com sucesso.")
            self._on_status("Ficha salva com sucesso.")
            self._refresh_tree()
            self._set_clean()
            self._is_new = False
            self._on_title("Editando ficha técnica: " + str(p2.get("nome", "")))
            self._on_saved(str(p2.get("produto_id") or self.product_id))
        except ProductServiceError as exc:
            messagebox.showerror("Erro ao salvar", str(exc))
        except Exception as exc:
            messagebox.showerror("Erro ao salvar", str(exc))

    def _pdf(self) -> None:
        prep_steps = self._prep_steps_for_save()
        if prep_steps is None:
            return
        p = self._collect_product()
        val = validate_product_for_save(p, self._ingredients, self._ps.list_active_products(), self.product_id)
        if not val.ok:
            messagebox.showerror(
                "PDF indisponível",
                "Não foi possível gerar o PDF. Corrija os seguintes pontos:\n\n" + "\n".join(val.errors),
            )
            return
        try:
            p2, ings, _ = self._ps.recalc_draft(p, self._ingredients)
            prod = Product.from_row_dict(p2)
            pub = product_to_public_pdf_dict(prod)
            pub["passos_preparo"] = [
                {"ordem": idx, "descricao": descricao}
                for idx, descricao in enumerate(prep_steps, start=1)
            ]
            lines = [ingredient_to_pdf_line(Ingredient.from_row_dict(i)) for i in ings]
            from app.services.pdf_service import generate_pdf

            payload = build_pdf_payload_from_public_dict(pub, lines)
            path = generate_pdf(payload)
            self._on_status(f"PDF gerado: {path}")
            prompt_open_generated_file(self, path, title="PDF gerado")
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _label_pdf(self) -> None:
        product = self._collect_product()
        if not str(product.get("nome", "") or "").strip():
            messagebox.showwarning("Etiqueta", "Informe o nome do produto antes de gerar a etiqueta.")
            return
        try:
            prep_steps = [
                {"ordem": idx, "descricao": descricao}
                for idx, descricao in enumerate(self._current_prep_steps(), start=1)
                if descricao.strip()
            ]
            payload = build_ingredient_label_payload(
                product,
                list(self._ingredients),
                prep_steps,
                nested_ingredient_resolver=self._ps.get_ingredients,
            )
            path = generate_ingredient_label_pdf(payload, get_labels_dir())
            self._on_status(f"Etiqueta gerada: {path}")
            prompt_open_generated_file(self, path, title="Etiqueta gerada")
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
