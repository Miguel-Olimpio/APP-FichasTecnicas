import importlib
import pkgutil

import app


def test_all_app_modules_importable():
    failures = []
    for module in pkgutil.walk_packages(app.__path__, app.__name__ + "."):
        try:
            importlib.import_module(module.name)
        except Exception as exc:
            failures.append(f"{module.name}: {type(exc).__name__}: {exc}")

    assert failures == []
