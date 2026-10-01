"""Local-only, descriptive workflow evidence tools. No hosted-service client."""
from .core import ValidationError, analyze, compare, load_events, validate_events
__version__ = "0.1.0"
__all__ = ["ValidationError", "analyze", "compare", "load_events", "validate_events"]
