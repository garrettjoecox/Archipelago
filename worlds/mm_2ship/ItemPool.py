from __future__ import annotations

import logging
from .Enums import Items
from typing import TYPE_CHECKING

from BaseClasses import ItemClassification as IC

logger = logging.getLogger("MM2SHIP")

from .PlacementConstraints import PLACEMENT_OPTION_BY_TYPE, START_WITH, placement_mode

if TYPE_CHECKING:
    from . import MM2ShipWorld


def _start_with_dungeon_items(world: "MM2ShipWorld") -> set[str]:
    """AP item names granted up front by the placement_* = Start With options."""
    from .LogicHelpersGen import DUNGEON_ITEMS

    names: set[str] = set()
    for item_type in PLACEMENT_OPTION_BY_TYPE:
        if placement_mode(world, item_type) == START_WITH:
            names.update(items[item_type] for items in DUNGEON_ITEMS.values())
    return names


def create_item_pool(world: "MM2ShipWorld") -> None:
    """
    Core item pool creation matching 2Ship's GeneratePools.cpp logic.

    This loops through all enabled locations and adds their vanilla items to the pool,
    then adds items that have no vanilla location (Hero's Shield, etc.).
    """
    from .Items import Items
    from .Enums import Locations
    from .VanillaItems import vanilla_items
    from .LocationData import LOCATION_RCTYPE
    from collections import Counter

    # Define map and compass items (excluded from pool if starting_maps_and_compasses is ON)
    # This includes dungeon maps/compasses AND Tingle maps
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
    # kind — 1/3/1/4 Small Keys, one Boss Key and 15 Stray Fairies per dungeon —
    # so GeneratePools' starting-item removal clears every copy from the pool.
    start_with_items = _start_with_dungeon_items(world)

    # Step 1: Add vanilla items from all enabled locations
    # This matches GeneratePools.cpp lines 28-153 where it loops through all checks
    # and adds their vanilla items to the item pool
    for location in world.multiworld.get_locations(world.player):
        # Convert location name back to enum
        try:
            loc_enum = Locations(location.name)
        except ValueError:
            continue  # Skip event locations or unknown locations

        # Look up the vanilla item for this location
        if loc_enum in vanilla_items:
            vanilla_item = vanilla_items[loc_enum]

            # Skip maps/compasses if starting with them
            # (The locations still exist, but the items are not in the pool)
            if world.options.starting_maps_and_compasses.value and vanilla_item in map_compass_items:
                continue

            # Skip Bunny Hood if starting with it
            if world.options.starting_bunny_hood.value and vanilla_item == Items.MASK_BUNNY:
                continue

            # Skip dungeon items the player starts with (placement_* = Start With)
            if vanilla_item.value in start_with_items:
                continue

            # Skip Ocarina if not shuffled (you start with it instead)
            if not world.options.shuffle_ocarina.value and vanilla_item == Items.OCARINA:
                continue

            # Skip Song of Time if not shuffled (you start with it instead —
            # mirrors GetComputedStartingItems + GeneratePools' starting-item
            # removal)
            if not world.options.shuffle_song_time.value and vanilla_item == Items.SONG_TIME:
                continue

            # Skip boss remains if not shuffled — those locations are pre-filled
            # with locked items and must not also appear in the random pool.
            if not world.options.shuffle_boss_remains.value and LOCATION_RCTYPE.get(loc_enum.name) == "RCTYPE_REMAINS":
                continue

            world.multiworld.itempool.append(world.create_item(vanilla_item.value))

    # Step 2: Add items with no vanilla location
    # These match GeneratePools.cpp lines 156-231

    # Add sword and shield if shuffled (line 158-159 in GeneratePools.cpp)
    # If not shuffled, these are given as starting items (see StartingItems.cpp)
    if world.options.shuffle_sword.value:
        world.multiworld.itempool.append(world.create_item("Progressive Sword"))
    if world.options.shuffle_shield.value:
        world.multiworld.itempool.append(world.create_item("Hero's Shield"))

    # Add boss souls if shuffled. The list comes from the generated item
    # groups so upstream soul additions flow through automatically.
    if world.options.shuffle_boss_souls.value:
        from .Items import item_name_groups
        for soul in sorted(item_name_groups["Boss Souls"]):
            # Skip Majora soul if triforce pieces are shuffled — the goal
            # doesn't require fighting Majora then.
            if soul == "Soul of Majora" and world.options.shuffle_triforce_pieces.value:
                continue
            world.multiworld.itempool.append(world.create_item(soul))

    # Add enemy souls if shuffled (generated group, same as above).
    if world.options.shuffle_enemy_souls.value:
        from .Items import item_name_groups
        for soul in sorted(item_name_groups["Enemy Souls"]):
            world.multiworld.itempool.append(world.create_item(soul))

    # Add clock shuffle items if shuffled, mirroring GeneratePools.cpp:
    # random mode uses the six concrete half-day clocks, ascending/descending
    # use six Progressive Time items. One copy is precollected as the
    # guaranteed starting time item (see MM2ShipWorld.generate_early), so its
    # pool copy is skipped here — the total granted is always six.
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

    # Add swim ability if shuffled
    if world.options.shuffle_swim.value:
        world.multiworld.itempool.append(world.create_item("Ability to Swim"))

    # Add ocarina buttons if shuffled
    if world.options.shuffle_ocarina_buttons.value:
        buttons = ["A Button", "C Down Button", "C Right Button", "C Left Button", "C Up Button"]
        for button in buttons:
            world.multiworld.itempool.append(world.create_item(button))

    # Add songs (without vanilla locations) if shuffled. Song of Time is NOT
    # added here: its copy comes from its vanilla location in Step 1, matching
    # GeneratePools.cpp.
    if world.options.shuffle_song_sun.value:
        world.multiworld.itempool.append(world.create_item("Sun's Song"))
    if world.options.shuffle_song_double_time.value:
        world.multiworld.itempool.append(world.create_item("Song of Double Time"))
    if world.options.shuffle_song_inverted_time.value:
        world.multiworld.itempool.append(world.create_item("Inverted Song of Time"))
    if world.options.shuffle_song_saria.value:
        world.multiworld.itempool.append(world.create_item("Saria's Song"))

    # Add a Tycoon's Wallet upgrade if shuffled. This is one more "Progressive Wallet"
    # on top of the two (Adult's, Giant's) already added from their vanilla locations
    # in Step 1 — the third copy converts to Tycoon's Wallet client-side once collected.
    if world.options.shuffle_tycoon_wallet.value:
        world.multiworld.itempool.append(world.create_item("Progressive Wallet"))

    # Add the Skeleton Key if shuffled. This is a standalone item on top of each
    # dungeon's own Small Keys already in the pool — collecting it instantly grants
    # the max Small Keys for every dungeon at once (see GiveItem.cpp's RI_SKELETON_KEY case).
    # Skipped when starting with Small Keys: it would have nothing left to unlock.
    if world.options.shuffle_skeleton_key.value and placement_mode(world, "small_key") != START_WITH:
        world.multiworld.itempool.append(world.create_item("Skeleton Key"))

    # Step 3: Trim stray fairies to the max count
    # This matches GeneratePools.cpp's removeAbleItemsInPool pass
    # IMPORTANT: Only count and trim items for THIS player
    item_counts = Counter(item.name for item in world.multiworld.itempool if item.player == world.player)

    # Stray fairies - trim to max count
    stray_fairy_items = [
        "Stone Tower Stray Fairy",
        "Great Bay Stray Fairy",
        "Snowhead Stray Fairy",
        "Woodfall Stray Fairy",
    ]
    max_fairies = world.options.stray_fairies_max.value
    for fairy_item in stray_fairy_items:
        while item_counts[fairy_item] > max_fairies:
            # Remove one instance of THIS PLAYER's item
            for item in world.multiworld.itempool:
                if item.name == fairy_item and item.player == world.player:
                    world.multiworld.itempool.remove(item)
                    item_counts[fairy_item] -= 1
                    break

    # Gold Skulltula tokens need no trim: skulltula_shuffled already decided how
    # many of each house's skulltulas are locations, and each contributes a token.

    # Step 3b: Rebalance Heart Pieces against starting health, mirroring
    # GeneratePools.cpp. Hearts you start with make the matching pieces
    # redundant, and starting below three hearts wants extras to climb back —
    # four pieces per heart either way. Heart capacity is logic-relevant
    # (CHECK_MAX_HP gates the Ghost Hut and Poe Sister checks), and Heart Pieces
    # are progression-classified here, so the surplus can't be trimmed away as
    # filler later; skipping this step would leave the pool visibly off.
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

    # Step 4: Add extra copies of items specified by the player
    for item_name, count in world.options.extra_items.items():
        for _ in range(count):
            world.multiworld.itempool.append(world.create_item(item_name))


def create_plentiful_and_trap_items(world: "MM2ShipWorld") -> None:
    """
    Apply plentiful items logic if enabled, add traps, then fill remaining with filler.
    Matches 2Ship's plentiful logic from GeneratePools.cpp lines 279-312.
    """
    # Plentiful items: duplicate major items if enabled
    if world.options.plentiful_items.value:
        plentiful_candidates = []

        # Only look at items for THIS player
        for item in world.multiworld.itempool:
            if item.player != world.player:
                continue

            # Skip triforce pieces (user specifies exact count)
            if item.name == "Piece of the Triforce":
                continue
            # Skip the Skeleton Key — it's powerful enough that only one copy should ever exist
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

            # Add based on classification
            if item.classification in (IC.progression, IC.useful):
                # Skip maps and compasses (they're IC.useful but we don't duplicate them)
                if "Map" not in item.name and "Compass" not in item.name and "Tingle Map" not in item.name:
                    plentiful_candidates.append(item.name)

        # Add duplicates
        for item_name in plentiful_candidates:
            world.multiworld.itempool.append(world.create_item(item_name))

    # Balance the pool to exactly the location count, filling by priority:
    # mandatory items first, then as many triforce pieces as fit within max, then
    # traps up to trap_amount, then junk filler for whatever is left. Triforce and
    # traps are both created here so the fill order is explicit.
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

    # Slots left for triforce + traps + filler once the mandatory items are placed.
    # (Base junk filler already in the pool is the lowest priority, so it doesn't
    # count as mandatory.)
    room = locations - _count(lambda i: not is_filler(i))
    if room < 0:
        raise OptionError(
            f"MM2Ship (player {world.player}): mandatory items exceed the {locations} "
            f"available locations by {-room}. Enable more shuffle options "
            f"(pots, grass, enemy drops, ...) or turn off plentiful_items."
        )

    # All of the items below are essentially fighting for left over slots. Start with most important (Triforce Hunt pieces) to least important (actual junk)
    # Do this instead of the previous solution because this will prevent failed generations due to OptionErrors if players set Triforce Pieces way higher than the amount of locations available
    # Triforce fills first
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
        # Set excess to useful
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

    # Traps fill next, up to trap_amount
    traps = min(world.options.trap_amount.value, room) if world.options.shuffle_traps.value else 0
    world.options.trap_amount.value = traps
    for _ in range(traps):
        world.multiworld.itempool.append(world.create_item(Items.TRAP.value))
    room -= traps

    # Junk filler takes whatever is left
    _trim(is_filler, _count(is_filler) - room)
    for _ in range(room - _count(is_filler)):
        world.multiworld.itempool.append(world.create_item(get_filler_item(world)))


def get_filler_item(world: "MM2ShipWorld") -> str:
    """
    Choose a filler item name. Prefers rupees and consumables.
    """
    filler_options = [
        "Junk",
    ]
    return world.random.choice(filler_options)
