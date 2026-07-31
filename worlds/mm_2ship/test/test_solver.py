"""
Solver regression tests against the generated region graph.

These guard the pipeline end-to-end: if a regenerated RegionData/LogicHelpersGen
breaks coverage or the vanilla layout becomes uncompletable, they fail before
anything reaches a real multiworld.
"""

from BaseClasses import ItemClassification as IC

from . import MM2ShipTestBase
from ..Enums import Locations
from ..ItemData import ITEMS
from ..Items import item_data_table
from ..LogicHelpersGen import CAN_USE_EXPLOSIVE
from ..LogicRuntime import LogicContext
from ..RegionData import REGIONS
from ..VanillaItems import vanilla_items


def _all_checks() -> set[str]:
    checks: set[str] = set()
    for spec in REGIONS.values():
        checks.update(rc for rc, _, _ in spec.checks)
    return checks


class TestSolverCoverage(MM2ShipTestBase):
    options = {}

    def test_full_inventory_reaches_everything(self) -> None:
        solver = self.world.logic
        counts = {entry.name: 99 for entry in ITEMS.values()}
        counts.update(solver.starting_counts)
        result = solver.solve(counts)

        self.assertEqual(set(result.regions), set(REGIONS),
                         "some regions unreachable with a full inventory")
        self.assertEqual(set(result.checks), _all_checks(),
                         "some checks unreachable with a full inventory")

    def test_progression_only_reaches_everything(self) -> None:
        solver = self.world.logic
        counts = {entry.name: 99 for entry in ITEMS.values() if entry.progression}
        counts.update(solver.starting_counts)
        result = solver.solve(counts)

        self.assertEqual(set(result.checks), _all_checks(),
                         "progression classification is missing a logic-relevant item")

    def test_vanilla_layout_completable(self) -> None:
        """Sphere-walk the vanilla item layout: collecting each reachable
        check's vanilla item must eventually reach every check."""
        solver = self.world.logic
        vanilla_by_rc = {f"RC_{loc.name}": item.value for loc, item in vanilla_items.items()}

        counts = dict(solver.starting_counts)
        seen: set[str] = set()
        for _ in range(64):  # sphere cap; vanilla completes in ~28
            result = solver.solve(dict(counts))
            new = result.checks - seen
            if not new:
                break
            for rc in new:
                name = vanilla_by_rc.get(rc)
                if name:
                    counts[name] = counts.get(name, 0) + 1
            seen |= new

        self.assertEqual(seen, _all_checks(), "vanilla layout deadlocked")

    def test_non_progression_items_cannot_gate_logic(self) -> None:
        """The mirror of test_progression_only_reaches_everything: nothing AP
        classifies as filler/useful/trap may open a check. Those items never
        enter CollectionState.prog_items, so if one did gate logic, fill would
        be free to hide progression behind a check the player cannot reach —
        which is exactly what the bombchu refill packs used to do."""
        solver = self.world.logic
        baseline = solver.solve(dict(solver.starting_counts)).checks

        junk = sorted(
            member.value for member, data in item_data_table.items()
            if data.item_id is not None and not (data.classification & IC.progression)
        )
        counts = dict(solver.starting_counts)
        for name in junk:
            counts[name] = counts.get(name, 0) + 1

        extra = solver.solve(counts).checks - baseline
        if extra:  # narrow down to the offenders for a useful failure message
            culprits = [
                name for name in junk
                if solver.solve({**solver.starting_counts, name: 1}).checks - baseline
            ]
            self.fail(f"non-progression items opened {len(extra)} checks; "
                      f"logic-relevant but not classified progression: {culprits}")

    def test_explosives_require_a_bomb_bag(self) -> None:
        """CAN_USE_EXPLOSIVE must track what the player can actually detonate.
        Item_Give's bombchu/bomb refill branches fill the inventory slot but
        clamp ammo to CUR_CAPACITY(UPG_BOMB_BAG) — 0 without a bag — so a pack
        on its own is an icon with no ammo."""
        solver = self.world.logic

        def can_explode(*item_names: str) -> bool:
            counts = dict(solver.starting_counts)
            for name in item_names:
                counts[name] = counts.get(name, 0) + 1
            return CAN_USE_EXPLOSIVE(LogicContext(solver, counts))

        self.assertFalse(can_explode(), "explosives available with no items")
        for pack in ("Bombchu", "5 Bombchus", "10 Bombchus", "5 Bombs", "10 Bombs"):
            self.assertFalse(can_explode(pack), f"{pack} granted explosives without a Bomb Bag")
        for bag in ("Bomb Bag", "Big Bomb Bag", "Biggest Bomb Bag", "Progressive Bomb Bag"):
            self.assertTrue(can_explode(bag), f"{bag} did not grant explosives")
        # Blast Mask needs a shield to survive the blast; default options don't
        # shuffle it, so the starting Hero's Shield covers that half.
        self.assertTrue(can_explode("Blast Mask"), "Blast Mask + shield did not grant explosives")
        # Powder Kegs are deliberately NOT explosives: 2ship dropped
        # (HAS_ITEM(ITEM_POWDER_KEG) && CAN_BE_GORON) from CAN_USE_EXPLOSIVE in
        # PR #1577 because re-buying a keg for every wall is miserable. Kegs
        # still gate their own explicit HAS_ITEM(ITEM_POWDER_KEG) rules.
        # Goron Mask is required for the assertion to bite — the dropped clause
        # needed it, so a keg alone could never have satisfied it either way.
        self.assertFalse(can_explode("Powder Keg", "Goron Mask"),
                         "Powder Keg + Goron Mask granted explosives")

    def test_consumables_absent_when_option_off(self) -> None:
        solver = self.world.logic  # options = {} -> starting_consumables off
        ctx = LogicContext(solver, dict(solver.starting_counts))
        self.assertFalse(ctx.has_item("ITEM_DEKU_STICK"))
        self.assertFalse(ctx.has_item("ITEM_DEKU_NUT"))

    def test_monotone_in_items(self) -> None:
        solver = self.world.logic
        empty = solver.solve(dict(solver.starting_counts))
        full_counts = {entry.name: 99 for entry in ITEMS.values()}
        full_counts.update(solver.starting_counts)
        full = solver.solve(full_counts)

        self.assertLessEqual(set(empty.checks), set(full.checks))
        self.assertLessEqual(set(empty.regions), set(full.regions))


class TestStartingConsumables(MM2ShipTestBase):
    options = {"starting_consumables": True}

    def test_starting_consumables_are_in_logic(self) -> None:
        """GrantStartingItems hands out full Deku Sticks and Nuts on top of
        GetComputedStartingItems, and it runs before the C++ solver
        (OnFileCreate.cpp) and on AP connect (Archipelago.cpp) — so the solver
        has to assume them. ITEM_DEKU_STICK gates torch lighting and a long
        list of CanKillEnemy rules."""
        solver = self.world.logic
        ctx = LogicContext(solver, dict(solver.starting_counts))
        self.assertTrue(ctx.has_item("ITEM_DEKU_STICK"), "starting Deku Stick missing from logic")
        self.assertTrue(ctx.has_item("ITEM_DEKU_NUT"), "starting Deku Nut missing from logic")


class TestGeneratedDataShape(MM2ShipTestBase):
    options = {}

    def test_every_location_has_a_region(self) -> None:
        checks = _all_checks()
        for loc in Locations:
            if loc is Locations.VICTORY:
                continue
            self.assertIn(f"RC_{loc.name}", checks,
                          f"{loc.name} exists in Checks.cpp but no region defines it")


class TestSolveCacheScope(MM2ShipTestBase):
    options = {
        "shuffle_triforce_pieces": True,
        "triforce_pieces_max": 5,
        "triforce_pieces_required": 3,
    }

    def test_goal_items_do_not_invalidate_cache(self) -> None:
        """Triforce pieces are goal-only: collecting one must not throw away
        the cached solve (that cost was the fuzzer's slowdown), while a
        logic-relevant item must."""
        from BaseClasses import CollectionState

        self.assertNotIn("Piece of the Triforce", self.world.logic.logic_item_names)

        state = CollectionState(self.multiworld)
        self.world.logic.result_for(state)  # prime the cache
        cached = state.mm2ship_result[self.player]

        state.collect(self.world.create_item("Piece of the Triforce"), prevent_sweep=True)
        self.assertIs(state.mm2ship_result.get(self.player), cached,
                      "goal-only item invalidated the solve cache")

        state.collect(self.world.create_item("Hookshot"), prevent_sweep=True)
        self.assertNotIn(self.player, state.mm2ship_result,
                         "logic-relevant item failed to invalidate the solve cache")
