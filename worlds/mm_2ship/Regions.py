from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import MultiWorld, Region

from .Enums import Regions as RegionsEnum, Locations
from .Locations import MM2ShipLocation, location_data_table
from .LocationData import LOCATION_RCTYPE
from .LocationFilter import location_should_be_included
from .RegionData import REGIONS, START_REGION

if TYPE_CHECKING:
    from . import MM2ShipWorld


class MM2ShipRegion(Region):
    game = "2 Ship 2 Harkinian (MM)"

    def __init__(self, name: str, player: int, multiworld: MultiWorld, hint: str | None = None):
        super().__init__(name, player, multiworld, hint)


def _ap_region_name(rr_key: str) -> str:
    """RR_* id -> AP region display name. The start region is AP's Menu."""
    if rr_key == START_REGION:
        return "Menu"
    return RegionsEnum[rr_key[3:]].value


# RC_* -> owning RR_* (first region defining the check, in sorted RR order).
# A check can appear in several regions (shared enemy drops, say). The owner
# only decides which AP region the location displays under; reachability stays
# exact because the location rule asks the solver, which ORs over all of them.
_CHECK_OWNER: dict[str, str] = {}
for _rid, _spec in REGIONS.items():
    for _rc, _rule, _src in _spec.checks:
        _CHECK_OWNER.setdefault(_rc, _rid)


def create_regions_and_locations(world: "MM2ShipWorld") -> None:
    player = world.player
    multiworld = world.multiworld

    # One AP region per RandoRegion; the start region (RR_MAX) becomes Menu.
    ap_regions: dict[str, MM2ShipRegion] = {}
    for rr_key in REGIONS:
        region = MM2ShipRegion(_ap_region_name(rr_key), player, multiworld)
        ap_regions[rr_key] = region
        multiworld.regions.append(region)

    menu = ap_regions[START_REGION]

    # Star topology with always-open entrances. The solver already accounts for
    # region access, so per-location rules enforce all reachability and these
    # entrances exist only to give spoilers and trackers some structure.
    for rr_key, region in ap_regions.items():
        if rr_key != START_REGION:
            menu.connect(region, f"Menu -> {region.name}")

    use_logic = world.use_logic()

    # An option-disabled location is skipped entirely: nothing is placed there
    # and it never reaches the spoiler log. The C++ resync loop applies the same
    # filter, so it can't send a location ID the server has never heard of.
    # Map and compass locations are the exception: starting_maps_and_compasses
    # removes their items from the pool, not the locations themselves.
    from .PlacementConstraints import vanilla_placed_item_names
    from .VanillaItems import vanilla_items

    # A location keeps its vanilla item for one of two reasons: the placement_*
    # options left a dungeon item on its own check (see StaysAtVanillaCheck), or
    # boss remains aren't shuffled. Either way the check still exists and still
    # counts, it just always holds what it holds in the vanilla game.
    vanilla_placed = vanilla_placed_item_names(world)
    boss_remains_stay = not world.options.shuffle_boss_remains.value

    for loc in Locations:
        if loc == Locations.VICTORY:
            continue
        if not location_should_be_included(world, loc):
            continue

        rc_key = f"RC_{loc.name}"
        owner = _CHECK_OWNER.get(rc_key, START_REGION)
        parent = ap_regions[owner]

        address = location_data_table[loc]
        loc_obj = MM2ShipLocation(player, loc.value, address, parent)
        parent.locations.append(loc_obj)

        if use_logic:
            loc_obj.access_rule = (
                lambda state, rc=rc_key: world.logic.check_reachable(state, rc)
            )

        # Locking the item here is what makes the server hand it back on check.
        # ItemPool builds from unfilled locations only, so the same item cannot
        # also land in the random pool.
        vanilla_item = vanilla_items.get(loc)
        if vanilla_item is not None and (
            vanilla_item.value in vanilla_placed
            or (boss_remains_stay and LOCATION_RCTYPE.get(loc.name) == "RCTYPE_REMAINS")
        ):
            loc_obj.place_locked_item(world.create_item(vanilla_item.value))

    # Victory event: beating Majora (or the triforce goal, which the C++
    # completes automatically on collecting the required pieces).
    majora_region = ap_regions.get("RR_MOON_MAJORAS_LAIR", menu)
    victory = MM2ShipLocation(player, Locations.VICTORY.value, None, majora_region)
    majora_region.locations.append(victory)
    victory.place_locked_item(world.create_item("Victory", create_as_event=True))
    if use_logic:
        victory.access_rule = lambda state: world.victory_reachable(state)
