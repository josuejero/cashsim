from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

import streamlit as st

F = TypeVar("F", bound=Callable[..., Any])

# A cache decorator factory returns a decorator that preserves the wrapped signature.
Decorator = Callable[[F], F]
Factory = Callable[..., Decorator]

# Streamlit provides decorator factories; we narrow types for checkers.
cache_data = cast(Factory, st.cache_data)
cache_resource = cast(Factory, st.cache_resource)
