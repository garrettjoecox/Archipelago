from dataclasses import dataclass
from Options import (
    Choice,
    Toggle,
    Range,
    ItemDict,
    PerGameCommonOptions,
    StartInventoryPool,
    Visibility,
    OptionGroup,
)

# ---------------------------------------------------------------------------
# These options mirror the 2 Ship 2 Harkinian randomizer's own options
# (StaticData/Options.cpp + Menu.cpp). Numeric bounds, defaults and choice
# ordinals must match the C++ side — slot_data sends the raw values to the
# game — and are enforced against the generated OptionData tables by
# test/test_options.py. Intentional divergences are documented there.
# ---------------------------------------------------------------------------


class TrueNoLogic(Toggle):
    """
    Ignore logic entirely: no location has an access rule and generation may
    require items to be obtained in unintended ways (or be flat-out impossible
    to complete without cheats). Use at your own risk.

    This option is intentionally hidden from the website and the template
    yaml — add "true_no_logic: true" to your yaml by hand to use it. The host
    must also opt in by setting allow_true_no_logic: true under
    mm_2ship_options in their host.yaml, otherwise generation fails.
    """
    display_name = "True No Logic"
    visibility = Visibility.spoiler


class Logic(Choice):
    """
    Which logic the randomizer uses to guarantee every location is reachable.

    Glitchless: full reachability logic, generated directly from the 2ship
    randomizer's own region/logic definitions (including the three-day time
    system).
    Vanilla: the same reachability rules as glitchless (kept as a separate
    value because the game treats it as its own mode).
    No Logic / Nearly No Logic: no access rules; anything can be anywhere.
    These two are host-gated the same way as True No Logic (see above).
    """
    display_name = "Logic"
    # Values mirror RandoOptionLogic in Types.h — do not reorder.
    option_glitchless = 0
    option_no_logic = 1
    option_nearly_no_logic = 2
    option_vanilla = 3
    default = 0  # RO_LOGIC_GLITCHLESS


class AccessDungeons(Choice):
    """
    What entering each of the four dungeons requires.

    Form and Song: both the matching transformation mask and the matching song
    (vanilla behavior).
    Form or Song: either one is enough.
    Form Only / Song Only: exactly that requirement.
    Open: dungeons have no entry requirement.
    """
    display_name = "Dungeon Access"
    option_form_and_song = 0
    option_form_or_song = 1
    option_form_only = 2
    option_song_only = 3
    option_open = 4
    default = 0  # RO_ACCESS_DUNGEONS_FORM_AND_SONG


class AccessMajoraMasksCount(Range):
    """
    How many of the 20 regular masks are needed (in addition to the remains
    requirement below) to enter Majora's Lair and fight Majora.
    """
    display_name = "Majora Access Masks Required"
    range_start = 0
    range_end = 20
    default = 0


class AccessMajoraRemainsCount(Range):
    """
    How many Boss Remains are needed (in addition to the masks requirement
    above) to enter Majora's Lair and fight Majora.
    """
    display_name = "Majora Access Remains Required"
    range_start = 0
    range_end = 4
    default = 0


class AccessMoonMasksCount(Range):
    """
    How many of the 20 regular masks are needed (in addition to the remains
    requirement below) to reach the Moon.
    """
    display_name = "Moon Access Masks Required"
    range_start = 0
    range_end = 20
    default = 0


class AccessMoonRemainsCount(Range):
    """
    How many Boss Remains are needed, together with the Oath to Order and the
    masks requirement above, to summon the giants and reach the Moon.
    Vanilla is 4.
    """
    display_name = "Moon Access Remains Required"
    range_start = 0
    range_end = 4
    default = 4


class AccessTrials(Choice):
    """
    What each of the four Moon Trials requires to enter.

    20 Masks: increasing regular-mask counts per trial (2, 6, 12, then all 20),
    like the vanilla moon children.
    Remains: each trial requires its matching Boss Remains.
    Forms: each trial requires its matching transformation mask.
    Open: trials have no requirement.
    """
    display_name = "Trials Access"
    option_20_masks = 0
    option_remains = 1
    option_forms = 2
    option_open = 3
    default = 0  # RO_ACCESS_TRIALS_20_MASKS


class ClockShuffle(Toggle):
    """
    Shuffle six Clock items into the pool. Each half-day (Day 1, Night 1, ...)
    is only playable once you own its Clock; time skips forward over half-days
    you don't own yet. You always start with one Clock so some half-day is
    playable. Logic accounts for which half-days you own.
    """
    display_name = "Clock Shuffle"
    default = 0  # RO_GENERIC_OFF


class ClockShuffleProgressive(Choice):
    """
    How the six shuffled Clocks are handed out.

    Randomized: each Clock item unlocks one specific half-day.
    Ascending: Progressive Time items unlock half-days in order
    (Day 1, Night 1, Day 2, ...).
    Descending: Progressive Time items unlock half-days in reverse order
    (Night 3 first).
    """
    display_name = "Clock Shuffle Progressive"
    # Values come from RO_CLOCK_SHUFFLE_* in Types.h
    option_randomized = 0
    option_ascending = 1
    option_descending = 2
    default = 0  # RO_CLOCK_SHUFFLE_RANDOM


class ClockTerminalTime(Range):
    """
    When the Final Hours countdown begins (minutes after midnight, 0-359, i.e.
    00:00 to 05:59 on the final day). With Clock Shuffle on, running out of
    owned half-days drops you into the Final Hours; this controls how much
    time then remains before the moon crashes. Vanilla Final Hours is 350
    (05:50).
    """
    display_name = "Final Hours Start Time"
    range_start = 0
    range_end = 359
    default = 350


class ExcludeTerminaFieldGrass(Toggle):
    """
    Exclude Termina Field grass checks from the location pool.
    Only applies when Shuffle Grass Drops is enabled.
    Does not exclude Termina Field grotto grass.
    """
    display_name = "Exclude Termina Field Grass"
    default = 0


class ExcludeCowGrottoGrass(Toggle):
    """
    Exclude cow grotto grass checks from the location pool.
    Only applies when Shuffle Grass Drops is enabled.
    Excludes 72 Termina Field Cow Grotto grass and 72 Great Bay Cow Grotto
    grass (144 total).
    """
    display_name = "Exclude Cow Grotto Grass"
    default = 0


class HintsBossRemains(Toggle):
    """The guard recruitment posters around Clock Town list where the Boss Remains are."""
    display_name = "Hints: Boss Remains"
    default = 0


class HintsGossipStones(Toggle):
    """Each Gossip Stone gives a static hint about the contents of a random location."""
    display_name = "Hints: Gossip Stones"
    default = 0


class HintsGossipStoneStrength(Range):
    """
    How strongly Gossip Stone hints are weighted toward important items and
    checks. At 0 every check is equally likely; at 100 the full item/check
    weighting applies. Only affects the Gossip Stone hints above.
    """
    display_name = "Hints: Gossip Stone Strength"
    range_start = 0
    range_end = 100
    default = 50


class HintsHookshot(Toggle):
    """The Zora in Great Bay Coast, near Pirates' Fortress, hints where the Hookshot is."""
    display_name = "Hints: Hookshot"
    default = 0


class HintsOathToOrder(Toggle):
    """
    Once you meet the Moon access requirements, Skull Kid on the Clock Tower
    rooftop hints where the Oath to Order is.
    """
    display_name = "Hints: Oath to Order"
    default = 0


class HintsPurchaseable(Toggle):
    """
    Gossip Stones offer their hint for a rupee cost instead of for free. The
    price scales from 10 to 250 rupees depending on how many checks remain, and
    the hint is guaranteed to be a check you have not obtained yet.
    """
    display_name = "Hints: Purchaseable"
    default = 0


class HintsSongOfSoaring(Toggle):
    """Hints the location of the Song of Soaring at its vanilla location."""
    display_name = "Hints: Song of Soaring"
    default = 0


class HintsSpiderHouses(Toggle):
    """
    Hint the Spider House rewards. The Swamp Spider House reward is hinted at the
    man's usual spot inside the Swamp Spider House; the Ocean Spider House reward
    is hinted in South Clock Town on Day 1, by the man on the scaffolding.
    """
    display_name = "Hints: Spider Houses"
    default = 0


class HintsBankSign(Toggle):
    """The sign next to the Bank in West Clock Town hints at the bank's Piece of Heart reward."""
    display_name = "Hints: Bank Sign"
    default = 0


class HintsTransformations(Toggle):
    """
    The sign near the Business Scrub in South Clock Town reveals where the
    transformation masks (Deku, Goron, Zora) are. Excludes the Fierce Deity mask.
    """
    display_name = "Hints: Transformations"
    default = 0


class PlacementSmallKeys(Choice):
    """
    Where each dungeon's Small Keys may be placed.

    Anywhere: Small Keys can be placed at any location, including other
    players' worlds.
    Own Dungeon: each dungeon's Small Keys are confined to locations within
    that same dungeon.
    """
    display_name = "Placement: Small Keys"
    option_anywhere = 0
    option_own_dungeon = 1
    default = 0  # RO_DUNGEON_ITEM_ANYWHERE


class PlacementBossKeys(Choice):
    """
    Where each dungeon's Boss Key may be placed.

    Anywhere: Boss Keys can be placed at any location, including other
    players' worlds.
    Own Dungeon: each dungeon's Boss Key is confined to locations within that
    same dungeon.
    """
    display_name = "Placement: Boss Keys"
    option_anywhere = 0
    option_own_dungeon = 1
    default = 0  # RO_DUNGEON_ITEM_ANYWHERE


class PlacementStrayFairies(Choice):
    """
    Where each dungeon's Stray Fairies may be placed. The Clock Town stray
    fairy is unaffected.

    Anywhere: Stray Fairies can be placed at any location, including other
    players' worlds.
    Own Dungeon: each dungeon's Stray Fairies are confined to locations within
    that same dungeon.
    """
    display_name = "Placement: Stray Fairies"
    option_anywhere = 0
    option_own_dungeon = 1
    default = 0  # RO_DUNGEON_ITEM_ANYWHERE


class PlentifulItems(Toggle):
    """
    Add a duplicate of most progression and useful items to the pool, making
    key items easier to come by. Junk is trimmed to make room; count-based
    items (Stray Fairies, Skulltula Tokens, Triforce Pieces, hearts) are not
    duplicated.
    """
    display_name = "Plentiful Items"
    default = 0


class PurchaseInfiniteRupees(Toggle):
    """
    Rupees sold in shops can be bought any number of times per cycle, instead
    of going out of stock after one purchase. The Archipelago check for that
    shop slot is still sent only once.
    """
    display_name = "Purchase Infinite Rupees"
    default = 0


class ShuffleBarrelDrops(Toggle):
    """Shuffle the items dropped by breakable barrels into the location pool."""
    display_name = "Shuffle Barrel Drops"
    default = 0


class ShuffleButterflies(Toggle):
    """
    Approaching a swarm of butterflies grants a shuffled check. These swarms
    grant nothing in the vanilla game, so this purely adds locations.
    """
    display_name = "Shuffle Butterflies"
    default = 0


class ShuffleBossRemains(Toggle):
    """
    Shuffle the four Boss Remains into the item pool. When disabled, each boss
    still grants its own Remains.
    """
    display_name = "Shuffle Boss Remains"
    default = 0


class ShuffleBossSouls(Toggle):
    """
    Shuffle the five Boss Souls into the pool. A boss does not appear (and so
    cannot be fought) until you have found its soul.
    """
    display_name = "Shuffle Boss Souls"
    default = 0


class ShuffleCows(Toggle):
    """Playing Epona's Song to cows grants shuffled checks."""
    display_name = "Shuffle Cows"
    default = 0


class ShuffleCrateDrops(Toggle):
    """Shuffle the items dropped by breakable crates into the location pool."""
    display_name = "Shuffle Crate Drops"
    default = 0


class ShuffleEnemyDrops(Toggle):
    """Shuffle the first drop from each non-boss enemy into the location pool."""
    display_name = "Shuffle Enemy Drops"
    default = 0


class ShuffleEnemySouls(Toggle):
    """
    Shuffle Enemy Souls into the pool. Each regular enemy type is immune to
    damage until you have found its soul, which can gate the checks behind it.
    """
    display_name = "Shuffle Enemy Souls"
    default = 0


class ShuffleFreestandingItems(Toggle):
    """Shuffle freestanding items (hearts, rupees, arrows, ...) into the location pool."""
    display_name = "Shuffle Freestanding Items"
    default = 0


class ShuffleFrogs(Toggle):
    """Returning the five Frog Choir frogs grants shuffled checks."""
    display_name = "Shuffle Frogs"
    default = 0


class ShuffleHiveDrops(Toggle):
    """Shooting down beehives grants shuffled checks."""
    display_name = "Shuffle Hive Drops"
    default = 0


class ShuffleGoldSkulltulas(Toggle):
    """Gold Skulltulas drop shuffled checks instead of their tokens."""
    display_name = "Shuffle Gold Skulltulas"
    default = 0


class ShuffleGrassDrops(Toggle):
    """Shuffle the items dropped by cutting grass into the location pool."""
    display_name = "Shuffle Grass Drops"
    default = 0


class ShuffleOcarina(Toggle):
    """Shuffle the Ocarina into the item pool. If disabled, you start with an Ocarina."""
    display_name = "Shuffle Ocarina"
    default = 0


class ShuffleOcarinaButtons(Toggle):
    """
    Shuffle the five ocarina buttons into the pool. Songs can only be played
    once you have found the buttons their notes use.
    """
    display_name = "Shuffle Ocarina Buttons"
    default = 0


class ShuffleOwlStatues(Toggle):
    """
    Activating an owl statue grants a shuffled check, and warp-song access to
    each owl is granted by finding its matching Owl Statue item.
    """
    display_name = "Shuffle Owl Statues"
    default = 0


class ShufflePotDrops(Toggle):
    """Shuffle the items dropped by breakable pots into the location pool."""
    display_name = "Shuffle Pot Drops"
    default = 0


class ShuffleShield(Toggle):
    """Shuffle a shield into the item pool. If disabled, you start with a Hero's Shield."""
    display_name = "Shuffle Shield"
    default = 0


class ShuffleShops(Toggle):
    """
    Shop inventories sell shuffled checks. Prices are randomized (0-200
    rupees), so wallet upgrades may be logically required for expensive slots.
    """
    display_name = "Shuffle Shops"
    default = 0


class ShuffleSkeletonKey(Toggle):
    """
    Add a Skeleton Key into the pool. Collecting it instantly grants the max
    number of Small Keys for every dungeon (Woodfall 1, Snowhead 3, Great Bay
    1, Stone Tower 4), in addition to each dungeon's own Small Keys already in
    the pool.
    """
    display_name = "Shuffle Skeleton Key"
    default = 0


class ShuffleSnowballDrops(Toggle):
    """Shuffle the items dropped by large snowballs into the location pool."""
    display_name = "Shuffle Snowball Drops"
    default = 0


class ShuffleSongDoubleTime(Toggle):
    """Shuffle the Song of Double Time into the pool. If disabled, you start with it."""
    display_name = "Shuffle Song of Double Time"
    default = 0


class ShuffleSongInvertedTime(Toggle):
    """Shuffle the Inverted Song of Time into the pool. If disabled, you start with it."""
    display_name = "Shuffle Inverted Song of Time"
    default = 0


class ShuffleSongSaria(Toggle):
    """
    Shuffle Saria's Song into the item pool. Playing it reveals a hint to a
    reachable, not-yet-found item, preferring your in-game priority-items list
    and otherwise a random reachable major item or mask. It is one-time use:
    the song is consumed once played.
    """
    display_name = "Shuffle Saria's Song"
    default = 0


class ShuffleSongSun(Toggle):
    """Shuffle the Sun's Song into the item pool."""
    display_name = "Shuffle Sun's Song"
    default = 0


class ShuffleSongTime(Toggle):
    """
    Shuffle the Song of Time into the item pool. If disabled, you start with
    the Song of Time. Be aware: without it you cannot reset to Day 1, so it
    gates most of the game.
    """
    display_name = "Shuffle Song of Time"
    default = 0


class ShuffleSword(Toggle):
    """Shuffle a sword upgrade into the item pool. If disabled, you start with the Kokiri Sword."""
    display_name = "Shuffle Sword"
    default = 0


class ShuffleSwim(Toggle):
    """
    Shuffle the ability to swim into the item pool. Until it is found, entering
    the swim state or submerging into deep water respawns Link (all forms,
    Zora included).
    """
    display_name = "Shuffle Swim"
    default = 0


class ShuffleTingleShops(Toggle):
    """Tingle's map purchases are shuffled checks."""
    display_name = "Shuffle Tingle Maps"
    default = 0


class ShuffleTraps(Toggle):
    """Add trapped items to the pool. Trap behavior can be tweaked in-game under Rando > General."""
    display_name = "Shuffle Traps"
    default = 0


class TrapAmount(Range):
    """How many Traps are shuffled into the item pool."""
    display_name = "Trap Amount"
    range_start = 1
    range_end = 100
    default = 5


class ShuffleTreeDrops(Toggle):
    """Shuffle the items dropped by shaking trees into the location pool."""
    display_name = "Shuffle Tree Drops"
    default = 0


class ShuffleWonderItems(Toggle):
    """
    Shuffle the game's hidden "wonder item" drops into the location pool —
    invisible rupees and the item clusters that appear when you strike an
    unmarked trigger, such as the Termina Field walls and the spider houses.
    """
    display_name = "Shuffle Wonder Items"
    default = 0


class ShuffleTriforcePieces(Toggle):
    """
    Triforce Hunt: shuffle Triforce Pieces into the multiworld and win by
    collecting the required number (the game completes automatically). Majora
    does not need to be defeated.
    """
    display_name = "Triforce Hunt"
    default = 0


class TriforcePiecesMax(Range):
    """
    How many Triforce Pieces are in the item pool. Only applies when Triforce
    Hunt is on. If there are more pieces than free locations, generation fails
    with a clear error — enable more shuffle options to make room.
    """
    display_name = "Triforce Pieces in Pool"
    range_start = 1
    range_end = 1000
    default = 15


class TriforcePiecesRequired(Range):
    """
    How many Triforce Pieces are needed to win. Only applies when Triforce
    Hunt is on. Values above Triforce Pieces in Pool are clamped down to it.
    """
    display_name = "Triforce Pieces Required"
    range_start = 1
    range_end = 1000
    default = 15


class SkulltulaTokensMax(Range):
    """
    Maximum Gold Skulltula tokens of each type (Swamp, Ocean) that can appear
    in the item pool. Only applies when Shuffle Gold Skulltulas is on.
    """
    display_name = "Skulltula Tokens in Pool"
    range_start = 1
    range_end = 30
    default = 30


class SkulltulaTokensRequired(Range):
    """
    Minimum Gold Skulltula tokens needed to obtain each Spider House reward.
    Only applies when Shuffle Gold Skulltulas is on. Values above Skulltula
    Tokens in Pool are clamped down to it.
    """
    display_name = "Skulltula Tokens Required"
    range_start = 1
    range_end = 30
    default = 30


class StrayFairiesMax(Range):
    """
    Maximum Stray Fairies per dungeon that can appear in the item pool.
    """
    display_name = "Stray Fairies in Pool"
    range_start = 1
    range_end = 15
    default = 15


class StrayFairiesRequired(Range):
    """
    Minimum Stray Fairies needed to obtain the corresponding Great Fairy
    reward. Does not affect the Clock Town fairy. Values above Stray Fairies
    in Pool are clamped down to it.
    """
    display_name = "Stray Fairies Required"
    range_start = 1
    range_end = 15
    default = 15


class StartingBunnyHood(Toggle):
    """Start with the Bunny Hood. The Bunny Hood will not be in the item pool."""
    display_name = "Starting Bunny Hood"
    default = 0


class StartingConsumables(Toggle):
    """Start with full Deku Sticks and Deku Nuts (ammo filled to your bag capacity)."""
    display_name = "Starting Consumables"
    default = 0


class StartingHealth(Range):
    """How many hearts you start with."""
    display_name = "Starting Health"
    range_start = 1
    range_end = 20
    default = 3


class StartingMapsAndCompasses(Toggle):
    """
    Start with every dungeon map and compass (Tingle's maps included). They
    are removed from the item pool.
    """
    display_name = "Starting Maps and Compasses"
    default = 0


class StartingRupees(Range):
    """
    Whether you start with a full wallet. The game reads this as a simple
    on/off flag: any value above 0 fills your rupees to your starting wallet's
    capacity (99 with the base wallet), while 0 starts you with none. The exact
    number is not a literal starting rupee count.

    Note: the 2ship default is 0 (off); this option defaults to 99 (on, a full
    base wallet) as an Archipelago quality-of-life divergence.
    """
    display_name = "Starting Rupees"
    range_start = 0
    range_end = 500
    default = 99


class ShuffleTycoonWallet(Toggle):
    """
    Add a third wallet upgrade into the pool (5000 rupee capacity), on top of
    the Adult's and Giant's Wallet upgrades already in the pool.
    """
    display_name = "Shuffle Tycoon's Wallet"
    default = 0


class ExtraItems(ItemDict):
    """
    Add extra copies of items into the pool on top of what is already there.
    For example, "Goron Mask: 2" adds two more Goron Masks, giving three total.
    Items with dedicated count options (Stray Fairies, Skulltula Tokens,
    Triforce Pieces, Traps) should use those options instead.
    """
    verify_item_name = True
    display_name = "Extra Items"


# -----------------------------
# Per-game options dataclass
# -----------------------------

@dataclass
class MM2ShipOptions(PerGameCommonOptions):
    # -----------------------------
    # Generation
    # -----------------------------
    true_no_logic: TrueNoLogic
    logic: Logic

    # -----------------------------
    # Randomizer Settings
    # -----------------------------
    access_dungeons: AccessDungeons
    access_majora_masks_count: AccessMajoraMasksCount
    access_majora_remains_count: AccessMajoraRemainsCount
    access_moon_masks_count: AccessMoonMasksCount
    access_moon_remains_count: AccessMoonRemainsCount
    access_trials: AccessTrials

    placement_small_keys: PlacementSmallKeys
    placement_boss_keys: PlacementBossKeys
    placement_stray_fairies: PlacementStrayFairies

    plentiful_items: PlentifulItems
    purchase_infinite_rupees: PurchaseInfiniteRupees

    shuffle_triforce_pieces: ShuffleTriforcePieces
    triforce_pieces_max: TriforcePiecesMax
    triforce_pieces_required: TriforcePiecesRequired

    skulltula_tokens_max: SkulltulaTokensMax
    skulltula_tokens_required: SkulltulaTokensRequired

    stray_fairies_max: StrayFairiesMax
    stray_fairies_required: StrayFairiesRequired

    shuffle_traps: ShuffleTraps
    trap_amount: TrapAmount

    # -----------------------------
    # Starting Stuff
    # -----------------------------
    starting_health: StartingHealth
    starting_rupees: StartingRupees
    starting_consumables: StartingConsumables
    starting_maps_and_compasses: StartingMapsAndCompasses
    starting_bunny_hood: StartingBunnyHood

    # -----------------------------
    # Item Shuffles
    # -----------------------------
    shuffle_sword: ShuffleSword
    shuffle_shield: ShuffleShield
    shuffle_ocarina: ShuffleOcarina
    shuffle_ocarina_buttons: ShuffleOcarinaButtons
    shuffle_swim: ShuffleSwim
    shuffle_skeleton_key: ShuffleSkeletonKey
    shuffle_tycoon_wallet: ShuffleTycoonWallet

    shuffle_song_time: ShuffleSongTime
    shuffle_song_double_time: ShuffleSongDoubleTime
    shuffle_song_inverted_time: ShuffleSongInvertedTime
    shuffle_song_saria: ShuffleSongSaria
    shuffle_song_sun: ShuffleSongSun

    clock_shuffle: ClockShuffle
    clock_shuffle_progressive: ClockShuffleProgressive
    clock_terminal_time: ClockTerminalTime

    # -----------------------------
    # Location Shuffle
    # -----------------------------
    exclude_termina_field_grass: ExcludeTerminaFieldGrass
    exclude_cow_grotto_grass: ExcludeCowGrottoGrass

    shuffle_shops: ShuffleShops
    shuffle_tingle_shops: ShuffleTingleShops
    shuffle_owl_statues: ShuffleOwlStatues
    shuffle_gold_skulltulas: ShuffleGoldSkulltulas
    shuffle_frogs: ShuffleFrogs
    shuffle_cows: ShuffleCows

    shuffle_grass_drops: ShuffleGrassDrops
    shuffle_pot_drops: ShufflePotDrops
    shuffle_crate_drops: ShuffleCrateDrops
    shuffle_barrel_drops: ShuffleBarrelDrops
    shuffle_freestanding_items: ShuffleFreestandingItems
    shuffle_snowball_drops: ShuffleSnowballDrops
    shuffle_tree_drops: ShuffleTreeDrops
    shuffle_enemy_drops: ShuffleEnemyDrops
    shuffle_butterflies: ShuffleButterflies
    shuffle_hive_drops: ShuffleHiveDrops
    shuffle_wonder_items: ShuffleWonderItems

    shuffle_boss_remains: ShuffleBossRemains
    shuffle_boss_souls: ShuffleBossSouls
    shuffle_enemy_souls: ShuffleEnemySouls

    # -----------------------------
    # Hints
    # -----------------------------
    hints_boss_remains: HintsBossRemains
    hints_oath_to_order: HintsOathToOrder
    hints_gossip_stones: HintsGossipStones
    hints_purchaseable: HintsPurchaseable
    hints_hookshot: HintsHookshot
    hints_song_of_soaring: HintsSongOfSoaring
    hints_spider_houses: HintsSpiderHouses
    hints_bank_sign: HintsBankSign
    hints_transformations: HintsTransformations
    hints_gossip_stone_strength: HintsGossipStoneStrength

    extra_items: ExtraItems

    # -----------------------------
    # AP common
    # -----------------------------
    start_inventory_from_pool: StartInventoryPool

# -----------------------------
# Option groups (UI organization)
# -----------------------------

mm2ship_option_groups = [
    OptionGroup("Generation", [
        Logic,
        TrueNoLogic,
    ]),

    OptionGroup("Randomizer Settings", [
        # access / gating
        AccessDungeons,
        AccessMajoraMasksCount,
        AccessMajoraRemainsCount,
        AccessMoonMasksCount,
        AccessMoonRemainsCount,
        AccessTrials,

        # dungeon item placement
        PlacementSmallKeys,
        PlacementBossKeys,
        PlacementStrayFairies,

        # core logic + density
        PlentifulItems,
        ExtraItems,
        PurchaseInfiniteRupees,

        # goal / endgame
        ShuffleTriforcePieces,
        TriforcePiecesMax,
        TriforcePiecesRequired,

        # collectibles requirements/caps
        SkulltulaTokensMax,
        SkulltulaTokensRequired,
        StrayFairiesMax,
        StrayFairiesRequired,

        # traps
        ShuffleTraps,
        TrapAmount,
    ]),

    OptionGroup("Starting Stuff", [
        StartingBunnyHood,
        StartingConsumables,
        StartingMapsAndCompasses,
        StartingHealth,
        StartingRupees,
    ]),

    OptionGroup("Item Shuffles", [
        # items/abilities/gear/songs/buttons themselves
        ShuffleSword,
        ShuffleShield,
        ShuffleOcarina,

        ShuffleOcarinaButtons,
        ShuffleSwim,
        ShuffleSkeletonKey,
        ShuffleTycoonWallet,

        ShuffleSongTime,
        ShuffleSongDoubleTime,
        ShuffleSongInvertedTime,
        ShuffleSongSaria,
        ShuffleSongSun,

        # clock behavior/settings
        ClockShuffle,
        ClockShuffleProgressive,
        ClockTerminalTime,

        # souls
        ShuffleBossSouls,
        ShuffleEnemySouls,
    ]),

    OptionGroup("Location Shuffles", [
        # exclusions belong with the location pools they affect
        ExcludeTerminaFieldGrass,
        ExcludeCowGrottoGrass,

        # “shuffle checks/drops/locations”
        ShuffleBossRemains,

        ShuffleShops,
        ShuffleTingleShops,
        ShuffleOwlStatues,
        ShuffleGoldSkulltulas,
        ShuffleFrogs,
        ShuffleCows,

        ShuffleGrassDrops,
        ShufflePotDrops,
        ShuffleCrateDrops,
        ShuffleBarrelDrops,
        ShuffleFreestandingItems,
        ShuffleSnowballDrops,
        ShuffleTreeDrops,
        ShuffleEnemyDrops,
        ShuffleButterflies,
        ShuffleHiveDrops,
        ShuffleWonderItems,
    ]),

    OptionGroup("Hints", [
        # hints are location/knowledge distribution
        HintsBossRemains,
        HintsOathToOrder,
        HintsGossipStones,
        HintsPurchaseable,
        HintsHookshot,
        HintsSongOfSoaring,
        HintsSpiderHouses,
        HintsBankSign,
        HintsTransformations,
        HintsGossipStoneStrength,
    ]),
]
