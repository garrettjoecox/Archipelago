"""
Option tests: generation profiles (each runs the full WorldTestBase suite),
plus the C++ mirror contracts — defaults, slider bounds and choice ordinals
must match the generated OptionData tables (i.e. the 2ship sources).
"""

import unittest

from Options import Choice, OptionError

from . import MM2ShipTestBase
from ..LocationFilter import RCTYPE_OPTION
from ..OptionData import RO_CHOICE_VALUES, RO_OPTIONS, RO_RANGES
from ..Options import MM2ShipOptions, mm2ship_option_groups
from ..Presets import mm2ship_options_presets


class TestDefault(MM2ShipTestBase):
    options = {}


class TestAllShuffles(MM2ShipTestBase):
    options = {
        "shuffle_pot_drops": True,
        "shuffle_crate_drops": True,
        "shuffle_barrel_drops": True,
        "shuffle_grass_drops": True,
        "shuffle_tree_drops": True,
        "shuffle_snowball_drops": True,
        "shuffle_freestanding_items": True,
        "shuffle_enemy_drops": True,
        "shuffle_butterflies": True,
        "shuffle_hive_drops": True,
        "shuffle_wonder_items": True,
        "shuffle_cows": True,
        "shuffle_frogs": True,
        "shuffle_shops": True,
        "shuffle_tingle_shops": True,
        "shuffle_gold_skulltulas": True,
        "shuffle_owl_statues": True,
        "shuffle_boss_remains": True,
        "shuffle_boss_souls": True,
        "shuffle_enemy_souls": True,
        "shuffle_ocarina": True,
        "shuffle_ocarina_buttons": True,
        "shuffle_swim": True,
        "shuffle_sword": True,
        "shuffle_shield": True,
        "shuffle_song_time": True,
        "shuffle_song_sun": True,
        "shuffle_song_double_time": True,
        "shuffle_song_inverted_time": True,
        "shuffle_song_saria": True,
        "shuffle_skeleton_key": True,
        "shuffle_tycoon_wallet": True,
    }


class TestClockShuffleRandom(MM2ShipTestBase):
    options = {
        "clock_shuffle": True,
        "clock_shuffle_progressive": "randomized",
    }


class TestClockShuffleAscending(MM2ShipTestBase):
    options = {
        "clock_shuffle": True,
        "clock_shuffle_progressive": "ascending",
    }


class TestSoulsanity(MM2ShipTestBase):
    options = {
        "shuffle_enemy_souls": True,
        "shuffle_boss_souls": True,
        "shuffle_enemy_drops": True,
    }


class TestTriforceHunt(MM2ShipTestBase):
    options = {
        "shuffle_triforce_pieces": True,
        "triforce_pieces_max": 15,
        "triforce_pieces_required": 10,
    }


class TestDungeonAccessOpen(MM2ShipTestBase):
    options = {
        "access_dungeons": "open",
    }


class TestMoonRemainsZero(MM2ShipTestBase):
    options = {
        "access_moon_remains_count": 0,
        "access_trials": "open",
    }


class TestMaxMaskRequirements(MM2ShipTestBase):
    """The mask-count gates at their new maximum (20 = every regular mask)
    must still generate a completable seed."""
    options = {
        "access_majora_masks_count": 20,
        "access_moon_masks_count": 20,
    }


class TestRequiredCountsClamped(MM2ShipTestBase):
    """required > max would be unbeatable; generate_early clamps down."""
    options = {
        "shuffle_triforce_pieces": True,
        "triforce_pieces_max": 12,
        "triforce_pieces_required": 900,
        "stray_fairies_max": 5,
        "stray_fairies_required": 15,
        "shuffle_pot_drops": True,  # room for the triforce pieces
    }

    def test_required_clamped_to_max(self) -> None:
        self.assertEqual(self.world.options.triforce_pieces_required.value, 12)
        self.assertEqual(self.world.options.stray_fairies_required.value, 5)


class TestNoLogicGate(MM2ShipTestBase):
    """No-logic generation must be blocked unless the host opts in.

    The host setting is forced in each test (and restored) so results don't
    depend on whatever the local host.yaml happens to allow.
    """
    auto_construct = False
    run_default_tests = False

    def _run_with_gate(self, options: dict, allow: bool) -> None:
        from .. import MM2ShipWorld
        self.options = options
        previous = MM2ShipWorld.settings.allow_true_no_logic
        MM2ShipWorld.settings.allow_true_no_logic = allow
        try:
            self.world_setup()
        finally:
            MM2ShipWorld.settings.allow_true_no_logic = previous

    def test_true_no_logic_requires_host_opt_in(self) -> None:
        with self.assertRaises(OptionError):
            self._run_with_gate({"true_no_logic": True}, allow=False)

    def test_no_logic_choice_requires_host_opt_in(self) -> None:
        with self.assertRaises(OptionError):
            self._run_with_gate({"logic": "no_logic"}, allow=False)

    def test_no_logic_allowed_when_host_opts_in(self) -> None:
        self._run_with_gate({"true_no_logic": True}, allow=True)


class TestOptionMirror(unittest.TestCase):
    """The AP options must mirror the 2ship sources (via the generated
    OptionData tables): same defaults, same slider bounds, same choice
    ordinals. slot_data sends the raw ints to the game, so any drift here is
    a live bug, not a style issue."""

    # AP-side deliberate differences from the C++ defaults, with reasons.
    INTENTIONAL_DEFAULT_DIVERGENCES = {
        "starting_rupees": 99,  # QoL: start with a full base wallet
    }

    # Choice enums whose C++ member prefix differs from the option's RO_* id.
    CHOICE_PREFIX_OVERRIDES = {
        "placement_small_keys": "RO_DUNGEON_ITEM",
        "placement_boss_keys": "RO_DUNGEON_ITEM",
        "placement_stray_fairies": "RO_DUNGEON_ITEM",
        "clock_shuffle_progressive": "RO_CLOCK_SHUFFLE",
    }

    # AP choice attr -> C++ member name fragment, where they differ.
    CHOICE_NAME_ALIASES = {
        "randomized": "RANDOM",
    }

    def test_location_type_options_are_wired_everywhere(self) -> None:
        """Every option that gates a location type is repeated by hand in four
        places, and three of them fail silently when one is missed: a typo in
        RCTYPE_OPTION enables the whole type (location_should_be_included reads
        it with a defaulting getattr), a gap in Allsanity ships a preset that
        does not mean what it says, and a gap in TestAllShuffles quietly drops
        a location class from the headline all-on generation test."""
        hints = MM2ShipOptions.type_hints
        grouped = {option for group in mm2ship_option_groups for option in group.options}
        allsanity = mm2ship_options_presets["Allsanity"]

        for rctype, ap_name in sorted(RCTYPE_OPTION.items()):
            self.assertIn(ap_name, hints,
                          f"{rctype} maps to {ap_name!r}, which is not an MM2ShipOptions field — "
                          f"the filter would silently treat that location type as always on")
            self.assertIn(hints[ap_name], grouped,
                          f"{ap_name} is in no OptionGroup")
            self.assertTrue(allsanity.get(ap_name),
                            f"{ap_name} adds locations but is not enabled in the Allsanity preset")
            self.assertTrue(TestAllShuffles.options.get(ap_name),
                            f"{ap_name} adds locations but is not enabled in TestAllShuffles")

    def test_defaults_match_cpp(self) -> None:
        hints = MM2ShipOptions.type_hints
        for ro, (ap_name, cpp_default) in RO_OPTIONS.items():
            option_cls = hints[ap_name]
            expected = self.INTENTIONAL_DEFAULT_DIVERGENCES.get(ap_name, cpp_default)
            self.assertEqual(
                option_cls.default, expected,
                f"{ap_name} default {option_cls.default} drifted from {ro} ({expected})")

    def test_range_bounds_match_cpp_sliders(self) -> None:
        hints = MM2ShipOptions.type_hints
        for ro, (range_min, range_max, _default) in RO_RANGES.items():
            ap_name, _ = RO_OPTIONS[ro]
            option_cls = hints[ap_name]
            self.assertEqual(option_cls.range_start, range_min,
                             f"{ap_name} range_start != {ro} slider min")
            if range_max is None:
                # dynamic UI max: the static ceiling is the paired _MAX option's max
                paired_ap, _ = RO_OPTIONS[ro.replace("_REQUIRED", "_MAX")]
                range_max = hints[paired_ap].range_end
            self.assertEqual(option_cls.range_end, range_max,
                             f"{ap_name} range_end != {ro} slider max")

    def test_choice_values_match_cpp(self) -> None:
        hints = MM2ShipOptions.type_hints
        checked = 0
        for ro, (ap_name, _default) in RO_OPTIONS.items():
            option_cls = hints[ap_name]
            if not issubclass(option_cls, Choice):
                continue
            prefix = self.CHOICE_PREFIX_OVERRIDES.get(ap_name, ro)
            for choice_name, choice_value in option_cls.options.items():
                member = f"{prefix}_{self.CHOICE_NAME_ALIASES.get(choice_name, choice_name).upper()}"
                self.assertIn(member, RO_CHOICE_VALUES,
                              f"{ap_name}.option_{choice_name}: no C++ enum member {member}")
                self.assertEqual(choice_value, RO_CHOICE_VALUES[member],
                                 f"{ap_name}.option_{choice_name} = {choice_value} but "
                                 f"{member} = {RO_CHOICE_VALUES[member]} in Types.h")
                checked += 1
        self.assertGreater(checked, 0, "no choice options were checked")
