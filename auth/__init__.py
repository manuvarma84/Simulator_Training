# auth/__init__.py
# professor/__init__.py
# student/__init__.py

# This can be empty but must exist
# Optional: Initialize blueprint here if needed
from .routes import auth_bp

__all__ = ['auth_bp']