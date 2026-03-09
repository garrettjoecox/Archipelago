"""
Option tests. Generation profiles first (each runs the full WorldTestBase
suite), then the C++ mirror contracts: defaults, slider bounds and choice
ordinals all have to match the generated OptionData tables, and through them
the 2ship sources.
"""

import unittest

from Options import Choice, OptionError

from . import MM2ShipTestBase
from ..Enums import Items
from ..LogicHelpersGen import MOON_MASK_ITEMS
from ..LocationFilter import RCTYPE_OPTION
from ..OptionData import RO_CHOICE_VALUES, RO_OPTIONS, RO_RANGES
from ..Options import MM2ShipOptions, mm2ship_option_groups
from ..Presets import mm2ship_options_presets
from ..VanillaItems import vanilla_items

# Heart Pieces sitting at their own locations, before starting_health adjusts them.
VANILLA_HEART_PIECES = sum(1 for item in vanilla_items.values() if item is Items.HEART_PIECE)


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


class TestTriforceTrapJunkFill(MM2ShipTestBase):
    """Triforce and trap counts, including the useful-classified surplus
    pieces past triforce_pieces_required."""

    options = {
        "shuffle_triforce_pieces": True,
        "triforce_pieces_max": 15,
        "triforce_pieces_required": 10,
        "shuffle_traps": True,
        "trap_amount": 5,
        "shuffle_pot_drops": True,
        "shuffle_grass_drops": True,
        "shuffle_enemy_drops": True,
        "shuffle_freestanding_items": True,
    }

    def _count(self, pred) -> int:
        return sum(1 for item in self.multiworld.itempool
                   if item.player == self.player and pred(item))

    def test_triforce_kept_and_classified(self) -> None:
        from BaseClasses import ItemClassification as IC
        piece = Items.TRIFORCE_PIECE.value
        self.assertEqual(self._count(lambda i: i.name == piece), 15)
        self.assertEqual(self._count(lambda i: i.name == piece and i.advancement), 10)
        self.assertEqual(
            self._count(lambda i: i.name == piece and i.classification == IC.useful), 5)

    def test_traps_added(self) -> None:
        self.assertEqual(self._count(lambda i: i.name == Items.TRAP.value), 5)


class TestJunkFillsExactRemainder(MM2ShipTestBase):
    """Junk still has to fill whatever locations are left over."""

    options = {
        "extra_items": {"Ice Arrows": 1},
    }

    def test_exactly_one_junk(self) -> None:
        junk = sum(1 for item in self.multiworld.itempool
                   if item.player == self.player and item.name == "Junk")
        self.assertEqual(junk, 1)


class TestTriforceMaxClampedToLocations(MM2ShipTestBase):
    """Asking for more pieces than the seed has locations clamps the count
    down to what fits."""

    options = {
        "shuffle_triforce_pieces": True,
        "triforce_pieces_max": 1000,
        "triforce_pieces_required": 10,
    }

    def test_max_clamped_required_kept(self) -> None:
        pieces = sum(1 for item in self.multiworld.itempool
                     if item.player == self.player and item.name == Items.TRIFORCE_PIECE.value)
        self.assertLess(pieces, 1000)  # actually clamped down
        self.assertEqual(self.world.options.triforce_pieces_max.value, pieces)
        self.assertEqual(self.world.options.triforce_pieces_required.value, 10)
        unfilled = len(self.multiworld.get_unfilled_locations(self.player))
        pool = sum(1 for item in self.multiworld.itempool if item.player == self.player)
        self.assertEqual(pool, unfilled)


class TestTriforceNoRoomRaises(MM2ShipTestBase):
    """Triforce Hunt with no room for a single piece is unwinnable, so
    generation raises instead of shipping it."""

    auto_construct = False
    run_default_tests = False

    def test_overflow_raises(self) -> None:
        self.options = {
            "shuffle_triforce_pieces": True,
            "triforce_pieces_max": 15,
            "triforce_pieces_required": 10,
            "extra_items": {"Ice Arrows": 2000},
        }
        with self.assertRaises(OptionError):
            self.world_setup()


class TestStartingHealthAddsHeartPieces(MM2ShipTestBase):
    """Below three hearts, GeneratePools.cpp puts four extra Heart Pieces in the
    pool per missing heart so the player can climb back to capacity."""

    options = {"starting_health": 1}

    def test_extra_pieces_added(self) -> None:
        pieces = sum(1 for item in self.multiworld.itempool
                     if item.player == self.player and item.name == "Heart Piece")
        self.assertEqual(pieces, VANILLA_HEART_PIECES + 8)


class TestStartingHealthRemovesHeartPieces(MM2ShipTestBase):
    """Above three hearts the pieces are redundant, so C++ drops four per extra
    heart. They are progression-classified here, so nothing else would trim them."""

    options = {"starting_health": 10}

    def test_pieces_removed(self) -> None:
        pieces = sum(1 for item in self.multiworld.itempool
                     if item.player == self.player and item.name == "Heart Piece")
        self.assertEqual(pieces, max(0, VANILLA_HEART_PIECES - 4 * (10 - 3)))


class TestTrialsTwentyMasks(MM2ShipTestBase):
    """The mask-count trial mode. It used to be the default, so nothing else
    covered it once upstream made Vanilla ordinal 0 and took its place."""

    options = {"access_trials": "20_masks"}

    def test_ordinal_sent_to_the_client(self) -> None:
        self.assertEqual(self.world.fill_slot_data()["access_trials"],
                         RO_CHOICE_VALUES["RO_ACCESS_TRIALS_20_MASKS"])


class TestMoonGossipStoneHints(MM2ShipTestBase):
    """Moon Trial gossip stones hint the 20 regular masks, so every one of them
    has to reach the client through slot_data's static_hints."""

    options = {"hints_moon_gossip_stones": True}

    def test_every_moon_mask_is_hinted(self) -> None:
        # Key presence only: this base stops before distribute_items_restrictive,
        # so nothing is placed yet and every hint list is legitimately empty here.
        # The lists are populated in a real generation, where fill_slot_data runs
        # after fill.
        hints = self.world.fill_slot_data()["static_hints"]
        for name in MOON_MASK_ITEMS:
            key = f"RI_{Items(name).name}"
            self.assertIn(key, hints, f"{name} is hinted in-game but absent from static_hints")

    def test_the_other_static_hints_survive(self) -> None:
        hints = self.world.fill_slot_data()["static_hints"]
        self.assertIn("RI_HOOKSHOT", hints)


class TestMoonGossipStoneHintsOff(MM2ShipTestBase):
    """Off by default, and then the 20 mask entries must not be paid for."""

    options = {}

    def test_moon_masks_absent(self) -> None:
        hints = self.world.fill_slot_data()["static_hints"]
        absent = [name for name in MOON_MASK_ITEMS if f"RI_{Items(name).name}" in hints]
        self.assertFalse(absent, f"moon mask hints sent with the option off: {absent}")


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

    def test_no_logic_choice_requires_host_opt_in(self) -> None:
        with self.assertRaises(OptionError):
            self._run_with_gate({"logic": "no_logic"}, allow=False)

    def test_no_logic_allowed_when_host_opts_in(self) -> None:
        self._run_with_gate({"logic": "no_logic"}, allow=True)


class TestOptionMirror(unittest.TestCase):
    """The AP options mirror the 2ship sources through the generated OptionData
    tables: same defaults, same slider bounds, same choice ordinals. slot_data
    sends the raw ints to the game, so drift here is a live bug, not a style
    complaint."""

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
        """Every option gating a location type is repeated by hand in four
        places, and three of them fail silently when one is missed. A typo in
        RCTYPE_OPTION enables the whole type, because
        location_should_be_included reads it with a defaulting getattr. A gap
        in Allsanity ships a preset that does not mean what it says. A gap in
        TestAllShuffles quietly drops a location class from the headline
        all-on generation test."""
        hints = MM2ShipOptions.type_hints
        grouped = {option for group in mm2ship_option_groups for option in group.options}
        allsanity = mm2ship_options_presets["Allsanity"]

        for rctype, ap_name in sorted(RCTYPE_OPTION.items()):
            self.assertIn(ap_name, hints,
                          f"{rctype} maps to {ap_name!r}, which is not an MM2ShipOptions field, "
                          f"so the filter would treat that location type as always on")
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

    def _choice_options(self):
        """(ap_name, option class, C++ enum member prefix) for every Choice option."""
        hints = MM2ShipOptions.type_hints
        for ro, (ap_name, _default) in RO_OPTIONS.items():
            option_cls = hints[ap_name]
            if issubclass(option_cls, Choice):
                yield ap_name, option_cls, self.CHOICE_PREFIX_OVERRIDES.get(ap_name, ro)

    def test_choice_values_match_cpp(self) -> None:
        checked = 0
        for ap_name, option_cls, prefix in self._choice_options():
            for choice_name, choice_value in option_cls.options.items():
                member = f"{prefix}_{self.CHOICE_NAME_ALIASES.get(choice_name, choice_name).upper()}"
                self.assertIn(member, RO_CHOICE_VALUES,
                              f"{ap_name}.option_{choice_name}: no C++ enum member {member}")
                self.assertEqual(choice_value, RO_CHOICE_VALUES[member],
                                 f"{ap_name}.option_{choice_name} = {choice_value} but "
                                 f"{member} = {RO_CHOICE_VALUES[member]} in Types.h")
                checked += 1
        self.assertGreater(checked, 0, "no choice options were checked")

    def test_every_cpp_choice_is_offered(self) -> None:
        """The other direction. A value upstream adds to a choice enum is a mode
        players can pick in the 2ship menu, so the yaml has to offer it too.
        Without this check a new enum member regenerates into OptionData and
        nothing fails; the mode is just missing from Archipelago."""
        for ap_name, option_cls, prefix in self._choice_options():
            members = {member: value for member, value in RO_CHOICE_VALUES.items()
                       if member.startswith(f"{prefix}_")}
            # A wrong prefix matches nothing, and the loop below would then
            # pass vacuously for exactly the option it was meant to guard.
            self.assertTrue(members,
                            f"no RO_CHOICE_VALUES member starts with {prefix}_, so {ap_name} "
                            f"is not actually being checked against Types.h")
            offered = set(option_cls.options.values())
            for member, value in members.items():
                self.assertIn(value, offered,
                              f"{member} ({value}) is a 2ship choice for {ap_name}, "
                              f"but no AP option value exposes it")
