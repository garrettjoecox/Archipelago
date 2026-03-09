# genlogic: the mm_2ship data and logic generation pipeline

This apworld's locations, items, options, region graph and access-rule logic
are all generated from the 2ship2harkinian randomizer's own sources; none of it
is written by hand. After changing the built-in rando (new checks, new items,
logic edits, new regions, condition tweaks), regenerate with one command:

```
python worlds/mm_2ship/tools/genlogic/generate.py /path/to/2ship2harkinian
```

Run it from the Archipelago repo root. With no argument it looks for a
`2ship2harkinian` checkout next to the Archipelago repo.

Then run the world's tests to confirm everything still holds together:

```
python -m unittest discover -s worlds/mm_2ship/test -t .
```

That is the whole loop for a logic or data change. New upstream *features* are
different: options, choice values and hint givers all need hand-written
follow-up too. The reference sections below explain how the pieces fit, and
[Updating after a 2ship change](#updating-after-a-2ship-change) is the
step-by-step for doing one.

## What gets generated (never edit these by hand)

| File | Source of truth | Contents |
|---|---|---|
| `Enums.py` | `Rando/Types.h`, `StaticData/Items.cpp` | `Regions`/`Locations`/`Items` string enums |
| `LocationData.py` | `StaticData/Checks.cpp`, `PlacementConstraints.cpp` | RCTYPE / scene / dungeon per check |
| `VanillaItems.py` | `StaticData/Checks.cpp` | vanilla item per check |
| `ItemData.py` | `StaticData/Items.cpp` + computed | AP item ids, names, RITYPE, progression flag |
| `OptionData.py` | `StaticData/Options.cpp` | `RO_*` -> (AP option attr, default) |
| `LogicHelpersGen.py` | `Logic/Logic.h`, `GiveItem.cpp`, `Souls.cpp`, ... | constants, helper predicates, `CanKillEnemy`, item/flag grant maps |
| `RegionData.py` | `Logic/Regions/*.cpp`, `Logic/Logic.cpp` | the full region graph with translated access rules |
| `SourceInfo.py` | the 2ship checkout's git HEAD | which commit this data came from (and whether that tree was dirty) |

Everything else in the apworld is hand-written and consumes the generated
modules (most importantly `LogicRuntime.py`, the reachability solver).

## How logic translation works

Region files use a strict macro DSL (`CHECK`/`CONNECTION`/`EXIT`/`EVENT`/`STAY`
with boolean condition expressions). The generator:

1. parses every condition into an expression AST (`cpp.py`),
2. translates it to a Python lambda over a `LogicContext` (`translate.py`), so
   `HAS_ITEM(ITEM_BOW)` becomes `s.has_item('ITEM_BOW')` and
   `RANDO_EVENTS[RE_X]` becomes `s.event('RE_X')`,
3. auto-generates helper functions from `Logic.h` macro bodies (`CAN_BE_DEKU`,
   `IS_DAY1`, `MIDNIGHT`, `ClockFilter`, ...) and from the `CanKillEnemy` /
   `canPlaySong` switch statements,
4. resolves exits to their target regions the same way
   `GetRegionIdFromEntrance` does (unclaimed entrances route to `RR_MAX`).

Unknown constructs fail loudly. If upstream adds a primitive the translator
doesn't know (a new function call, a new macro shape), generation stops and
lists every offending condition. Teach the translator about it in
`translate.py`, usually one line in `PRIMITIVE_CALLS`, and add the matching
method on `LogicRuntime.LogicContext` if it needs runtime state.

Expression-shaped macros and `inline bool` helpers written as
`if (cond) return true; ... return expr;` chains translate on their own. No
Python changes needed for those.

## What is hand-ported (and how drift is caught)

`LogicRuntime.py` ports the C++ *algorithms* (not data):

- `Solver.solve()` ← `GlitchlessLogic.cpp` reachability fixpoint (regions x
  time masks x event counters, plus vanilla self-grants for option-disabled
  checks) and `Logic.cpp FindReachableRegions`
- `expand_time_forward` / `owned_time_slices` ← `TimeLogic.cpp`
- `owns_half_day` ← `Logic.h OwnsHalfDayForMode`
- `can_access_dungeon` ← `Logic.h CanAccessDungeon`
- starting items ← `StartingItems.cpp GetComputedStartingItems`
- pool composition ← `GeneratePools.cpp` (in `ItemPool.py`)
- own-dungeon placement ← `PlacementConstraints.cpp` (in `PlacementConstraints.py`)
- option normalization ← `OnFileCreate.cpp` (in `MM2ShipWorld.generate_early`)

Two more sources are tracked without being ported. `CheckTracker.cpp
RefreshChecksInLogic` is a third, independent implementation of the
reachability fixpoint, and the one players actually read, so it has to agree
with the other two. `GiveItem.cpp` is parsed for grant flags, but
`extra_slot_grants` in `generate.py` is hand-written, so a *changed* grant
would otherwise pass unnoticed.

The generator hashes those C++ sources into `drift_hashes.json`. When any of
them changes upstream, regeneration exits with code 2 and lists exactly which
hand-ported pieces need review. After updating the Python ports (or confirming
no change is needed), re-run with `--accept-drift` to record the new baseline.

**The ledger catches "this file changed", not "the port covers it."** When it
fires on `GeneratePools.cpp`, walk the C++ function top to bottom against
`ItemPool.py` and `LocationFilter.py` rather than skimming the diff. An
unported branch (a whole-scene skip, a pool rebalance) looks like no change
at all.

## Wire-contract invariants (do not break)

- **Location ids are C++ enum ordinals.** The game client does
  `RANDO_SAVE_CHECKS[<ap location id>]`, so the `Locations` enum mirrors
  `RandoCheckId` order exactly. The generator guarantees that, which also means
  ids shift whenever upstream inserts checks mid-enum. Game build and apworld
  always have to be built from the same 2ship commit.

  This is enforced, not just documented. `SourceInfo.BUILD_VERSION` is the
  `project(2s2h VERSION x.y.z)` of the checkout the data came from, the same
  value `mm/src/boot/build.c.in` turns into `gBuildVersion`. It rides in
  `slot_data` as `game_build_version`, and `Archipelago.cpp VerifyBuildVersion`
  compares it against `gBuildVersionMajor/Minor/Patch`, refusing to touch the
  save on mismatch. Nothing is hand-maintained on either side: both numbers
  come from that one CMake line.

  That only holds while the version moves whenever the check table does, so the
  generator warns when it sees the table change with the version standing still
  (state in `location_table_guard.json`). Read that warning as "bump
  `project(2s2h VERSION ...)` before releasing". During development, where you
  rebuild the game from the same checkout anyway, it is safe to ignore.
- **Item names must match `Items.cpp` exactly.** The client resolves received
  items by display name. Item *ids* are permanent: the generator re-reads
  `ItemData.py` and only ever appends (seeded originally from the hand-written
  `Items.py` table). Duplicate display names collapse to the canonical entry,
  so `Piece of the Triforce` is `RI_TRIFORCE_PIECE`, mirroring the client.
- **Progression classification is computed.** An item is progression when the
  translated logic can test something it grants: an inventory item, a flag, a
  quest item, an event-adjacent family. Overrides live in `Items.py`.

## Updating after a 2ship change

Most syncs are steps 1-3 plus a version bump. The rest is a checklist of what
upstream can change that generation alone cannot absorb.

### 1. Regenerate

```
python worlds/mm_2ship/tools/genlogic/generate.py ~/Developer/2ship2harkinian
```

Read the output. Every message maps to a specific follow-up below. Anything
marked ERROR stops generation, but warnings still write the files, which makes
them easy to scroll past. Don't.

| Generator says | Means | Do |
|---|---|---|
| `N option(s) ... have no attribute in the AP Options.py dataclass` | upstream added an `RO_*` option | step 4a |
| `DRIFT WARNING` | hand-ported C++ changed | step 3 |
| `LOCATION TABLE WARNING: the check table changed but the 2ship build version is still X` | `project(2s2h VERSION ...)` needs bumping before release | step 5 |
| `ERROR: N checks exist in Checks.cpp but are in no region` | upstream dropped checks out of the region graph; they are dead content in-game too | fix it in the 2ship source, don't filter it apworld-side |
| `ERROR: <thing> mapped nothing` | a parser stopped matching, usually an upstream rename | fix the extractor in `generate.py` |
| translation errors | a new condition primitive | teach `translate.py` (see above) |

### 2. Review the generated diff

```
git diff --stat worlds/mm_2ship
```

Generated output is deterministic, so the diff is readable. Two things to look
for specifically:

- **A table that shrank to empty is a parser break, not a data change.** This
  has bitten us for real. Upstream renamed `RandoItemIdToDungeon` to
  `DungeonItemToDungeon` and left a same-signature function behind, so the
  extractor kept matching, returned `{}`, and silently declassified every key
  and stray fairy as non-progression. Nothing errored. Extractors now hard-fail
  on an empty parse; keep it that way when adding new ones.
- **Location id churn is routine.** Any mid-enum insert upstream shifts
  thousands of ids. That is expected, and is exactly what the build-version
  guard above exists to police.

### 3. Resolve drift

The ledger tells you *a hand-ported file changed*, not *your port is wrong*.
For each file it lists, diff it upstream and review the matching Python port
from the list above, remembering that an unported branch looks like no change
at all. Then re-baseline:

```
python worlds/mm_2ship/tools/genlogic/generate.py ~/Developer/2ship2harkinian --accept-drift
```

`Archipelago.cpp` and `CheckTracker.cpp` are tracked but not ported: read those
diffs and confirm they don't contradict the solver.

### 4. Hand-written follow-ups

`Options.py` is hand-written (its docstrings are the yaml documentation), as
are the solver and pool-composition ports. Match the change to its case:

#### a. New option

1. Add the class to `Options.py`. Copy the wording from the tooltip in
   `Rando/Menu.cpp`; don't paraphrase from memory.
2. Add the field to `MM2ShipOptions` and the class to an `OptionGroup`.
3. Defaults, ranges and choice ordinals must match C++; `TestOptionMirror`
   enforces this. Deliberate divergences go in its
   `INTENTIONAL_DEFAULT_DIVERGENCES` with a reason.
4. If it gates a *location type*, also add it to `LocationFilter.RCTYPE_OPTION`,
   the `Allsanity` preset and `TestAllShuffles`. All four are checked by
   `test_location_type_options_are_wired_everywhere`.

#### b. New or renumbered choice value

Upstream inserts enum members **at the front**, not just the end. Every later
ordinal then shifts, and an option's default can change meaning while its
integer stays the same, so `RO_OPTIONS` shows no diff at all and only
`RO_CHOICE_VALUES` moves. Diff that table specifically.

All three mirror tests cover this; let them tell you what to fix:

- `test_choice_values_match_cpp`: an AP value disagrees with Types.h
- `test_every_cpp_choice_is_offered`: upstream added a mode the yaml doesn't offer
- `test_defaults_match_cpp`: the default moved

#### c. New static hint giver

Both halves are required. Either one alone is silently useless in a multiworld:

1. 2ship side: the hook must call `Rando::GetItemLocationForHint`, not
   `FindItemPlacement` + `GetLocationNameForHint`. The latter only searches
   `RANDO_SAVE_CHECKS`, so an item in another player's world hints
   "in an Unknown Location".
2. apworld side: the item must appear in `MM2ShipWorld._static_hint_item_keys`
   so its placements ride in `slot_data["static_hints"]`.

#### d. New pool/placement semantics

Mirror it in `ItemPool.py`, `LocationFilter.py` or `PlacementConstraints.py`,
and in `LogicRuntime._compute_starting_items` too if it changes what the player
starts with. Where the C++ hard-codes counts, mirror the literals rather than
deriving them; the ledger review reads the port line by line against the C++.

#### e. Anything that randomizes *which checks exist*

If the game picks a subset with `Ship_Random`, AP has to commit to that choice
at generation time and put the seed in `slot_data`. Universal Tracker
regenerates from `slot_data` alone and has to land on the same list. See
`skulltula_seed` and `roll_skulltula_subset` for the pattern.

### 5. Version bumps

Per the wire-contract invariants above, an apworld and a game build from
different commits write items into the wrong checks. Both numbers come from one
CMake line, so:

1. In 2ship, bump `project(2s2h VERSION x.y.z)` in `CMakeLists.txt`.
2. In the apworld, set `archipelago.json`'s `world_version` to match.

`SourceInfo.BUILD_VERSION` picks up the first of those on the next
regeneration. Note that this version doubles as the o2r asset-archive version,
so bumping it forces asset re-extraction.

### 6. Verify

```
python -m unittest discover -s worlds/mm_2ship/test -t .
```

Then generate a real seed exercising whatever changed. The test base stops
before `distribute_items_restrictive`, so anything that depends on items
actually being placed (notably `static_hints`) is only exercised end to end:

```
SKIP_REQUIREMENTS_UPDATE=1 ./venv/bin/python Generate.py \
  --player_files_path <dir> --outputpath <dir>
```

A multi-slot yaml set is worth the extra minute when the change affects
placement. Foreign-world placements are where the interesting cases live.

### 7. Commit, in this order

Commit the 2ship side **first**, then regenerate once more before committing
the apworld. `SourceInfo` records the source commit and whether that tree was
dirty; regenerating last is what gets you a bare commit hash in `slot_data`
instead of one with a `-dirty` suffix pointing at sources nobody can check out.
