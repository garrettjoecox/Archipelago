"""
Own Dungeon placement: confined dungeon items must end up inside their own
dungeon (and nothing may linger in pre_fill_items afterwards).
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
