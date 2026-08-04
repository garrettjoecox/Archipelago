from __future__ import annotations

import logging
import pkgutil
from typing import Any, ClassVar

import orjson

from BaseClasses import CollectionState, Item, Tutorial
from Options import OptionError
from worlds.AutoWorld import LogicMixin, WebWorld, World
from settings import Group, Bool

# NOTE: alias the enum — Python binds the .Items *module* to the name "Items"
# in this package's namespace when anything imports it, clobbering a plain
# `from .Enums import Items` binding.
from .Enums import Items as ItemsEnum
from .Items import MM2ShipItem, item_data_table, item_table, item_name_groups
from .LocationFilter import roll_skulltula_subset
from .Locations import location_table, location_name_groups
from .LogicRuntime import Solver
from .OptionData import RO_OPTIONS
from .Options import Logic, MM2ShipOptions, mm2ship_option_groups
from .Presets import mm2ship_options_presets
from .SourceInfo import BUILD_VERSION, SOURCE_COMMIT, SOURCE_DIRTY

logger = logging.getLogger("MM2SHIP")


class MM2ShipState(LogicMixin):
    """Per-CollectionState cache of the reachability solve.

    The 2ship logic is a global fixpoint over regions x 45 time slices x event
    counters, not a set of per-location item rules, so it cannot be expressed
    through AP's rule_builder (whose caching invalidates per item dependency).
    Instead the whole solve result is cached per state and invalidated by
    MM2ShipWorld.collect/remove whenever a logic-relevant item changes;
    identical inventories across states share results through the world-level
    memo in Solver. init_mixin/copy_mixin are the only hooks LogicMixin
    offers — invalidation deliberately lives in the world's collect/remove.
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
        Allow players to generate with true_no_logic or the no-logic Logic
        values. No-logic seeds may be impossible to complete without cheats,
        so hosts must opt in.
        """

    allow_true_no_logic: AllowTrueNoLogic | bool = False


class MM2ShipWorld(World):
    """2 Ship 2 Harkinian (Majora's Mask)"""

    game = "2 Ship 2 Harkinian (MM)"
    web = MM2ShipWebWorld()

    options: MM2ShipOptions
    options_dataclass = MM2ShipOptions
    settings: ClassVar[MM2ShipSettings]

    # name -> id mappings (dict[str, int]). These are the full static tables —
    # they feed the shared data package and must never vary per seed/options.
    location_name_to_id = location_table
    item_name_to_id = item_table

    # optional groups
    item_name_groups = item_name_groups
    location_name_groups = location_name_groups

    # Universal Tracker: regeneration needs only slot_data (all options and
    # shop prices are in it), no player yaml required.
    ut_can_gen_without_yaml = True

    def __init__(self, multiworld, player):
        super().__init__(multiworld, player)

        apworld_manifest = orjson.loads(
            pkgutil.get_data(__name__, "archipelago.json").decode("utf-8")
        )
        self.apworld_version: str = apworld_manifest.get("world_version", "0.1.0")

        # Shop prices (RC_* key -> price in rupees)
        self.shop_prices: dict[str, int] = {}

        # Clock Shuffle's guaranteed starting time item (see generate_early)
        self.starting_clock_name: str | None = None

        # Which Gold Skulltulas are checks, and the seed that picked them
        # (both filled in by generate_early — see LocationFilter).
        self.skulltula_seed: int = 0
        self.skulltula_shuffled_locations: frozenset[str] = frozenset()

        # Items held for placement during pre_fill (dungeon confinement);
        # populated only while confine_dungeon_items runs.
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
        if self.options.true_no_logic.value:
            return False
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
            if "true_no_logic" in passthrough:
                self.options.true_no_logic.value = int(passthrough["true_no_logic"])
            self.shop_prices = {str(k): int(v) for k, v in passthrough.get("shop_prices", {}).items()}
        else:
            if not self.use_logic() and not self.settings.allow_true_no_logic:
                raise OptionError(
                    f"MM2Ship (player {self.player}): no-logic generation "
                    f"(true_no_logic, or logic: no_logic/nearly_no_logic) requires the host "
                    f"to set allow_true_no_logic: true under mm_2ship_options in host.yaml."
                )

            # Generate random prices for shop and tingle shop locations,
            # keyed by the RC_ enum name (e.g. "RC_BOMB_SHOP_ITEM_01") to match
            # RandoStaticCheck.name on the C++ side. 0-200 mirrors 2Ship's range.
            from .ShopLocations import all_shop_locations

            for shop_location in all_shop_locations:
                self.shop_prices[f"RC_{shop_location.name}"] = self.random.randint(0, 200)

        # Required counts above what the pool can contain would be unbeatable;
        # clamp down to the pool cap, like the 2ship UI does.
        # skulltula_tokens_required is deliberately absent: every Spider House
        # always hands out all 30 of its tokens (skulltula_shuffled of them
        # through the pool, the rest straight from the unshuffled skulltulas),
        # so any requirement up to 30 stays satisfiable.
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

        # Clock Shuffle guarantee (mirrors GetComputedStartingItems): the
        # player always starts with one time item so some half-day is owned.
        # It is precollected (and the matching pool copy skipped in ItemPool)
        # so the game client grants it on connect.
        if self.options.clock_shuffle.value:
            if passthrough is not None:
                # Older slot_data has no "starting_clock" key; never roll RNG
                # here in a tracker regen — the server reports the real
                # precollected clock anyway.
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
        # Victory condition: collect the Victory event. Its location rule
        # (Regions.create_regions_and_locations) encodes beating Majora or the
        # triforce goal, matching what makes the C++ client send GOAL.
        self.set_completion_rule(lambda state: state.has("Victory", self.player))

    # ---------------------------------------------------------------- slot data

    def fill_slot_data(self) -> dict[str, Any]:
        # Every 2ship-mirrored option, by its C++ apName (the game applies
        # slot_data values straight into its option table by these names).
        slot_data: dict[str, Any] = {
            ap_name: int(getattr(self.options, ap_name).value)
            for ap_name, _default in RO_OPTIONS.values()
            if getattr(self.options, ap_name, None) is not None
        }
        slot_data.update({
            "apworld_version": self.apworld_version,
            # Wire-contract guard: location ids are RandoCheckId ordinals, so a
            # game build from a different 2ship release would silently write
            # items into the wrong checks. This is the CMake project version of
            # the checkout this apworld was generated from, which is exactly
            # what the client reports as gBuildVersion — it refuses to sync when
            # the two disagree.
            "game_build_version": BUILD_VERSION,
            # Suffixed when the checkout had uncommitted changes, so a mismatch
            # report never points at a commit that isn't what was generated.
            "source_commit": SOURCE_COMMIT + ("-dirty" if SOURCE_DIRTY else ""),
            "true_no_logic": int(self.options.true_no_logic.value),
            "starting_clock": self.starting_clock_name,
            # Seed behind the Gold Skulltula subset, so Universal Tracker can
            # rebuild the identical location list (see roll_skulltula_subset).
            "skulltula_seed": self.skulltula_seed,
            # Shop prices (dict[RC_* name, price])
            "shop_prices": self.shop_prices,
        })
        return slot_data

    @staticmethod
    def interpret_slot_data(slot_data: dict[str, Any]) -> dict[str, Any]:
        """Universal Tracker hook: hand slot_data back so UT regenerates the
        world with it available as multiworld.re_gen_passthrough (applied in
        generate_early)."""
        return slot_data


__all__ = [
    "MM2ShipWorld",
    "MM2ShipWebWorld",
    "MM2ShipSettings",
    "MM2ShipState",
]
