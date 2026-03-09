from argparse import Namespace

from BaseClasses import CollectionState, MultiWorld
from test.bases import WorldTestBase
from test.general import gen_steps
from worlds.AutoWorld import AutoWorldRegister, call_all


class MM2ShipTestBase(WorldTestBase):
    game = "2 Ship 2 Harkinian (MM)"


def setup_passthrough_multiworld(slot_data: dict, seed: int) -> MultiWorld:
    """Build a second solo multiworld the way Universal Tracker does: default
    yaml options, with slot_data exposed as multiworld.re_gen_passthrough so
    generate_early restores every seed-derived decision from it."""
    multiworld = MultiWorld(1)
    multiworld.game[1] = MM2ShipTestBase.game
    multiworld.player_name = {1: "Tester"}
    multiworld.set_seed(seed)
    args = Namespace()
    world_type = AutoWorldRegister.world_types[MM2ShipTestBase.game]
    for name, option in world_type.options_dataclass.type_hints.items():
        setattr(args, name, {1: option.from_any(option.default)})
    multiworld.set_options(args)
    multiworld.re_gen_passthrough = {MM2ShipTestBase.game: slot_data}
    multiworld.state = CollectionState(multiworld)
    for step in gen_steps:
        call_all(multiworld, step)
    return multiworld
