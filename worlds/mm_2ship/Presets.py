from typing import Any

# Option presets shown on the WebHost options pages (wired up via
# MM2ShipWebWorld.options_presets). Values use the yaml-facing forms
# (bools, ints, choice names) and are validated by AP's general test suite.

mm2ship_options_presets: dict[str, dict[str, Any]] = {
    # A gentler first seed: vanilla structure, generous hints and starting aid.
    "Beginner": {
        "starting_consumables": True,
        "hints_gossip_stones": True,
        "hints_transformations": True,
        "hints_song_of_soaring": True,
        "hints_boss_remains": True,
    },
    # Everything shuffled that adds locations, with dungeon items kept local.
    "Allsanity": {
        "shuffle_shops": True,
        "shuffle_tingle_shops": True,
        "shuffle_owl_statues": True,
        "shuffle_gold_skulltulas": True,
        "shuffle_frogs": True,
        "shuffle_cows": True,
        "shuffle_grass_drops": True,
        "shuffle_pot_drops": True,
        "shuffle_crate_drops": True,
        "shuffle_barrel_drops": True,
        "shuffle_freestanding_items": True,
        "shuffle_snowball_drops": True,
        "shuffle_tree_drops": True,
        "shuffle_enemy_drops": True,
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
        "placement_small_keys": "own_dungeon",
        "placement_boss_keys": "own_dungeon",
        "placement_stray_fairies": "own_dungeon",
    },
    # Triforce Hunt goal with softened world access.
    "Triforce Hunt": {
        "shuffle_triforce_pieces": True,
        "triforce_pieces_max": 30,
        "triforce_pieces_required": 20,
        "access_dungeons": "form_or_song",
        "shuffle_shops": True,
        "shuffle_owl_statues": True,
    },
}
