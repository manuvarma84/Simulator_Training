# business_simulation/__init__.py
from .routes import bp  # The blueprint from routes.py
from . import decorators  # Makes decorators available at package level

__version__ = "1.0.0"  # Optional but recommended

# Optional: Explicit exports list
__all__ = ['bp', 'decorators']