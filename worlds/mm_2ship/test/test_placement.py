"""
Dungeon item placement: Own Dungeon must confine items to their own dungeon,
Start With must hand them over up front and keep them out of the pool, and
Vanilla must lock every one of them onto the location it holds in the vanilla
game (StaysAtVanillaCheck).
"""

from . import MM2ShipTestBase
from ..Enums import Locations
from ..PlacementConstraints import (
    CLOCK_TOWN_STRAY_FAIRY, DUNGEON_ITEM_NAMES, LOCATION_VALUE_TO_DUNGEON, PLACEMENT_OPTION_BY_TYPE,
)
from ..VanillaItems import vanilla_items

# Every dungeon item, by AP item name -> the dungeon that owns it. Built here
# rather than through PlacementConstraints' own helper, because the tests have
# to be able to disagree with the code they check.
DUNGEON_OF_ITEM = {
    item_names[item_type]: dungeon
    for dungeon, item_names in DUNGEON_ITEM_NAMES.items()
    for item_type in PLACEMENT_OPTION_BY_TYPE
}
# ... plus the Clock Town Stray Fairy, which the placement options govern
# despite it belonging to no dungeon.
ALL_DUNGEON_ITEMS = set(DUNGEON_OF_ITEM) | {CLOCK_TOWN_STRAY_FAIRY}


class TestOwnDungeonPlacement(MM2ShipTestBase):
    options = {
        "placement_small_keys": "own_dungeon",
        "placement_boss_keys": "own_dungeon",
        "placement_stray_fairies": "own_dungeon",
    }

    def test_dungeon_items_confined(self) -> None:
        confined_names = DUNGEON_OF_ITEM

        placed_any = False
        for location in self.multiworld.get_filled_locations(self.player):
            if location.item and location.item.name in confined_names:
                placed_any = True
                self.assertEqual(
                    LOCATION_VALUE_TO_DUNGEON.get(location.name),
                    confined_names[location.item.name],
                    f"{location.item.name} placed outside its dungeon at {location.name}")
        self.assertTrue(placed_any, "no confined dungeon items were pre-placed")

        # Default options leave plenty of dungeon room, so nothing should have
        # fallen back to the main pool, and the pre_fill window must be closed.
        leftovers = [item.name for item in self.multiworld.itempool
                     if item.player == self.player and item.name in confined_names]
        self.assertFalse(leftovers, f"confined items fell back to the main pool: {leftovers}")
        self.assertFalse(self.world.pre_fill_items)

    def test_clock_town_stray_fairy_stays_vanilla(self) -> None:
        """It belongs to no dungeon, so Own Dungeon has nowhere to confine it to;
        StaysAtVanillaCheck leaves it on its own check instead of in the pool."""
        location = self.multiworld.get_location(Locations.CLOCK_TOWN_STRAY_FAIRY.value, self.player)
        self.assertTrue(location.locked)
        self.assertEqual(location.item.name, CLOCK_TOWN_STRAY_FAIRY)
        self.assertNotIn(CLOCK_TOWN_STRAY_FAIRY,
                         [item.name for item in self.multiworld.itempool if item.player == self.player])


class TestStartWithDungeonItems(MM2ShipTestBase):
    """Start With mirrors GetComputedStartingItems: the player is granted every
    dungeon item on connect, so none of them may also sit in the pool."""

    options = {
        "placement_small_keys": "start_with",
        "placement_boss_keys": "start_with",
        "placement_stray_fairies": "start_with",
        "shuffle_skeleton_key": True,
    }

    # GetComputedStartingItems' counts, one per vanilla location of each kind.
    EXPECTED_STARTING_COUNTS = {
        "Woodfall Small Key": 1,
        "Snowhead Small Key": 3,
        "Great Bay Small Key": 1,
        "Stone Tower Small Key": 4,
        "Woodfall Boss Key": 1,
        "Snowhead Boss Key": 1,
        "Great Bay Boss Key": 1,
        "Stone Tower Boss Key": 1,
        "Woodfall Stray Fairy": 15,
        "Snowhead Stray Fairy": 15,
        "Great Bay Stray Fairy": 15,
        "Stone Tower Stray Fairy": 15,
        # Belongs to no dungeon, but GetComputedStartingItems grants it too.
        CLOCK_TOWN_STRAY_FAIRY: 1,
    }

    def test_dungeon_items_not_in_pool(self) -> None:
        granted = set(self.EXPECTED_STARTING_COUNTS)
        pooled = [item.name for item in self.multiworld.itempool
                  if item.player == self.player and item.name in granted]
        self.assertFalse(pooled, f"start-with dungeon items still in the pool: {sorted(set(pooled))}")

    def test_skeleton_key_not_shuffled(self) -> None:
        """It would have nothing left to unlock (GeneratePools.cpp skips it)."""
        self.assertNotIn(
            "Skeleton Key",
            [item.name for item in self.multiworld.itempool if item.player == self.player])

    def test_solver_starts_with_them(self) -> None:
        starting = self.world.logic.starting_counts
        for name, count in self.EXPECTED_STARTING_COUNTS.items():
            self.assertEqual(starting.get(name, 0), count,
                             f"{name} missing from the solver's starting inventory")


class TestVanillaDungeonItemPlacement(MM2ShipTestBase):
    """Vanilla mirrors StaysAtVanillaCheck: the check stays a check, but it always
    holds the item it holds in the vanilla game, and none enter the item pool."""

    options = {
        "placement_small_keys": "vanilla",
        "placement_boss_keys": "vanilla",
        "placement_stray_fairies": "vanilla",
        # Would otherwise be clamped down to 5 and make the required count a lie.
        "stray_fairies_max": 5,
        "stray_fairies_required": 15,
    }

    def test_locked_onto_their_vanilla_locations(self) -> None:
        seen = 0
        for loc, vanilla_item in vanilla_items.items():
            if vanilla_item.value not in ALL_DUNGEON_ITEMS:
                continue
            location = self.multiworld.get_location(loc.value, self.player)
            self.assertTrue(location.locked, f"{loc.value} is not locked to its vanilla item")
            self.assertEqual(location.item.name, vanilla_item.value)
            seen += 1
        # 9 Small Keys + 4 Boss Keys + 4x15 Stray Fairies + the Clock Town one.
        self.assertEqual(seen, 74)

    def test_none_in_the_item_pool(self) -> None:
        pooled = sorted({item.name for item in self.multiworld.itempool
                         if item.player == self.player and item.name in ALL_DUNGEON_ITEMS})
        self.assertFalse(pooled, f"vanilla-placed dungeon items still in the pool: {pooled}")

    def test_stray_fairy_pool_cap_normalized(self) -> None:
        """No fairy enters the pool, so every dungeon keeps all 15 and the
        required count must not be clamped down to the cap (OnFileCreate.cpp)."""
        self.assertEqual(self.world.options.stray_fairies_max.value, 15)
        self.assertEqual(self.world.options.stray_fairies_required.value, 15)

    def test_pool_still_balances_locations(self) -> None:
        unfilled = len(self.multiworld.get_unfilled_locations(self.player))
        pool = sum(1 for item in self.multiworld.itempool if item.player == self.player)
        self.assertEqual(pool, unfilled)
