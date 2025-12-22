"""Typing shims.

These helpers provide stable type signatures for optional dependencies.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, overload


def _identity_decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    return func


def _decorator_factory[**P, R](
    *_args: Any,
    **_kwargs: Any,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        return func

    return decorator


@overload
def cache_data[**P, R](func: Callable[P, R]) -> Callable[P, R]: ...


@overload
def cache_data[**P, R](
    *,
    ttl: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def cache_data[**P, R](func: Callable[P, R] | None = None, **kwargs: Any) -> Any:
    """
    Streamlit cache_data shim.

    If streamlit is available, returns streamlit.cache_data. Otherwise,
    returns a no-op decorator.
    """
    try:
        import streamlit as st

        if func is None:
            return st.cache_data(**kwargs)
        return st.cache_data(func=func, **kwargs)
    except Exception:
        if func is not None:
            return _identity_decorator(func)
        return _decorator_factory(**kwargs)


@overload
def cache_resource[**P, R](func: Callable[P, R]) -> Callable[P, R]: ...


@overload
def cache_resource[**P, R](
    *,
    ttl: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def cache_resource[**P, R](func: Callable[P, R] | None = None, **kwargs: Any) -> Any:
    """
    Streamlit cache_resource shim.

    If streamlit is available, returns streamlit.cache_resource. Otherwise,
    returns a no-op decorator.
    """
    try:
        import streamlit as st

        if func is None:
            return st.cache_resource(**kwargs)
        return st.cache_resource(func=func, **kwargs)
    except Exception:
        if func is not None:
            return _identity_decorator(func)
        return _decorator_factory(**kwargs)
