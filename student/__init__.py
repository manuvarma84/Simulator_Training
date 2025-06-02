# auth/__init__.py
# professor/__init__.py
# student/__init__.py

# This can be empty but must exist
# Optional: Initialize blueprint here if needed
from .routes import student_bp

__all__ = ['student_bp']