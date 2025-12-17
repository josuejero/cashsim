from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

import streamlit as st

F = TypeVar("F", bound=Callable[..., Any])


Decorator = Callable[[F], F]
Factory = Callable[..., Decorator]


cache_data = cast(Factory, st.cache_data)
cache_resource = cast(Factory, st.cache_resource)
