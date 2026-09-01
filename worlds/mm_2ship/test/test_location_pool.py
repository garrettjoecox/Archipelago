"""
Which checks become AP locations, where that isn't a plain on/off toggle:
the per-Spider-House Gold Skulltula subset, the shop checks 2ship shuffles even
with Shuffle Shops off, and the song checks under shuffle_songs = Vanilla.
"""

from collections import Counter

from . import MM2ShipTestBase
from ..Enums import Locations
from ..LocationFilter import (
    ALWAYS_SHUFFLED_SHOP_CHECKS, SKULLTULAS_BY_SCENE, SONG_LOCATION_ITEM_NAMES, SONG_LOCATION_KEYS,
)
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
        vanilla token when reached. Otherwise the Spider House rewards would
        need 30 tokens from a pool holding only skulltula_shuffled of them."""
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
    """One check per house with every token still required. The standard
    generation suite is what proves the seed stays completable."""

    options = {
        "shuffle_gold_skulltulas": True,
        "skulltula_shuffled": 1,
        "skulltula_tokens_required": 30,
    }


class TestNeverShuffledScenes(MM2ShipTestBase):
    """GeneratePools.cpp skips every SCENE_LAST_BS check outright. As AP
    locations the two Majora's Lair pots would sit past the point of no return,
    in the same region as the Victory event, where fill could hide progression."""

    options = {"shuffle_pot_drops": True}

    def test_majora_lair_pots_are_not_locations(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        for key in ("MOON_MAJORA_POT_01", "MOON_MAJORA_POT_02"):
            self.assertNotIn(Locations[key].value, names,
                             f"{key} is in SCENE_LAST_BS and must never be a location")

    def test_other_pots_still_are(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertIn(Locations["SWAMP_SPIDER_HOUSE_MAIN_ROOM_LOWER_POT_01"].value, names)


class TestAlwaysShuffledShopChecks(MM2ShipTestBase):
    """GeneratePools.cpp shuffles the Curiosity Shop special item and both Bomb
    Shop bomb bags even with shops off, because the first bag is progression."""

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


class TestSongsVanilla(MM2ShipTestBase):
    """shuffle_songs = Vanilla is GeneratePools.cpp skipping every RCTYPE_SONG
    check. They are not AP locations either, and the solver hands out their
    songs when the check is reached, the way the unshuffled game does."""

    options = {"shuffle_songs": "vanilla"}

    def test_song_checks_are_not_locations(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        for key in SONG_LOCATION_KEYS:
            self.assertNotIn(Locations[key].value, names,
                             f"{key} must not be a location with songs on Vanilla")

    def test_no_song_in_the_item_pool(self) -> None:
        pooled = sorted({item.name for item in self.multiworld.itempool
                         if item.player == self.player and item.name in SONG_LOCATION_ITEM_NAMES})
        self.assertFalse(pooled, f"vanilla songs still in the pool: {pooled}")

    def test_the_solver_self_grants_them(self) -> None:
        self_granted = self.world.logic.disabled_check_vanilla
        for key in SONG_LOCATION_KEYS:
            self.assertIn(f"RC_{key}", self_granted,
                          f"{key} is not a location, so the solver has to grant its song")


class TestSongsAnywhere(MM2ShipTestBase):
    """The default. Song checks are ordinary checks and their songs ordinary
    pool items, free to land anywhere."""

    options = {"shuffle_songs": "anywhere"}

    def test_song_checks_are_locations(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        for key in SONG_LOCATION_KEYS:
            self.assertIn(Locations[key].value, names)

    def test_songs_are_pooled_and_unconfined(self) -> None:
        pooled = {item.name for item in self.multiworld.itempool
                  if item.player == self.player and item.name in SONG_LOCATION_ITEM_NAMES}
        self.assertTrue(pooled, "no songs reached the item pool")
        # Nothing is pre-placed, so every song check is still open for the fill.
        for key in SONG_LOCATION_KEYS:
            self.assertFalse(
                self.multiworld.get_location(Locations[key].value, self.player).locked)
