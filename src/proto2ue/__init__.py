"""proto2ue package initialization."""

from .descriptor_loader import DescriptorLoader, OptionContext, OptionValidator
from . import model

__all__ = [
    "DescriptorLoader",
    "OptionContext",
    "OptionValidator",
    "model",
]
