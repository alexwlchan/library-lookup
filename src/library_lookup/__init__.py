"""
Tidied-up code for my library-lookup project.

This is code extracted from the main scripts which has been tested and
documented to a higher standard than the rest of the code.

Functions in this library may be a good candidate for extracting into
a utility library like chives.
"""

from .passwords import get_required_password


__all__ = ["get_required_password"]
