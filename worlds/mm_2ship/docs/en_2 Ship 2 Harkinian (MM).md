# 2 Ship 2 Harkinian (MM)

## What is 2 Ship 2 Harkinian (2S2H)?

2 Ship 2 Harkinian is a fanmade PC port of The Legend of Zelda: Majora's Mask. Being a native port, it adds widescreen
support, higher framerates, a built-in randomizer, a built-in check tracker, and a long list of optional
quality-of-life toggles. If you're curious about the specifics,
[download 2S2H](https://www.2ship2harkinian.com/) and take a look through the ESC menu.

## Where is the options page?

The [player options page for this game](../player-options) contains all the options you need to configure and export a
config file. Until this world is upstreamed, generate a template yaml from the apworld via the Archipelago Launcher's
"Generate Template Options" instead.

## I haven't played Majora's Mask before.

We recommend playing Majora's Mask vanilla first, ideally to 100% completion. The three-day cycle already asks a lot of
new players; you'll have a much better time in the randomizer when you're familiar with the base game.

## What does randomization do to this game?

Item locations are shuffled with the rest of the multiworld. Chests, major items, songs, masks and dungeon items are
randomized by default, with optional pools for shops, owl statues, cows, frogs, Gold Skulltulas, freestanding items,
hidden "wonder items" (invisible rupees and the clusters revealed by striking hidden triggers) and breakables (pots,
grass, crates, barrels, snowballs, trees, enemy drops). Further options can shuffle boss and enemy souls (which gate
fighting those enemies), the ocarina buttons, the ability to swim, and even the six half-days of the clock itself
(Clock Shuffle). The logic is generated directly from the 2S2H randomizer's own rules, three-day time system included,
so what counts as in logic matches the standalone randomizer.

## What is the goal of 2 Ship 2 Harkinian (MM) when randomized?

The standard goal matches vanilla: gather what you need to reach Majora's Lair on the Moon and defeat Majora. The exact
requirements (remains and mask counts for the Moon, Majora's Lair, and the trials) are configurable. Alternatively,
Triforce Hunt scatters Triforce Pieces across the multiworld, and the game completes automatically once you've found
the required amount.

## Can I play offline?

Mostly, yes. Creating the save file requires a connection to the slot. Afterwards you can play offline: the client
tracks your checks locally and resyncs everything with the server the next time you connect. If you're planning a
purely solo seed, consider generating a randomizer directly in 2S2H instead for a simpler time.

## What items from this game can appear in other players' worlds?

Every shuffled item can appear in another player's world.

## How many checks are there?

It depends heavily on the chosen options. The default pool is a few hundred checks; enabling every shuffle option
(grass, pots, enemy drops, and so on) grows it into the thousands.

## Is there a tracker pack?

2S2H comes with a built-in check tracker, found in the ESC menu's Randomizer section. Universal Tracker is also
supported, which is handy for cross-checking logic.
