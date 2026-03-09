"""
Shop and Tingle shop locations that need randomized prices.

Derived from the generated LOCATION_RCTYPE table so new shop checks flow in
automatically when the apworld data is regenerated.

These are ordered tuples, not sets: generate_early draws one RNG price per
entry while iterating, so iteration order must be identical on every
machine/process for a seed to be reproducible (set order follows the salted
string hash and is not).
"""

from .Enums import Locations
from .LocationData import LOCATION_RCTYPE

# All shop locations (RCTYPE_SHOP), in generated (enum) order
shop_locations: tuple[Locations, ...] = tuple(
    Locations[key] for key, rctype in LOCATION_RCTYPE.items() if rctype == "RCTYPE_SHOP"
)

# All tingle shop locations (RCTYPE_TINGLE_SHOP), in generated (enum) order
tingle_shop_locations: tuple[Locations, ...] = tuple(
    Locations[key] for key, rctype in LOCATION_RCTYPE.items() if rctype == "RCTYPE_TINGLE_SHOP"
)

# Every shop/tingle location that needs a price, in stable order
all_shop_locations: tuple[Locations, ...] = shop_locations + tingle_shop_locations
