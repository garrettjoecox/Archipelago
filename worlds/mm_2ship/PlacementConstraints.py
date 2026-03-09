from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import CollectionState, Item
from Fill import fill_restrictive

from .Enums import Items, Locations
from .LocationData import LOCATION_DUNGEON
from .OptionData import RO_CHOICE_VALUES

if TYPE_CHECKING:
    from . import MM2ShipWorld

# LOCATION_DUNGEON is keyed by the Locations enum's attribute name (e.g.
# "WOODFALL_TEMPLE_BOSS_KEY_CHEST"), while AP Location objects are named after
# the enum's display value (e.g. "Woodfall Temple Boss Key Chest"). Re-keying by
# display value is what makes a lookup by Location.name work.
LOCATION_VALUE_TO_DUNGEON: dict[str, str] = {
    Locations[key].value: dungeon for key, dungeon in LOCATION_DUNGEON.items() if key in Locations.__members__
}

# Each dungeon's Small Key, Boss Key and Stray Fairy by AP item name, generated
# from Rando::Logic::DungeonItemToDungeon() (LogicHelpersGen).
from .LogicHelpersGen import DUNGEON_ITEMS as DUNGEON_ITEM_NAMES

# Confined item type -> the MM2ShipOptions attribute controlling its placement.
PLACEMENT_OPTION_BY_TYPE: dict[str, str] = {
    "small_key": "placement_small_keys",
    "boss_key": "placement_boss_keys",
    "stray_fairy": "placement_stray_fairies",
}

# RandoOptionDungeonItemPlacement ordinals, from the generated Types.h mirror.
OWN_DUNGEON = RO_CHOICE_VALUES["RO_DUNGEON_ITEM_OWN_DUNGEON"]
START_WITH = RO_CHOICE_VALUES["RO_DUNGEON_ITEM_START_WITH"]
VANILLA = RO_CHOICE_VALUES["RO_DUNGEON_ITEM_VANILLA"]

# The one Stray Fairy that belongs to no dungeon, so DungeonItemToDungeon()
# returns -1 for it while DungeonItemPlacementOption() still routes it through
# placement_stray_fairies (PlacementConstraints.cpp names it explicitly).
CLOCK_TOWN_STRAY_FAIRY = Items.CLOCK_TOWN_STRAY_FAIRY.value


def placement_mode(world: "MM2ShipWorld", item_type: str) -> int:
    """The placement_* value governing one confined dungeon item type."""
    return getattr(world.options, PLACEMENT_OPTION_BY_TYPE[item_type]).value


def dungeon_items_for_mode(world: "MM2ShipWorld", mode: int) -> dict[str, str | None]:
    """AP item name -> owning dungeon, for the dungeon items placed by `mode`.

    The single membership table the placement rules below are phrased against,
    mirroring PlacementConstraints.cpp's DungeonItemPlacementOption(). Each item
    type routes through its own placement_* option, and the Clock Town Stray
    Fairy rides along with the stray fairies despite belonging to no dungeon.
    A `None` dungeon is that C++ function's `DungeonItemToDungeon() < 0`.
    """
    items: dict[str, str | None] = {}
    for item_type in PLACEMENT_OPTION_BY_TYPE:
        if placement_mode(world, item_type) != mode:
            continue
        for dungeon, item_names in DUNGEON_ITEM_NAMES.items():
            items[item_names[item_type]] = dungeon
    if placement_mode(world, "stray_fairy") == mode:
        items[CLOCK_TOWN_STRAY_FAIRY] = None
    return items


def vanilla_placed_item_names(world: "MM2ShipWorld") -> frozenset[str]:
    """AP item names that stay at their own vanilla location.

    Port of PlacementConstraints.cpp's StaysAtVanillaCheck(), which
    GeneratePools consults before anything else: such a check keeps its vanilla
    item and is marked shuffled, but enters neither the check nor the item pool.
    The AP mirror keeps the location and locks the vanilla item onto it
    (Regions.py), which is what makes the client see the same shuffled check
    holding the same item.
    """
    # case RO_DUNGEON_ITEM_VANILLA: return true;
    names = set(dungeon_items_for_mode(world, VANILLA))
    # case RO_DUNGEON_ITEM_OWN_DUNGEON: return DungeonItemToDungeon(itemId) < 0;
    # There is no dungeon to confine the Clock Town fairy to, so it stays put.
    names.update(name for name, dungeon in dungeon_items_for_mode(world, OWN_DUNGEON).items()
                 if dungeon is None)
    return frozenset(names)


def confine_dungeon_items(world: "MM2ShipWorld") -> None:
    """Pre-place dungeon items into their own dungeon under Own Dungeon.

    Mirrors the confinement PlacementConstraints.cpp does with
    RandoItemIdToDungeon/IsItemAllowedAtCheck for the standalone randomizer.
    Must run from World.pre_fill(), after create_items() has filled
    multiworld.itempool and before the main fill consumes it.

    The Skeleton Key is deliberately left out. It has no vanilla location and
    grants every dungeon's keys at once (GiveItem.cpp), so there is no single
    dungeon to confine it to.
    """
    # Item name -> owning dungeon, for every type whose option is Own Dungeon.
    # Dropping the dungeon-less items is RandoItemIdToDungeon() returning -1:
    # they can't be confined, and vanilla_placed_item_names pins them instead.
    confined_name_to_dungeon: dict[str, str] = {
        name: dungeon
        for name, dungeon in dungeon_items_for_mode(world, OWN_DUNGEON).items()
        if dungeon is not None
    }
    if not confined_name_to_dungeon:
        return

    # Pull this world's confined items out of the multiworld pool, per dungeon.
    confined_by_dungeon: dict[str, list[Item]] = {}
    remaining_pool: list[Item] = []
    for item in world.multiworld.itempool:
        dungeon = confined_name_to_dungeon.get(item.name) if item.player == world.player else None
        if dungeon is not None:
            confined_by_dungeon.setdefault(dungeon, []).append(item)
        else:
            remaining_pool.append(item)
    if not confined_by_dungeon:
        return
    world.multiworld.itempool[:] = remaining_pool

    # While these items are neither in the pool nor placed, expose them via
    # get_pre_fill_items so other worlds' all_state stays correct.
    world.pre_fill_items = [item for items in confined_by_dungeon.values() for item in items]

    # Base state: everything else this player can end up with, meaning the rest
    # of their own pool plus a sweep restricted to this world's locations.
    # Sweeping the whole multiworld would scale with every other game's location
    # count for nothing, since this world's rules only read its own items.
    base_state = CollectionState(world.multiworld)
    for item in world.multiworld.itempool:
        if item.player == world.player:
            base_state.collect(item, prevent_sweep=True)
    base_state.sweep_for_advancements(locations=world.get_locations())

    dungeon_locations: dict[str, list] = {}
    for location in world.multiworld.get_unfilled_locations(world.player):
        dungeon = LOCATION_VALUE_TO_DUNGEON.get(location.name)
        if dungeon:
            dungeon_locations.setdefault(dungeon, []).append(location)

    for dungeon, confined_items in confined_by_dungeon.items():
        locations = [loc for loc in dungeon_locations.get(dungeon, []) if loc.item is None]
        if not locations:
            world.multiworld.itempool.extend(confined_items)
            continue

        # This dungeon's fill can depend on the other dungeons' confined items,
        # including ones earlier iterations already placed. Count the still
        # unplaced ones as owned and re-sweep to pick up the placed ones.
        state = base_state.copy()
        for other_dungeon, other_items in confined_by_dungeon.items():
            if other_dungeon != dungeon:
                for item in other_items:
                    if item.location is None:
                        state.collect(item, prevent_sweep=True)
        state.sweep_for_advancements(locations=world.get_locations())

        world.random.shuffle(locations)

        # allow_partial: when a dungeon has no room for all of its own confined
        # items (other options excluded most of its locations, say), the
        # leftovers fall back to the main pool instead of failing generation.
        fill_restrictive(
            world.multiworld, state, locations, confined_items,
            single_player_placement=True, lock=True, allow_excluded=True,
            allow_partial=True, name=f"MM2Ship {dungeon}",
        )

        if confined_items:
            world.multiworld.itempool.extend(confined_items)

    world.pre_fill_items = []
