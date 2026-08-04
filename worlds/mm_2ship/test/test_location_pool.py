"""
Which checks become AP locations, where that isn't a plain on/off toggle:
the per-Spider-House Gold Skulltula subset, and the shop checks 2ship shuffles
even with Shuffle Shops off.
"""

from collections import Counter

from . import MM2ShipTestBase
from ..Enums import Locations
from ..LocationFilter import ALWAYS_SHUFFLED_SHOP_CHECKS, SKULLTULAS_BY_SCENE
from ..ShopLocations import shop_locations

SKULLTULAS_PER_HOUSE = 30
ALL_SKULLTULAS = frozenset().union(*(frozenset(keys) for keys in SKULLTULAS_BY_SCENE.values()))


class TestPartialSkulltulaShuffle(MM2ShipTestBase):
    """skulltula_shuffled picks how many of each house's 30 skulltulas are
    checks; the rest keep their own token, exactly like GeneratePools.cpp."""

    SHUFFLED = 7
    options = {
        "shuffle_gold_skulltulas": True,
        "skulltula_shuffled": SHUFFLED,
        # the whole point of a partial shuffle is that all 30 tokens per house
        # are still obtainable, so ask for all of them
        "skulltula_tokens_required": 30,
    }

    def _present_skulltulas(self) -> set[str]:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        return {key for key in ALL_SKULLTULAS if Locations[key].value in names}

    def test_only_the_chosen_skulltulas_are_locations(self) -> None:
        present = self._present_skulltulas()
        for scene, keys in SKULLTULAS_BY_SCENE.items():
            self.assertEqual(len(set(keys) & present), self.SHUFFLED,
                             f"{scene} has the wrong number of skulltula locations")
        self.assertEqual(self.world.skulltula_shuffled_locations, present)

    def test_pool_holds_one_token_per_shuffled_skulltula(self) -> None:
        counts = Counter(item.name for item in self.multiworld.itempool
                         if item.player == self.player)
        self.assertEqual(counts["Swamp Gold Skulltula Token"], self.SHUFFLED)
        self.assertEqual(counts["Ocean Gold Skulltula Token"], self.SHUFFLED)

    def test_unshuffled_skulltulas_still_grant_their_token(self) -> None:
        """They are not AP locations, so the solver has to hand out their
        vanilla token when reached — otherwise the Spider House rewards would
        need 30 tokens from a pool that only holds skulltula_shuffled."""
        self_granted = self.world.logic.disabled_check_vanilla
        for scene, keys in SKULLTULAS_BY_SCENE.items():
            granted = [key for key in keys if f"RC_{key}" in self_granted]
            self.assertEqual(len(granted), SKULLTULAS_PER_HOUSE - self.SHUFFLED,
                             f"{scene} self-grants the wrong number of tokens")
            for key in granted:
                self.assertIn("Gold Skulltula Token", self_granted[f"RC_{key}"])


class TestFullSkulltulaShuffle(MM2ShipTestBase):
    options = {
        "shuffle_gold_skulltulas": True,
        "skulltula_shuffled": SKULLTULAS_PER_HOUSE,
    }

    def test_every_skulltula_is_a_location(self) -> None:
        self.assertEqual(self.world.skulltula_shuffled_locations, ALL_SKULLTULAS)
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        missing = [key for key in ALL_SKULLTULAS if Locations[key].value not in names]
        self.assertFalse(missing, f"skulltulas missing as locations: {missing}")


class TestMinimumSkulltulaShuffle(MM2ShipTestBase):
    """One check per house with every token still required — the standard
    generation suite proves the seed is completable."""

    options = {
        "shuffle_gold_skulltulas": True,
        "skulltula_shuffled": 1,
        "skulltula_tokens_required": 30,
    }


class TestAlwaysShuffledShopChecks(MM2ShipTestBase):
    """GeneratePools.cpp shuffles the Curiosity Shop special item and both Bomb
    Shop bomb bags even with shops off — the first bomb bag is progression."""

    options = {"shuffle_shops": False}

    def test_always_shuffled_checks_exist(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        for key in ALWAYS_SHUFFLED_SHOP_CHECKS:
            self.assertIn(Locations[key].value, names,
                          f"{key} must be a location even with shuffle_shops off")

    def test_other_shop_checks_are_dropped(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        others = [loc for loc in shop_locations if loc.name not in ALWAYS_SHUFFLED_SHOP_CHECKS]
        self.assertTrue(others)
        for loc in others:
            self.assertNotIn(loc.value, names,
                             f"{loc.name} should be dropped with shuffle_shops off")

    def test_they_have_prices(self) -> None:
        """They are bought, not picked up, so logic needs a price for each."""
        for key in ALWAYS_SHUFFLED_SHOP_CHECKS:
            self.assertIn(f"RC_{key}", self.world.shop_prices)
