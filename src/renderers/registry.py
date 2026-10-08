"""
Available DOCX -> PDF renderers, selectable at runtime from the Settings page (setting "renderer", see settings.py).
"""
import logging
import threading

from .libreoffice_render_impl import LibreOfficeRenderImpl
from .render_interface import IRender
from .word_render_impl import WordRenderImpl

logger = logging.getLogger(__name__)

# Renderer id -> implementation, in order of preference when the configured one is not available.
RENDERERS: dict[str, type[IRender]] = {
    "libreoffice": LibreOfficeRenderImpl,
    "word": WordRenderImpl,
}

_instances: dict[str, IRender] = {}
_lock = threading.Lock()


def renderer_availability() -> dict[str, bool]:
    """Renderer id -> True if it can work on this machine."""
    return {renderer_id: implementation.is_available() for renderer_id, implementation in RENDERERS.items()}


def get_renderer(renderer_id: str) -> IRender:
    """
    Instance of the renderer renderer_id, created once and then reused (it caches e.g. the LibreOffice paths).
    If it is not available, the first available renderer is used instead; raises RuntimeError if there is none.
    """
    with _lock:
        if renderer_id not in _instances:
            available = renderer_availability()
            chosen = renderer_id if available.get(renderer_id) else next((key for key, ok in available.items() if ok), None)
            if chosen is None:
                raise RuntimeError("No PDF renderer available: install LibreOffice (or Microsoft Word on Windows).")
            if chosen != renderer_id:
                logger.warning("Renderer %r not available, using %r.", renderer_id, chosen)
            _instances[renderer_id] = _instances.get(chosen) or RENDERERS[chosen]()
            _instances.setdefault(chosen, _instances[renderer_id])
        return _instances[renderer_id]
