"""
Universal Tracker support: slot_data must carry everything seed-derived, and a
regeneration from slot_data alone (default yaml) must reproduce the world.
"""

from . import MM2ShipTestBase, setup_passthrough_multiworld
from ..OptionData import RO_OPTIONS


class TestUniversalTrackerRegen(MM2ShipTestBase):
    options = {
        "clock_shuffle": True,
        "clock_shuffle_progressive": "randomized",
        "shuffle_shops": True,
        "shuffle_owl_statues": True,
        "shuffle_triforce_pieces": True,
        "triforce_pieces_max": 10,
        "triforce_pieces_required": 5,
        "placement_small_keys": "own_dungeon",
        "access_majora_remains_count": 3,
        # a partial skulltula shuffle makes the location set itself seed-derived
        "shuffle_gold_skulltulas": True,
        "skulltula_shuffled": 7,
    }

    def test_slot_data_carries_all_options(self) -> None:
        slot_data = self.world.fill_slot_data()
        for ap_name, _default in RO_OPTIONS.values():
            self.assertIn(ap_name, slot_data, f"slot_data missing option {ap_name}")
        self.assertIn("true_no_logic", slot_data)
        self.assertIn("starting_clock", slot_data)
        self.assertIn("shop_prices", slot_data)
        self.assertTrue(slot_data["shop_prices"], "shop prices missing despite shuffle_shops")
        self.assertIn("skulltula_seed", slot_data)

    def test_interpret_slot_data_returns_passthrough(self) -> None:
        slot_data = self.world.fill_slot_data()
        self.assertEqual(self.world.interpret_slot_data(slot_data), slot_data)

    def test_regen_from_slot_data_reproduces_world(self) -> None:
        slot_data = self.world.fill_slot_data()
        # A different seed proves nothing depends on the original RNG.
        regen = setup_passthrough_multiworld(slot_data, seed=(self.multiworld.seed or 0) + 1)
        regen_world = regen.worlds[1]

        for ap_name, _default in RO_OPTIONS.values():
            self.assertEqual(
                getattr(regen_world.options, ap_name).value,
                getattr(self.world.options, ap_name).value,
                f"option {ap_name} not restored from slot_data")

        self.assertEqual(regen_world.shop_prices, self.world.shop_prices)
        self.assertEqual(regen_world.starting_clock_name, self.world.starting_clock_name)
        self.assertEqual(regen_world.skulltula_shuffled_locations,
                         self.world.skulltula_shuffled_locations)
        self.assertEqual(
            {loc.name for loc in regen.get_locations(1)},
            {loc.name for loc in self.multiworld.get_locations(self.player)},
            "regenerated world has a different location set")
        self.assertEqual(regen_world.fill_slot_data(), slot_data)
