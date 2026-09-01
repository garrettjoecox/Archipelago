"""
Option-based location filtering. Deliberately pure: no Archipelago imports.

Used by Regions.py to decide which AP locations exist, by generate_early to
filter location_name_to_id, and by LogicRuntime, where disabled checks still
self-grant their vanilla items when reachable, like the C++ solver.
"""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

from .Enums import Locations
from .LocationData import LOCATION_RCTYPE, LOCATION_SCENE
from .OptionData import RO_CHOICE_VALUES
from .VanillaItems import vanilla_items

if TYPE_CHECKING:
    from . import MM2ShipWorld

# C++ RandoCheckType -> the MM2ShipOptions attribute that enables it. A type
# absent from this dict is always active (RCTYPE_CHEST, RCTYPE_NPC,
# RCTYPE_STRAY_FAIRY, RCTYPE_HEART, RCTYPE_MINIGAME, and so on). Only plain
# on/off options belong here. RCTYPE_SONG and RCTYPE_REMAINS use three-way
# Choices and are handled separately.
RCTYPE_OPTION: dict[str, str] = {
    "RCTYPE_BARREL":      "shuffle_barrel_drops",
    "RCTYPE_BEEHIVE":     "shuffle_hive_drops",
    "RCTYPE_BUTTERFLY":   "shuffle_butterflies",
    "RCTYPE_COW":         "shuffle_cows",
    "RCTYPE_CRATE":       "shuffle_crate_drops",
    "RCTYPE_ENEMY_DROP":  "shuffle_enemy_drops",
    "RCTYPE_FREESTANDING":"shuffle_freestanding_items",
    "RCTYPE_FROG":        "shuffle_frogs",
    "RCTYPE_GRASS":       "shuffle_grass_drops",
    "RCTYPE_OWL":         "shuffle_owl_statues",
    "RCTYPE_POT":         "shuffle_pot_drops",
    # "RCTYPE_REMAINS":     "shuffle_boss_remains",
    "RCTYPE_SHOP":        "shuffle_shops",
    "RCTYPE_SKULL_TOKEN": "shuffle_gold_skulltulas",
    "RCTYPE_SNOWBALL":    "shuffle_snowball_drops",
    "RCTYPE_TINGLE_SHOP": "shuffle_tingle_shops",
    "RCTYPE_TREE":        "shuffle_tree_drops",
    "RCTYPE_WONDER_ITEM": "shuffle_wonder_items",
}

# Scenes GeneratePools.cpp skips outright, whatever the options say. Majora's
# boss room holds two pots upstream deliberately never shuffles: "determine if
# it's ok for these pots to be shuffled since we cannot return from here"
# (Regions/Moon.cpp). As AP locations they would sit past the point of no
# return, in the Victory event's own region, where fill could hide progression.
NEVER_SHUFFLED_SCENES: frozenset[str] = frozenset({"SCENE_LAST_BS"})

# Shop checks GeneratePools.cpp shuffles even with Shuffle Shops off: the
# Curiosity Shop's special item and the Bomb Shop's two Bomb Bags (the first
# one is progression, so it must be reachable through the pool).
ALWAYS_SHUFFLED_SHOP_CHECKS: frozenset[str] = frozenset({
    "BOMB_SHOP_ITEM_03",
    "BOMB_SHOP_ITEM_04_OR_CURIOSITY_SHOP_ITEM",
    "CURIOSITY_SHOP_SPECIAL_ITEM",
})

# RandoOptionSongShuffle ordinals, from the generated Types.h mirror.
SONG_LOCATIONS = RO_CHOICE_VALUES["RO_SONG_SHUFFLE_SONG_LOCATIONS"]
SONG_VANILLA = RO_CHOICE_VALUES["RO_SONG_SHUFFLE_VANILLA"]

SONG_LOCATION_KEYS: tuple[str, ...] = tuple(
    key for key, rctype in LOCATION_RCTYPE.items() if rctype == "RCTYPE_SONG"
)

# Port of PlacementConstraints.cpp's IsSongLocationItem(). Reading it off the
# check table means a song added or moved upstream needs no change here. Keyed
# on the item, and the extra songs have no vanilla check to be confined to.
SONG_LOCATION_ITEM_NAMES: frozenset[str] = frozenset(
    vanilla_items[Locations[key]].value
    for key in SONG_LOCATION_KEYS
    if Locations[key] in vanilla_items
)

# Every Gold Skulltula, grouped by Spider House scene: the population
# roll_skulltula_subset draws each house's checks from. Built in generated
# (enum) order so the draw is reproducible across machines.
SKULLTULAS_BY_SCENE: dict[str, list[str]] = {}
for _key, _rctype in LOCATION_RCTYPE.items():
    if _rctype == "RCTYPE_SKULL_TOKEN":
        SKULLTULAS_BY_SCENE.setdefault(LOCATION_SCENE[_key], []).append(_key)


def roll_skulltula_subset(per_house: int, seed: int) -> frozenset[str]:
    """Pick which Gold Skulltulas are checks, per Spider House.

    Mirrors the shuffle at the top of GeneratePools.cpp, which draws
    skulltula_shuffled of each house's skulltulas and leaves the rest vanilla.
    AP has to commit to that choice during worldgen, so the draw is seeded from
    a value that also rides in slot_data. Universal Tracker regenerates from
    slot_data alone and has to land on the same subset.
    """
    rng = Random(seed)
    chosen: set[str] = set()
    for scene in sorted(SKULLTULAS_BY_SCENE):
        names = SKULLTULAS_BY_SCENE[scene]
        chosen.update(names if per_house >= len(names) else rng.sample(names, per_house))
    return frozenset(chosen)


def location_should_be_included(world: "MM2ShipWorld", loc: Locations) -> bool:
    """Does this location exist under the current world options?

    Filtering goes by type: each location's C++ RandoCheckType (in
    LocationData.LOCATION_RCTYPE) maps to the option that controls it, which
    beats matching on name patterns and stays in step with C++.

    Three callers have to agree on the answer, so all of them come through
    here: generate_early filtering location_name_to_id, Regions.py filtering
    Location objects, and the solver self-granting a disabled check's vanilla
    item.

    False drops the AP Location outright, which also keeps its vanilla item out
    of the pool, since ItemPool builds from the locations that exist.
    """
    name = loc.name  # UPPER_SNAKE_CASE enum key

    if LOCATION_SCENE.get(name) in NEVER_SHUFFLED_SCENES:
        return False

    rctype = LOCATION_RCTYPE.get(name)

    # No controlling option means the type is always active. A few checks are
    # exempt anyway: GeneratePools.cpp shuffles them whatever the option says.
    option_name = RCTYPE_OPTION.get(rctype) if rctype else None
    if option_name is not None:
        option = getattr(world.options, option_name, None)
        if option is not None and not option.value:
            return name in ALWAYS_SHUFFLED_SHOP_CHECKS

    # Only Vanilla drops the song checks. Under Song Locations they all stay
    # checks, and the confinement happens at fill time instead.
    if rctype == "RCTYPE_SONG" and world.options.shuffle_songs.value == SONG_VANILLA:
        return False

    # Only skulltula_shuffled of each Spider House's 30 skulltulas are checks
    # (see roll_skulltula_subset). Dropping the rest here is what makes the
    # solver self-grant their vanilla token, exactly like they do in-game.
    if rctype == "RCTYPE_SKULL_TOKEN" and name not in world.skulltula_shuffled_locations:
        return False

    # Grass sub-exclusions, only reachable with shuffle_grass_drops on. Mirrors
    # how GeneratePools.cpp handles excluded junk-item checks.
    if rctype == "RCTYPE_GRASS":
        if world.options.exclude_termina_field_grass.value and name.startswith("TERMINA_FIELD_GRASS_"):
            return False
        if world.options.exclude_cow_grotto_grass.value and (
            "TERMINA_FIELD_COW_GROTTO_GRASS_" in name
            or "GREAT_BAY_COAST_COW_GROTTO_GRASS_" in name
        ):
            return False

    return True
