from __future__ import annotations

import sys
from collections.abc import Callable
from types import ModuleType
from typing import Any, Literal, cast, get_args, get_origin

_PATCHED = False


def _patch_pydantic_v1_for_py314() -> None:
    if sys.version_info < (3, 14):
        return

    try:
        from pydantic.v1 import utils as v1_utils
    except Exception:
        return

    global _PATCHED
    if _PATCHED:
        return

    original_func = cast(Callable[[object, object], bool], v1_utils.lenient_issubclass)

    def _literal_issubclass(cls: object, class_or_tuple: object) -> bool:
        origin = get_origin(class_or_tuple)
        if origin is not Literal:
            return False
        literal_types: set[type[object]] = {type(arg) for arg in get_args(class_or_tuple)}
        if not literal_types:
            return False
        literal_type_tuple = tuple(literal_types)
        if isinstance(cls, type):
            return issubclass(cls, literal_type_tuple)
        return False

    def lenient_issubclass(cls: object, class_or_tuple: object) -> bool:
        try:
            return original_func(cls, class_or_tuple)
        except TypeError:
            return _literal_issubclass(cls, class_or_tuple)

    _PATCHED = True
    v1_utils.lenient_issubclass = lenient_issubclass

    try:
        from pydantic.v1 import main as v1_main
    except Exception:
        return

    v1_main_any = cast(Any, v1_main)
    v1_main_any.lenient_issubclass = lenient_issubclass


def try_import_great_expectations() -> tuple[ModuleType | None, Exception | None]:
    _patch_pydantic_v1_for_py314()
    try:
        import great_expectations as gx
    except Exception as exc:
        if sys.version_info >= (3, 14):
            return None, RuntimeError(
                "Great Expectations failed to import on Python 3.14 (pydantic v1). "
                f"Original error: {exc}"
            )
        return None, exc

    return gx, None


def import_great_expectations() -> ModuleType:
    gx, error = try_import_great_expectations()
    if gx is None:
        assert error is not None
        raise error
    return gx
