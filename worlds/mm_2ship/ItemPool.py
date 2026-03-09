from __future__ import annotations

import logging
from .Enums import Items
from typing import TYPE_CHECKING

from BaseClasses import ItemClassification as IC

logger = logging.getLogger("MM2SHIP")

from .PlacementConstraints import START_WITH, dungeon_items_for_mode, placement_mode

if TYPE_CHECKING:
    from . import MM2ShipWorld


def create_item_pool(world: "MM2ShipWorld") -> None:
    """Build the item pool, mirroring 2Ship's GeneratePools.cpp."""
    from .Items import Items
    from .Enums import Locations
    from .VanillaItems import vanilla_items
    from collections import Counter

    # Tingle's maps count as maps here too, so starting_maps_and_compasses
    # takes them out of the pool alongside the dungeon ones.
    map_compass_items = {
        Items.GREAT_BAY_COMPASS,
        Items.GREAT_BAY_MAP,
        Items.SNOWHEAD_COMPASS,
        Items.SNOWHEAD_MAP,
        Items.STONE_TOWER_COMPASS,
        Items.STONE_TOWER_MAP,
        Items.WOODFALL_COMPASS,
        Items.WOODFALL_MAP,
        Items.TINGLE_MAP_CLOCK_TOWN,
        Items.TINGLE_MAP_GREAT_BAY,
        Items.TINGLE_MAP_ROMANI_RANCH,
        Items.TINGLE_MAP_SNOWHEAD,
        Items.TINGLE_MAP_STONE_TOWER,
        Items.TINGLE_MAP_WOODFALL,
    }

    # Dungeon items the player is handed on connect (placement_* = Start With).
    # GetComputedStartingItems grants exactly one per vanilla location of each
    # kind (1/3/1/4 Small Keys, one Boss Key and 15 Stray Fairies per dungeon,
    # plus the dungeon-less Clock Town one), so GeneratePools' starting-item
    # removal clears every copy from the pool.
    start_with_items = set(dungeon_items_for_mode(world, START_WITH))

    # Every enabled location contributes its vanilla item. Unfilled only: a
    # location pre-filled in Regions.py already holds what it hands out (a boss
    # warp when boss remains aren't shuffled, a dungeon item left at its vanilla
    # check, the Victory event), and that item must not also enter the pool.
    for location in world.multiworld.get_unfilled_locations(world.player):
        try:
            loc_enum = Locations(location.name)
        except ValueError:
            continue  # event location, or one that isn't ours

        if loc_enum in vanilla_items:
            vanilla_item = vanilla_items[loc_enum]

            # The player starts with each item skipped below, so it leaves the
            # pool while its location stays a location. Same as GeneratePools'
            # starting-item removal, which reads GetComputedStartingItems.
            if world.options.starting_maps_and_compasses.value and vanilla_item in map_compass_items:
                continue
            if world.options.starting_bunny_hood.value and vanilla_item == Items.MASK_BUNNY:
                continue
            if vanilla_item.value in start_with_items:
                continue
            if not world.options.shuffle_ocarina.value and vanilla_item == Items.OCARINA:
                continue
            if not world.options.shuffle_song_time.value and vanilla_item == Items.SONG_TIME:
                continue

            world.multiworld.itempool.append(world.create_item(vanilla_item.value))

    # From here on: items with no vanilla location of their own.

    # Unshuffled, these two are starting items instead (StartingItems.cpp).
    if world.options.shuffle_sword.value:
        world.multiworld.itempool.append(world.create_item("Progressive Sword"))
    if world.options.shuffle_shield.value:
        world.multiworld.itempool.append(world.create_item("Hero's Shield"))

    # Souls come from the generated item groups, so upstream additions flow
    # through without a code change here.
    if world.options.shuffle_boss_souls.value:
        from .Items import item_name_groups
        for soul in sorted(item_name_groups["Boss Souls"]):
            # A Triforce Hunt goal never requires fighting Majora.
            if soul == "Soul of Majora" and world.options.shuffle_triforce_pieces.value:
                continue
            world.multiworld.itempool.append(world.create_item(soul))

    if world.options.shuffle_enemy_souls.value:
        from .Items import item_name_groups
        for soul in sorted(item_name_groups["Enemy Souls"]):
            world.multiworld.itempool.append(world.create_item(soul))

    # Six clocks either way, mirroring GeneratePools.cpp: random mode uses the
    # six concrete half-days, ascending/descending six Progressive Time items.
    # generate_early precollects one as the guaranteed starting clock, so that
    # copy is skipped here to keep the total at six.
    if world.options.clock_shuffle.value:
        if world.options.clock_shuffle_progressive.value == 0:  # RO_CLOCK_SHUFFLE_RANDOM
            time_items = [
                "Time (Day 1)", "Time (Night 1)", "Time (Day 2)",
                "Time (Night 2)", "Time (Day 3)", "Time (Night 3)",
            ]
        else:
            time_items = ["Progressive Time"] * 6
        skipped_starting_clock = False
        for time_item in time_items:
            if not skipped_starting_clock and time_item == world.starting_clock_name:
                skipped_starting_clock = True
                continue
            world.multiworld.itempool.append(world.create_item(time_item))

    if world.options.shuffle_swim.value:
        world.multiworld.itempool.append(world.create_item("Ability to Swim"))

    if world.options.shuffle_ocarina_buttons.value:
        buttons = ["A Button", "C Down Button", "C Right Button", "C Left Button", "C Up Button"]
        for button in buttons:
            world.multiworld.itempool.append(world.create_item(button))

    # Song of Time is deliberately absent: it has a vanilla location, so its
    # copy already came from the loop above, matching GeneratePools.cpp.
    if world.options.shuffle_song_sun.value:
        world.multiworld.itempool.append(world.create_item("Sun's Song"))
    if world.options.shuffle_song_double_time.value:
        world.multiworld.itempool.append(world.create_item("Song of Double Time"))
    if world.options.shuffle_song_inverted_time.value:
        world.multiworld.itempool.append(world.create_item("Inverted Song of Time"))
    if world.options.shuffle_song_saria.value:
        world.multiworld.itempool.append(world.create_item("Saria's Song"))

    # A third "Progressive Wallet" on top of the Adult's and Giant's copies the
    # loop above already added. The client converts that third one to Tycoon's.
    if world.options.shuffle_tycoon_wallet.value:
        world.multiworld.itempool.append(world.create_item("Progressive Wallet"))

    # The Skeleton Key sits on top of each dungeon's own Small Keys: collecting
    # it grants every dungeon's maximum at once (GiveItem.cpp, RI_SKELETON_KEY).
    # Starting with Small Keys leaves it nothing to unlock, so it is skipped.
    if world.options.shuffle_skeleton_key.value and placement_mode(world, "small_key") != START_WITH:
        world.multiworld.itempool.append(world.create_item("Skeleton Key"))

    # Trim stray fairies down to the pool cap (GeneratePools' removeAbleItemsInPool).
    # The itempool is shared across the multiworld, hence the player filter here
    # and in every count below it.
    item_counts = Counter(item.name for item in world.multiworld.itempool if item.player == world.player)

    stray_fairy_items = [
        "Stone Tower Stray Fairy",
        "Great Bay Stray Fairy",
        "Snowhead Stray Fairy",
        "Woodfall Stray Fairy",
    ]
    max_fairies = world.options.stray_fairies_max.value
    for fairy_item in stray_fairy_items:
        while item_counts[fairy_item] > max_fairies:
            for item in world.multiworld.itempool:
                if item.name == fairy_item and item.player == world.player:
                    world.multiworld.itempool.remove(item)
                    item_counts[fairy_item] -= 1
                    break

    # Gold Skulltula tokens need no trim: skulltula_shuffled already decided how
    # many of each house's skulltulas are locations, and each contributes a token.

    # Rebalance Heart Pieces against starting health, mirroring GeneratePools.cpp:
    # four pieces per heart, added below three hearts and removed above.
    # Heart capacity is logic-relevant (CHECK_MAX_HP gates the Ghost Hut and Poe
    # Sister checks) so pieces are progression-classified, which means nothing
    # downstream would trim the surplus as filler.
    starting_health = world.options.starting_health.value
    if starting_health < 3:
        for _ in range(4 * (3 - starting_health)):
            world.multiworld.itempool.append(world.create_item("Heart Piece"))
    elif starting_health > 3:
        # C++ stops early when the pool runs out, so this is a best-effort trim.
        to_remove = 4 * (starting_health - 3)
        for item in [i for i in world.multiworld.itempool
                     if i.player == world.player and i.name == "Heart Piece"][:to_remove]:
            world.multiworld.itempool.remove(item)

    for item_name, count in world.options.extra_items.items():
        for _ in range(count):
            world.multiworld.itempool.append(world.create_item(item_name))


def create_plentiful_and_trap_items(world: "MM2ShipWorld") -> None:
    """Duplicate majors under plentiful_items, then top the pool up to the
    location count with triforce pieces, traps and filler."""
    if world.options.plentiful_items.value:
        plentiful_candidates = []

        for item in world.multiworld.itempool:
            if item.player != world.player:
                continue

            # Skipped below: items whose quantity is set by an option of its
            # own or load-bearing for logic, plus the Skeleton Key, which is
            # strong enough that a second copy would be absurd.
            if item.name == "Piece of the Triforce":
                continue
            if item.name == "Skeleton Key":
                continue
            if item.name == "Swamp Gold Skulltula Token":
                continue
            if item.name == "Ocean Gold Skulltula Token":
                continue
            if item.name == "Woodfall Stray Fairy":
                continue
            if item.name == "Snowhead Stray Fairy":
                continue
            if item.name == "Great Bay Stray Fairy":
                continue
            if item.name == "Stone Tower Stray Fairy":
                continue
            if item.name == "Heart Container":
                continue
            if item.name == "Heart Piece":
                continue

            if item.classification in (IC.progression, IC.useful):
                # Maps and compasses are useful but a second one does nothing.
                if "Map" not in item.name and "Compass" not in item.name and "Tingle Map" not in item.name:
                    plentiful_candidates.append(item.name)

        for item_name in plentiful_candidates:
            world.multiworld.itempool.append(world.create_item(item_name))

    # Balance the pool to exactly the location count. Mandatory items go in
    # first; everything after that is competing for the slots they leave, so
    # fill in priority order: triforce pieces, traps up to trap_amount, junk.
    # Clamping the counts to what fits beats failing generation on a player who
    # asked for more pieces than the seed has locations.
    from BaseClasses import ItemClassification
    from Options import OptionError

    locations = len(world.multiworld.get_unfilled_locations(world.player))
    is_filler = lambda i: i.classification == ItemClassification.filler

    def _count(pred) -> int:
        return sum(1 for i in world.multiworld.itempool if i.player == world.player and pred(i))

    def _trim(pred, budget: int) -> None:
        matches = [i for i in world.multiworld.itempool if i.player == world.player and pred(i)]
        world.random.shuffle(matches)
        for item in matches[:max(0, budget)]:
            world.multiworld.itempool.remove(item)

    # Junk already in the pool is the lowest priority of all, so it does not
    # count as mandatory here.
    room = locations - _count(lambda i: not is_filler(i))
    if room < 0:
        raise OptionError(
            f"MM2Ship (player {world.player}): mandatory items exceed the {locations} "
            f"available locations by {-room}. Enable more shuffle options "
            f"(pots, grass, enemy drops, ...) or turn off plentiful_items."
        )

    if world.options.shuffle_triforce_pieces.value:
        keep = min(world.options.triforce_pieces_max.value, room)
        if keep < 1:
            raise OptionError(
                f"MM2Ship (player {world.player}): triforce hunt is on but the "
                f"{locations} available locations are all taken by mandatory items, "
                f"leaving no room for triforce pieces. Enable more shuffle options "
                f"(pots, grass, enemy drops, ...) or turn off plentiful_items."
            )
        required = min(world.options.triforce_pieces_required.value, keep)
        pieces = [world.create_item(Items.TRIFORCE_PIECE.value) for _ in range(keep)]
        # Pieces past the required count can't gate anything.
        for piece in pieces[required:]:
            piece.classification = ItemClassification.useful
        world.multiworld.itempool.extend(pieces)
        if (keep, required) != (world.options.triforce_pieces_max.value,
                                world.options.triforce_pieces_required.value):
            logger.warning(
                "MM2Ship (player %s): %s locations, triforce max %s -> %s, required %s -> %s.",
                world.player, locations, world.options.triforce_pieces_max.value, keep,
                world.options.triforce_pieces_required.value, required)
        world.options.triforce_pieces_max.value = keep
        world.options.triforce_pieces_required.value = required
        room -= keep

    traps = min(world.options.trap_amount.value, room) if world.options.shuffle_traps.value else 0
    world.options.trap_amount.value = traps
    for _ in range(traps):
        world.multiworld.itempool.append(world.create_item(Items.TRAP.value))
    room -= traps

    _trim(is_filler, _count(is_filler) - room)
    for _ in range(room - _count(is_filler)):
        world.multiworld.itempool.append(world.create_item(get_filler_item(world)))


def get_filler_item(world: "MM2ShipWorld") -> str:
    """Junk is 2ship's only filler item; the list is here for when that changes."""
    filler_options = [
        "Junk",
    ]
    return world.random.choice(filler_options)
