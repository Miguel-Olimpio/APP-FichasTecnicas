from app.utils.units import (
    ensure_in_options,
    format_quantity_with_unit,
    get_units_for_cost_unit,
    is_count_unit,
    is_valid_unit_for_cost_unit,
    normalize_cost_unit_key,
    normalize_unit,
    to_kg,
    unit_family,
)


def test_normalize_unit():
    assert normalize_unit(" KG ") == "kg"


def test_to_kg_from_g():
    assert abs(to_kg(500, "g") - 0.5) < 1e-9


def test_unit_family_mass():
    assert unit_family("kg") == "mass"


def test_get_units_for_cost_unit():
    assert get_units_for_cost_unit("kg") == ["kg", "g"]
    assert "un" in get_units_for_cost_unit("un")
    assert get_units_for_cost_unit("porção") == ["porção"]


def test_is_valid_unit_for_cost_unit():
    assert is_valid_unit_for_cost_unit("g", "kg")
    assert not is_valid_unit_for_cost_unit("un", "kg")
    assert is_valid_unit_for_cost_unit("pacote", "un")


def test_ensure_in_options():
    assert "kg" in ensure_in_options("kg", ["kg", "g"])
    assert "legado" in ensure_in_options("legado", ["kg", "g"])


def test_normalize_cost_unit_key():
    assert normalize_cost_unit_key("unidade") == "un"
    assert normalize_cost_unit_key("porção") == "porção"


def test_is_count_unit_alias():
    assert is_count_unit("un")
    assert is_count_unit("pacote")


def test_format_quantity_with_unit_converts_sub_kilo_and_sub_liter():
    assert format_quantity_with_unit("0,8", "kg") == "800 g"
    assert format_quantity_with_unit(0.8, "L") == "800 mL"
    assert format_quantity_with_unit(1.25, "kg") == "1,25 kg"
