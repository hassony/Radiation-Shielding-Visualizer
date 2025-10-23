# __init__.py — Marks this directory as a Python package

"""
xray_interaction package
------------------------
This package contains the simplified physical models and
visualization utilities for the X-ray Interaction Visualizer project.
"""

from .physics import (
    Z_MAP,
    energy_grid,
    photoelectric_rel,
    compton_rel,
    rayleigh_rel,
    normalize_interactions
)
