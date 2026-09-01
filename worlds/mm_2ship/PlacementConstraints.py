from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from BaseClasses import CollectionState, Item
from Fill import fill_restrictive

from .Enums import Items, Locations
from .LocationData import LOCATION_DUNGEON, LOCATION_RCTYPE
from .LocationFilter import SONG_LOCATIONS, SONG_LOCATION_ITEM_NAMES
from .OptionData import RO_CHOICE_VALUES

if TYPE_CHECKING:
    from . import MM2ShipWorld

logger = logging.getLogger("MM2SHIP")

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

# RandoOptionRemainsShuffle ordinals. A different enum from the placement one
# above. Own Dungeon is 2 here and 1 there, so never share a constant.
REMAINS_VANILLA = RO_CHOICE_VALUES["RO_REMAINS_SHUFFLE_VANILLA"]
REMAINS_OWN_DUNGEON = RO_CHOICE_VALUES["RO_REMAINS_SHUFFLE_OWN_DUNGEON"]

# CONFINEMENT_GROUP_SONGS on the C++ side, where it is an int past the last
# dungeon index. Groups are only ever compared for equality, so a string works.
SONGS_GROUP = "SONGS"

# Keyed by display name like LOCATION_VALUE_TO_DUNGEON, for Location.name lookups.
SONG_LOCATION_VALUES: frozenset[str] = frozenset(
    Locations[key].value for key, rctype in LOCATION_RCTYPE.items()
    if rctype == "RCTYPE_SONG" and key in Locations.__members__
)

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


def confinement_groups(world: "MM2ShipWorld") -> dict[str, str]:
    """AP item name -> confinement group, for every item this seed confines.

    Port of PlacementConstraints.cpp's RandoItemIdToConfinementGroup(). An item
    the C++ answers -1 for is absent here. The Skeleton Key is left out on
    purpose. It has no vanilla location and grants every dungeon's keys at once
    (GiveItem.cpp), so there is no single dungeon to confine it to.
    """
    groups: dict[str, str] = {}

    # Dropping the dungeon-less items is RandoItemIdToDungeon() returning -1.
    # Nothing to confine them to, so vanilla_placed_item_names pins them to
    # their own check instead.
    groups.update({
        name: dungeon
        for name, dungeon in dungeon_items_for_mode(world, OWN_DUNGEON).items()
        if dungeon is not None
    })

    if world.options.shuffle_boss_remains.value == REMAINS_OWN_DUNGEON:
        for dungeon, item_names in DUNGEON_ITEM_NAMES.items():
            groups[item_names["remains"]] = dungeon

    # Last, so a song wins over any dungeon answer. The C++ checks songs first.
    if world.options.shuffle_songs.value == SONG_LOCATIONS:
        for name in SONG_LOCATION_ITEM_NAMES:
            groups[name] = SONGS_GROUP

    return groups


def location_confinement_group(world: "MM2ShipWorld", location_name: str) -> str | None:
    """Port of CheckIdToConfinementGroup(). None for a check in no group."""
    if (world.options.shuffle_songs.value == SONG_LOCATIONS
            and location_name in SONG_LOCATION_VALUES):
        return SONGS_GROUP
    return LOCATION_VALUE_TO_DUNGEON.get(location_name)


def confine_items(world: "MM2ShipWorld") -> None:
    """Pre-place every confined item inside its own group's locations.

    Mirrors what PlacementConstraints.cpp does with IsItemAllowedAtCheck for
    the standalone randomizer. Must run from World.pre_fill(), after
    create_items() has filled multiworld.itempool and before the main fill
    consumes it.
    """
    confined_name_to_group = confinement_groups(world)
    if not confined_name_to_group:
        return

    # Pull this world's confined items out of the multiworld pool, per group.
    confined_by_group: dict[str, list[Item]] = {}
    remaining_pool: list[Item] = []
    for item in world.multiworld.itempool:
        group = confined_name_to_group.get(item.name) if item.player == world.player else None
        if group is not None:
            confined_by_group.setdefault(group, []).append(item)
        else:
            remaining_pool.append(item)
    if not confined_by_group:
        return
    world.multiworld.itempool[:] = remaining_pool

    # While these items are neither in the pool nor placed, expose them via
    # get_pre_fill_items so other worlds' all_state stays correct.
    world.pre_fill_items = [item for items in confined_by_group.values() for item in items]

    # Base state: everything else this player can end up with, meaning the rest
    # of their own pool plus a sweep restricted to this world's locations.
    # Sweeping the whole multiworld would scale with every other game's location
    # count for nothing, since this world's rules only read its own items.
    base_state = CollectionState(world.multiworld)
    for item in world.multiworld.itempool:
        if item.player == world.player:
            base_state.collect(item, prevent_sweep=True)
    base_state.sweep_for_advancements(locations=world.get_locations())

    group_locations: dict[str, list] = {}
    for location in world.multiworld.get_unfilled_locations(world.player):
        group = location_confinement_group(world, location.name)
        if group:
            group_locations.setdefault(group, []).append(location)

    def give_up(group: str, leftovers: list[Item]) -> None:
        """Hand the leftovers back to the general pool. The option did not
        fully take, so it warns."""
        logger.warning(
            "MM2Ship (player %s): no room left in %s for %s; "
            "they fall back to the general item pool.",
            world.player, group, sorted(item.name for item in leftovers))
        world.multiworld.itempool.extend(leftovers)

    for group, confined_items in confined_by_group.items():
        locations = [loc for loc in group_locations.get(group, []) if loc.item is None]
        if not locations:
            give_up(group, confined_items)
            continue

        # This group's fill can depend on the other groups' confined items,
        # including ones earlier iterations already placed. Count the still
        # unplaced ones as owned and re-sweep to pick up the placed ones.
        state = base_state.copy()
        for other_group, other_items in confined_by_group.items():
            if other_group != group:
                for item in other_items:
                    if item.location is None:
                        state.collect(item, prevent_sweep=True)
        state.sweep_for_advancements(locations=world.get_locations())

        world.random.shuffle(locations)

        # allow_partial: when a group has no room for all of its own confined
        # items (other options excluded most of a dungeon's locations, say), the
        # leftovers fall back to the main pool instead of failing generation.
        # fill_restrictive removes what it places, leaving the rest behind.
        fill_restrictive(
            world.multiworld, state, locations, confined_items,
            single_player_placement=True, lock=True, allow_excluded=True,
            allow_partial=True, name=f"MM2Ship {group}",
        )

        if confined_items:
            give_up(group, confined_items)

    world.pre_fill_items = []
