from __future__ import annotations

import logging
import pkgutil
from typing import Any, ClassVar

import orjson

from BaseClasses import CollectionState, Item, Tutorial
from Options import OptionError
from worlds.AutoWorld import LogicMixin, WebWorld, World
from settings import Group, Bool

# Importing anything from this package binds the .Items *module* to the name
# "Items" here, clobbering a plain `from .Enums import Items`. Hence the alias.
from .Enums import Items as ItemsEnum
from .Items import MM2ShipItem, item_data_table, item_table, item_name_groups
from .LocationFilter import roll_skulltula_subset
from .Locations import location_table, location_name_groups
from .LogicHelpersGen import MOON_MASK_ITEMS
from .LogicRuntime import STRAY_FAIRY_SCATTERED_TOTAL, Solver
from .OptionData import RO_OPTIONS
from .Options import Logic, MM2ShipOptions, mm2ship_option_groups
from .Presets import mm2ship_options_presets
from .SourceInfo import BUILD_VERSION, SOURCE_COMMIT, SOURCE_DIRTY

logger = logging.getLogger("MM2SHIP")


class MM2ShipState(LogicMixin):
    """Per-CollectionState cache of the reachability solve.

    2ship logic is a global fixpoint over regions x 45 time slices x event
    counters rather than per-location item rules, so it does not fit AP's
    rule_builder, whose caching invalidates per item dependency. The whole
    solve is cached per state instead. LogicMixin only offers init_mixin and
    copy_mixin, so invalidation lives in MM2ShipWorld.collect/remove.
    """

    mm2ship_result: dict[int, Any]

    def init_mixin(self, multiworld) -> None:
        self.mm2ship_result = {}

    def copy_mixin(self, new_state: CollectionState) -> CollectionState:
        new_state.mm2ship_result = dict(self.mm2ship_result)
        return new_state


class MM2ShipWebWorld(WebWorld):
    theme = "ice"  # placeholder
    option_groups = mm2ship_option_groups
    options_presets = mm2ship_options_presets

    setup_en = Tutorial(
        tutorial_name="Start Guide",
        description="A guide to playing 2 Ship 2 Harkinian (MM) in Archipelago.",
        language="English",
        file_name="guide_en.md",
        link="guide/en",
        authors=["ItsHeckinPat"],
    )

    tutorials = [setup_en]
    game_info_languages = ["en"]


class MM2ShipSettings(Group):
    class AllowTrueNoLogic(Bool):
        """
        Allow players to pick the no_logic and nearly_no_logic Logic values.
        Seeds generated that way can be impossible to complete without
        cheating, so hosts have to opt in.
        """

    allow_true_no_logic: AllowTrueNoLogic | bool = False


class MM2ShipWorld(World):
    """2 Ship 2 Harkinian (Majora's Mask)"""

    game = "2 Ship 2 Harkinian (MM)"
    web = MM2ShipWebWorld()

    options: MM2ShipOptions
    options_dataclass = MM2ShipOptions
    settings: ClassVar[MM2ShipSettings]

    # The full static tables. They feed the shared data package, so they must
    # never vary by seed or by options.
    location_name_to_id = location_table
    item_name_to_id = item_table

    item_name_groups = item_name_groups
    location_name_groups = location_name_groups

    # Universal Tracker regenerates from slot_data alone; no player yaml needed.
    ut_can_gen_without_yaml = True

    def __init__(self, multiworld, player):
        super().__init__(multiworld, player)

        apworld_manifest = orjson.loads(
            pkgutil.get_data(__name__, "archipelago.json").decode("utf-8")
        )
        self.apworld_version: str = apworld_manifest.get("world_version", "0.1.0")

        # RC_* enum name -> price in rupees.
        self.shop_prices: dict[str, int] = {}

        # Clock Shuffle's guaranteed starting time item (see generate_early)
        self.starting_clock_name: str | None = None

        # Which Gold Skulltulas are checks, and the seed that picked them.
        # Both are filled in by generate_early (see LocationFilter).
        self.skulltula_seed: int = 0
        self.skulltula_shuffled_locations: frozenset[str] = frozenset()

        # Non-empty only while confine_dungeon_items runs, so other worlds'
        # all_state can still see items that are neither pooled nor placed.
        self.pre_fill_items: list[Item] = []

        self._logic: Solver | None = None

    # ------------------------------------------------------------------ logic

    @property
    def logic(self) -> Solver:
        """Reachability solver over the generated region graph. Built lazily so
        options and shop prices are final (after generate_early)."""
        if self._logic is None:
            self._logic = Solver(self)
        return self._logic

    def use_logic(self) -> bool:
        """True when access rules should be applied (glitchless/vanilla logic)."""
        return self.options.logic.value in (Logic.option_glitchless, Logic.option_vanilla)

    def victory_reachable(self, state: CollectionState) -> bool:
        """Goal: collect the required triforce pieces (the game auto-completes),
        or reach Majora's Lair and be able to defeat Majora."""
        if self.options.shuffle_triforce_pieces.value:
            return state.has("Piece of the Triforce", self.player,
                             self.options.triforce_pieces_required.value)
        if not self.logic.region_reachable(state, "RR_MOON_MAJORAS_LAIR"):
            return False
        if self.options.shuffle_boss_souls.value:
            return state.has("Soul of Majora", self.player)
        return True

    def collect(self, state: CollectionState, item: Item) -> bool:
        changed = super().collect(state, item)
        # Only a logic-relevant item can change the solve result. Goal-only
        # items (triforce pieces) and filler would otherwise trigger a full
        # re-solve per collect, which gets expensive with hundreds of pieces.
        if changed and (self._logic is None or item.name in self._logic.logic_item_names):
            state.mm2ship_result.pop(self.player, None)
        return changed

    def remove(self, state: CollectionState, item: Item) -> bool:
        changed = super().remove(state, item)
        if changed and (self._logic is None or item.name in self._logic.logic_item_names):
            state.mm2ship_result.pop(self.player, None)
        return changed

    # ---------------------------------------------------------------- worldgen

    def generate_early(self) -> None:
        # Universal Tracker regeneration: restore everything seed-derived from
        # slot_data instead of rolling it again (see interpret_slot_data).
        passthrough = getattr(self.multiworld, "re_gen_passthrough", {}).get(self.game)
        if passthrough is not None:
            for ap_name, _default in RO_OPTIONS.values():
                option = getattr(self.options, ap_name, None)
                if option is not None and ap_name in passthrough:
                    option.value = int(passthrough[ap_name])
            self.shop_prices = {str(k): int(v) for k, v in passthrough.get("shop_prices", {}).items()}
        else:
            if not self.use_logic() and not self.settings.allow_true_no_logic:
                raise OptionError(
                    f"MM2Ship (player {self.player}): no-logic generation "
                    f"(logic: no_logic/nearly_no_logic) requires the host "
                    f"to set allow_true_no_logic: true under mm_2ship_options in host.yaml."
                )

            # Keyed by RC_ enum name (e.g. "RC_BOMB_SHOP_ITEM_01") to match
            # RandoStaticCheck.name on the C++ side. 0-200 is 2Ship's range.
            from .ShopLocations import all_shop_locations

            for shop_location in all_shop_locations:
                self.shop_prices[f"RC_{shop_location.name}"] = self.random.randint(0, 200)

        # Vanilla Stray Fairies never enter the pool, so every dungeon keeps its
        # full set of 15 whatever the pool cap says. OnFileCreate.cpp normalizes
        # the option the same way, which also stops the clamp below from
        # lowering stray_fairies_required for no reason.
        from .PlacementConstraints import VANILLA
        if self.options.placement_stray_fairies.value == VANILLA:
            self.options.stray_fairies_max.value = STRAY_FAIRY_SCATTERED_TOTAL

        # A requirement the pool can't satisfy is an unbeatable seed, so clamp
        # it down the way the 2ship UI does. skulltula_tokens_required is
        # deliberately absent: every Spider House hands out all 30 of its tokens
        # either way, so any requirement up to 30 is satisfiable.
        for required_name, cap_name in (
            ("triforce_pieces_required", "triforce_pieces_max"),
            ("stray_fairies_required", "stray_fairies_max"),
        ):
            required = getattr(self.options, required_name)
            cap = getattr(self.options, cap_name).value
            if required.value > cap:
                logger.warning(
                    "MM2Ship (player %s): %s (%s) exceeds %s (%s); clamping down.",
                    self.player, required_name, required.value, cap_name, cap)
                required.value = cap

        # Which Gold Skulltulas are checks (see LocationFilter for the rules).
        if passthrough is not None:
            self.skulltula_seed = int(passthrough.get("skulltula_seed", 0))
        else:
            self.skulltula_seed = self.random.getrandbits(32)
        self.skulltula_shuffled_locations = roll_skulltula_subset(
            self.options.skulltula_shuffled.value, self.skulltula_seed)

        # Mirrors GetComputedStartingItems: one time item is guaranteed, so
        # some half-day is always owned. Precollecting it (and skipping the
        # matching pool copy in ItemPool) is what makes the client grant it on
        # connect.
        if self.options.clock_shuffle.value:
            if passthrough is not None:
                # Older slot_data has no "starting_clock" key. Never roll RNG in
                # a tracker regen; the server reports the real precollected
                # clock anyway.
                clock = passthrough.get("starting_clock")
                self.starting_clock_name = str(clock) if clock else None
            elif self.options.clock_shuffle_progressive.value == 0:  # RO_CLOCK_SHUFFLE_RANDOM
                self.starting_clock_name = self.random.choice([
                    "Time (Day 1)", "Time (Night 1)", "Time (Day 2)",
                    "Time (Night 2)", "Time (Day 3)", "Time (Night 3)",
                ])
            else:
                self.starting_clock_name = "Progressive Time"
            if self.starting_clock_name:
                self.multiworld.push_precollected(self.create_item(self.starting_clock_name))

    def create_regions(self) -> None:
        from .Regions import create_regions_and_locations
        create_regions_and_locations(self)

    def create_item(self, name: str, create_as_event: bool = False) -> MM2ShipItem:
        item_enum = ItemsEnum(name)
        entry = item_data_table[item_enum]

        return MM2ShipItem(
            str(item_enum.value),
            entry.classification,
            None if create_as_event else entry.item_id,
            self.player,
        )

    def create_items(self) -> None:
        from .ItemPool import create_item_pool, create_plentiful_and_trap_items

        create_item_pool(self)
        create_plentiful_and_trap_items(self)

    def get_filler_item_name(self) -> str:
        from .ItemPool import get_filler_item
        return get_filler_item(self)

    def get_pre_fill_items(self) -> list[Item]:
        return list(self.pre_fill_items)

    def pre_fill(self) -> None:
        from .PlacementConstraints import confine_dungeon_items
        confine_dungeon_items(self)

    def set_rules(self) -> None:
        # The Victory event's own location rule (in Regions.py) is what encodes
        # beating Majora or finishing the triforce hunt, matching whatever makes
        # the C++ client send GOAL.
        self.set_completion_rule(lambda state: state.has("Victory", self.player))

    # ---------------------------------------------------------------- slot data

    def fill_slot_data(self) -> dict[str, Any]:
        # Keyed by C++ apName, which is how the game applies them straight
        # into its own option table.
        slot_data: dict[str, Any] = {
            ap_name: int(getattr(self.options, ap_name).value)
            for ap_name, _default in RO_OPTIONS.values()
            if getattr(self.options, ap_name, None) is not None
        }
        slot_data.update({
            "apworld_version": self.apworld_version,
            # Wire-contract guard. Location ids are RandoCheckId ordinals, so a
            # build from a different 2ship release would silently write items
            # into the wrong checks. This is the CMake project version of the
            # checkout the data was generated from, which is the same number the
            # client reports as gBuildVersion; it refuses to sync on a mismatch.
            "game_build_version": BUILD_VERSION,
            # Suffixed when that checkout had uncommitted changes, so a mismatch
            # report never names a commit nobody can check out.
            "source_commit": SOURCE_COMMIT + ("-dirty" if SOURCE_DIRTY else ""),
            "starting_clock": self.starting_clock_name,
            # Universal Tracker rebuilds the identical location list from this
            # seed alone (see roll_skulltula_subset).
            "skulltula_seed": self.skulltula_seed,
            "shop_prices": self.shop_prices,
            # Static in-game hints ("the Hookshot can be found ...") still have
            # to resolve when the item landed in another player's world, which
            # the client's own location scouts cannot see. Every placement of
            # each statically hinted item, keyed by the RI_* name the client
            # resolves with GetItemIdFromName: [[player slot, AP location id]].
            "static_hints": self._static_hints(),
        })
        return slot_data

    # Items hinted by fixed in-game hint givers (pirate hookshot talk, smithy
    # gold dust hint, Skull Kid's Oath hint, Song of Soaring engraving, the
    # bounty posters). This has to cover every item the client passes to
    # Rando::GetItemLocationForHint / GetForeignItemLocations.
    STATIC_HINT_ITEMS: ClassVar[tuple[str, ...]] = (
        "HOOKSHOT",
        "BOTTLE_GOLD_DUST",
        "SONG_OATH",
        "SONG_SOARING",
        "REMAINS_ODOLWA",
        "REMAINS_GOHT",
        "REMAINS_GYORG",
        "REMAINS_TWINMOLD",
        "MASK_DEKU",
        "MASK_GORON",
        "MASK_ZORA",
    )

    def _static_hint_item_keys(self) -> tuple[str, ...]:
        """Every RI_* key whose placements need to ride in slot_data this seed.

        The Moon Trial gossip stones each hint one of the 20 regular masks.
        EnGs.cpp walks ITEM_MASK_TRUTH..ITEM_MASK_GIANT, the same range
        MoonMaskCount() counts, so the generated list stays in step. They ride
        along only when that option is on, because it is off by default and
        they nearly double the size of the whole static-hint payload.
        """
        if not self.options.hints_moon_gossip_stones.value:
            return self.STATIC_HINT_ITEMS
        return (*self.STATIC_HINT_ITEMS,
                *(ItemsEnum(name).name for name in MOON_MASK_ITEMS))

    def _static_hints(self) -> dict[str, list[list[int]]]:
        static_hints: dict[str, list[list[int]]] = {}
        for key in self._static_hint_item_keys():
            static_hints[f"RI_{key}"] = [
                [location.player, location.address]
                for location in self.multiworld.find_item_locations(
                    ItemsEnum[key].value, self.player, resolve_group_locations=True)
                if location.address is not None
            ]
        return static_hints

    @staticmethod
    def interpret_slot_data(slot_data: dict[str, Any]) -> dict[str, Any]:
        """Universal Tracker hook. Handing slot_data back is what makes it show
        up as multiworld.re_gen_passthrough during UT's regeneration, where
        generate_early applies it."""
        return slot_data


__all__ = [
    "MM2ShipWorld",
    "MM2ShipWebWorld",
    "MM2ShipSettings",
    "MM2ShipState",
]
