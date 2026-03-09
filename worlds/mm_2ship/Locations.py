from __future__ import annotations

from enum import StrEnum

from BaseClasses import Location

from .Enums import Locations  # string Enum: Locations.SOMETHING.value == "Human Readable Name"


class MM2ShipLocation(Location):
    game = "2 Ship 2 Harkinian (MM)"


# --------------------------------------------------------------------------
# AP Location IDs
#
# IDs are the C++ RandoCheckId enum ordinals (Enums.py preserves that order),
# because the game client static_casts them. Upstream regularly inserts checks
# mid-enum, shifting every later ID. That is fine under the wire contract: the
# game build and the apworld always ship from the same 2ship commit.
# --------------------------------------------------------------------------

base_location_table: dict[Locations, int] = {
    loc: i for i, loc in enumerate(Locations, start=1)
}

location_data_table: dict[Locations, int | None] = {
    **base_location_table,
    # Event locations (no network address)
    Locations.VICTORY: None,
}

# Archipelago wants {name: address} with a string name, and event locations
# (address=None) have no place in the network table.
location_table: dict[str, int] = {loc.value: addr for loc, addr in location_data_table.items() if addr is not None}


# pickling will fail unless the items in the group are actual strings
def stringify_set(items: set[StrEnum]) -> set[str]:
    return {str(item) for item in items}


location_name_groups: dict[str, set[str]] = {
    # Add groups later if you want.
    # Example:
    # "Bosses": stringify_set({Locations.ODOLWA, Locations.GOHT, Locations.GYORG, Locations.TWINMOLD}),
}
