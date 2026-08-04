"""
Dungeon item placement: Own Dungeon must confine items to their own dungeon,
Start With must hand them over up front and keep them out of the pool.
"""

from . import MM2ShipTestBase
from ..PlacementConstraints import DUNGEON_ITEM_NAMES, LOCATION_VALUE_TO_DUNGEON, PLACEMENT_OPTION_BY_TYPE


class TestOwnDungeonPlacement(MM2ShipTestBase):
    options = {
        "placement_small_keys": "own_dungeon",
        "placement_boss_keys": "own_dungeon",
        "placement_stray_fairies": "own_dungeon",
    }

    def test_dungeon_items_confined(self) -> None:
        confined_names = {
            item_names[item_type]: dungeon
            for dungeon, item_names in DUNGEON_ITEM_NAMES.items()
            for item_type in PLACEMENT_OPTION_BY_TYPE
        }

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
