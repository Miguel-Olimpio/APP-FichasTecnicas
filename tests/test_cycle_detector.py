from app.services.cycle_detector_service import validate_no_cycle_for_save, would_create_cycle


def _ing(pid: str, ref: str) -> dict:
    return {
        "ingrediente_id": "x",
        "produto_id": pid,
        "tipo": "produto_composto",
        "produto_ref_id": ref,
    }


def test_direct_self_reference():
    all_rows = []
    cur = [_ing("A", "A")]
    assert validate_no_cycle_for_save("A", cur, all_rows) is False


def test_mutual_cycle():
    all_rows = [_ing("B", "A")]
    cur = [_ing("A", "B")]
    assert validate_no_cycle_for_save("A", cur, all_rows) is False


def test_longer_cycle():
    all_rows = [_ing("B", "C"), _ing("C", "A")]
    cur = [_ing("A", "B")]
    assert validate_no_cycle_for_save("A", cur, all_rows) is False


def test_no_cycle_linear():
    all_rows = []
    cur = [_ing("A", "B"), _ing("A", "C")]
    assert validate_no_cycle_for_save("A", cur, all_rows) is True


def test_would_create_cycle_helper():
    all_rows = [_ing("B", "A")]
    cur = [_ing("A", "B")]
    assert would_create_cycle("A", "B", all_rows, cur) is True
