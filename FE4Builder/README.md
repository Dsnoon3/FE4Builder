# FE4Builder character editor

## Music & Sound Player

Open **Graphics & Text → Music & Sound Player**, or select **Play Song**, **Play SFX Byte**, or **Play SFX Word** in Event Editor and click **Preview audio…**. The player itself is read-only; their existing operands can now be changed in Event Editor using the same catalogue. The browser currently lists **138 music IDs, 5 observed byte-effect IDs, and 15 observed word commands**, with reference-use labels and search. Music names come from the Nightmare list and can differ from your translation; this is not an exhaustive SFX-bank decoder.

Play renders a timed native preview in a hidden Snes9x worker and plays the WAV through Windows audio or a Linux WAV player. Stop cancels preparation or playback; closing the player also stops it. Choose 6–120 seconds or repeat the clip (restarting the preview, not a seamless musical loop). The first preview takes a few seconds; subsequent plays use a bounded 128 MB cache. The opened ROM, event parameters, backups/history and game saves remain untouched. Preview reads the current loaded ROM bytes, including already-staged memory edits, but does not apply an unwritten form.

Word commands now have shared descriptions in the player and Event Editor, including evidence/uncertainty notes. `$00E0`–`$00E7` fade music out progressively more slowly (about 0.5–4.1 seconds in the native preview), then stop its sequence. `$00E8` restores music volume over about 0.5 seconds and does not restart a stopped track. `$00F7` ducks to 60/255; `$7FF7` ducks to 127/255 using the high byte as its target. These leave the track running. Fade-in previews with a background begin ducked so restoration is audible. The low-word menu/dialogue cues are named by their native call sites. `$00D0` sets a synchronization flag; its exact scene-specific musical purpose is marked partly understood.

`PLAY_SFX_WORD` sends a sound-driver word, not necessarily an audible effect. Some words control fading or playback state. An optional background track lets you hear those changes; None previews the command in isolation and can be silent. Byte effects load the normal chapter sound bank and are previewed without background music. Sounds that require another game-specific bank/state may differ or remain silent. Unsupported modified sound drivers are rejected. Audio previews require 64-bit Python. Windows uses the bundled Snes9x core; Linux detects a separately installed Snes9x libretro core and paplay/aplay/ffplay. See the root LINUX.md for Ubuntu 22.04 setup. The bundled Windows core and its license/source links are under `vendor/snes9x`.

The worker boots a private emulator instance and redirects its main task in emulated work RAM to native audio processing, isolating it from intro-event sounds. It does not patch a ROM file. Tests check distinct non-silent music, a native byte effect, a fading word command, headers, driver guards, cancellation/cache reuse, read-only UI, and event links; development playback is captured or mocked rather than played over the speakers.

## Event Editor — Prologue

Open **Maps & Events → Event Editor (Prologue)**, or use **Edit Prologue commands…** in Chapter Event Viewer. The first version supports **18 scripts / 219 commands**, including the opening, Quan’s arrival, Lex/Azelle’s arrival, Yngvi’s capture, the ending and several conversations/retreat scenes. The list also identifies unused reference scripts; editing an unused script does not make it run.

Select a command in the ordered script list. **Load Unit Direct** exposes character, Prologue faction, start/destination X/Y, entrance speed (0–7), sprite color, commander flag and native AI setting (0–15). Packed movement flags and reserved bits are preserved. Faction determines allegiance independently of sprite color; changing characters also requires reviewing sprite preparation and later scene commands. **Run Event Condition / Register Character Map Sprite** offers a named character dropdown (10 existing commands). It changes whose map-sprite graphics are prepared, not which unit spawns, moves or joins; keep it aligned with the later scene commands. Invalid character assignments are rejected, and both command opcodes stay unchanged. Camera position exposes X/Y (0–63); ordinary **Map Scroll** exposes destination X/Y (0–63, camera upper-left in tiles) and scroll speed (1–255, higher is faster; zero is rejected). Scripted scrolling and scrolling to an event unit slot remain read-only; Pause exposes event timer ticks (1–65,535); fade-in/out exposes the native timing parameter (1–255). **Play Song**, **Play SFX Byte**, and **Play SFX Word** offer catalogue dropdowns. Preview auditions the selected draft without writing it. Word commands preserve all 16 bits, including values such as `$7FF7`; many control fading rather than produce an effect. Existing unknown IDs may be preserved unchanged, but new selections must come from the catalogue. Other commands and all loaded-byte displays remain read-only. Dialogue, reinforcements, recruitment, village rewards and objectives retain their existing dedicated editors through the linked viewer. Loaded parameters in the command list reflect the ROM snapshot; the pending marker identifies an unwritten draft.

This version edits operands in place: it cannot add, delete, reorder or replace commands, edit branch destinations, or create new events. Unsupported/relocated layouts are rejected rather than guessed. The Edain-abduction script has an unsupported layout and stays in the reference viewer. Changing scene timing or camera position can still alter presentation; test the full scene with **Save & Launch**.

**Write to ROM / Ctrl+S** overwrites the opened ROM with automatic backup and undo history. F5 saves and launches; failed saves retain the draft and restore memory. Edits preserve ROM length, support copier headers, reject stale drafts, and share structural profiles with the other event editors. Tests cover all 136 editable commands, exact changed operands, read-only commands, ranges, headers, coexistence with linked editors, save rollback, backups, undo/redo and viewer navigation. Development tests use memory or disposable ROM copies.

## Usability cleanup

Use **Ctrl+S / Write to ROM** to overwrite the opened ROM with backup and undo history. **Ctrl+Shift+S / Save a copy** exports a draft without changing the editing target or clearing pending edits. A persistent marker and changed-field highlights show what is unwritten. File → Show / copy ROM path reveals the full source path.

Skills use named checkboxes; holy blood uses None / Minor / Major controls. Unknown bits remain preserved, with raw values under Advanced. Technical fields start collapsed; game-facing labels lead with names and show growth %, leadership stars and converted gold. Known affected-record links and inventory-slot owner details explain shared data; event/script users may be additional.

Each ROM remembers its editor record/table/filter and tool chapter/zoom context. Long event forms scroll, windows fit the work area, and Escape closes tools through their normal unsaved-changes checks. Searching retains the existing selection behavior: it filters the list without switching the currently edited record.


## Objectives & Progression

Open **Maps & Events → Objectives & Progression**, or use the matching link in Chapter Event Viewer. Browse 105 existing seize/death checks across all chapters, including direct and flag-dependent links to chapter-ending scripts. Pick a castle-capture trigger or a unit-defeat trigger, change its faction and target, or switch between those two condition types. The six-byte command keeps its original completion flag and linked story actions. This changes what activates the existing event; it does not create a new victory script.

The editor separates direct events from later events which check the completion flag. Other prerequisites can still apply. For example, Chapter 2's Agusti capture sets a flag and the ending runs in a later state check. Reference tabs expose the chapter conditions and story scripts; links open the event viewer and the first directly catalogued dialogue scene. Intermediate captures, map changes, recruitment, rewards and other story dependencies are not automatically rewritten.

The **global defeat rule** selects a protected roster slot (Generation ID 1–24), shared across generations. Default slot 1 means Sigurd / Seliph; slot 2 means Noish / Shannan. When a player-faction unit in that slot reaches the normal defeat handler, the native game-over sequence runs. Changing this replaces the default protected slot in every chapter; it does not add a second protected unit. Scripted deaths can bypass that handler, and other defeat conditions and game-over messages remain unchanged.

Chapter order remains native. The editor shows the next chapter, including Chapter 5's generation transition and the final epilogue, but does not reorder chapters or patch inheritance. It supports fixed-size existing conditions, not new rout/survival objectives or arbitrary chapter jumps. Newly overlapping event triggers, invalid targets, stale drafts, relocated pointers and unsupported opcode layouts are rejected. Existing shared conditions and flag-only reactions remain supported. Field help starts collapsed.

**Write to ROM** overwrites the selected original ROM with automatic backup and undo history; F5 saves and launches it. Copier headers are supported and ROM size is unchanged. Tests cover all 105 triggers, conversions between seize/death, every protected slot, compatibility with conversations/reinforcements/dialogue, byte preservation, save failure rollback and undo. Native Snes9x tests on copies confirmed a changed death trigger ran Yngvi's event, the protected-slot change caused game over on Noish's defeat, and a changed ending trigger reached the save prompt and continued into Chapter 1. Later chapter paths should be tested after editing.

## Recruitment & Conversations

Open **Maps & Events → Recruitment & Conversations**, or use **Edit recruitment / conversation…** in Chapter Event Viewer. Browse 164 existing conversation routes across the twelve chapters. The chapter list shows current participant names, and Find searches names and event labels. Reference tabs show chapter conditions and linked event actions; flags, payment rules and other story requirements remain intact.

Participant controls are enabled for 53 routes with verified Talk menu tables or direct Talk-target setup commands. Editing a pair updates the event checks and those linked availability records together. Paired money-dependent variants are grouped. Self-talk, invalid IDs, byte-sized target overflow and collisions with another conversation in the chapter are rejected. Substitute-aware and unverified availability routes remain read-only; their dialogue and verified recruitment switches are still accessible.

The 16 verified direct recruitment commands have individual checkboxes naming the character who joins the player faction. Some commands are shared by multiple routes. Unchecking skips that faction transfer; checking restores its exact original bytes. Shared commands show how many conversation routes they affect. This does **not** cancel dialogue, payments, event flags or later story actions. It does not add recruitment to a scene that has no verified recruitment command. A skipped five-byte command becomes five native yield opcodes, retaining script size with a few frames of delay.

**Edit dialogue…** opens the selected existing scene directly in Dialogue Editor. Participant changes do not automatically replace dialogue portraits, rewards or other hardcoded character references; the named recruitment character remains separate from the talk target. This version edits existing routes and does not create new events or alter child/substitute mappings.

**Write to ROM** overwrites the selected original file with automatic backup and undo history. F5 saves and launches it. Edits use fixed-size fields, preserve ROM size, support copier headers, reject relocated/custom layouts and stale drafts, and cooperate with Reinforcement Editor and ordinary dialogue-pointer edits. Snes9x confirmed a Prologue Ethlyn→Sigurd conversation changed to Alec→Sigurd: Alec gained Talk and launched that conversation. A separate disposable fixture verified enabled versus disabled faction transfer. Tests cover all routes, all editable pairs, every recruitment switch, exact changed bytes, compatibility, invalid inputs, save failures and undo.

The shared Prologue layout check also accepts changed dialogue pointers for its three battle quotes and Midir's cutscene-death quote (listed as **Turn1Evans Phase3** in Dialogue Editor). Changed pointers must resolve to readable dialogue in the supported Project Naga layout. Event instructions, conversation-table locations and stale-draft checks remain protected; conversation writes preserve those dialogue pointers and texts.

## Reinforcement Editor

Open **Maps & Events → Reinforcement Editor**, or select a supported event in Chapter Event Viewer and click **Edit reinforcements…**. This first version covers 58 existing scripts with 542 direct/group loads across the chapters. Select a spawn to edit entry X/Y and movement speed. Direct loads also expose destination X/Y; group destinations and unit identities remain managed by Army Editor. An Army Editor shortcut settles your draft before switching tools.

Verified turn conditions can be changed to turns 1–254; 255 means any turn. Faction/phase, AI, flags and other story requirements remain intact. The interface shows how many events share a turn condition: changing it affects all of them. Story-driven arrivals have no turn control. This version does not add/delete units or events, replace character identities, or edit arbitrary trigger logic. Eleven unsupported scripts are listed in `data/reinforcements.json`; use the read-only viewer for those.

**Write to ROM** overwrites the selected ROM with automatic backup and undo history; F5 saves and launches it. Coordinates are zero-based, 0–63, and speed is 0–7. Other bits in the movement operand are preserved. Edits keep script sizes and ROM size unchanged. Modified opcode layouts or relocated scripts are rejected. Camera paths, later scripted moves and map camera bounds are separate, so test changed arrivals in-game. Headered ROMs are supported. Reference names follow the disassembly.

Validation round-trips every supported spawn script, checks exact changed bytes, copier headers, stale/custom layouts, failed-save rollback and backup/undo. Snes9x testing on a disposable copy moved Quan's Prologue arrival from turn 3 to turn 1 and his destination from (59,14) to (58,14); RAM confirmed Quan, Finn and Ethlyn deployed on turn 1, with Quan at the new tile. Later story paths have not all been played through.

## Grouped main menu

After choosing a ROM, the main menu groups tools into **Characters**, **Items**, **Maps & Events**, **Graphics & Text**, and **Advanced**. Each tool has a short description. **Find editor** searches names, descriptions and categories; double-click a result or select it and press **Open selected editor**. Clearing the search returns to the previous category. The advanced Nightmare modules remain available under Advanced; existing editor features and linked navigation are preserved.

## Village Rewards

Open **Maps & Events → Village Rewards**. Select a chapter and village event variant, choose an item reward, enter optional **Extra gold at visit**, and use **Write rewards to ROM**. You can add an item to a gold-only village, change/remove an existing item, and change the stat/amount where a stat-gain event already exists. The editor covers **78 event variants** across the twelve chapters, including the original **14 item grants and four stat grants**. Some physical villages use multiple visitor/story-dependent variants: edit the relevant variants separately. Original recipient conditions, dialogue and story callbacks are retained. Adding entirely new stat-gain animations/conditions is outside this editor.

Extra gold is paid **in addition to** the normal village gold, which still falls with raid damage. This leaves base gold, raid penalties, destruction timing and the normal gold popup unchanged. Extra gold accepts 0–50,000 (the normal held-gold cap still applies); existing stat rewards accept increases 0–30. An added item on a stat-gain village is independent of its existing stat reward. Item choices are shared **player item slots**, not new copies of item types: reusing a slot that is already owned or assigned elsewhere can transfer that same instance. Slot numbers are shown to distinguish repeated item names.

**Edit village dialogue…** opens the linked scene in Dialogue Editor. Reward dialogue is not rewritten automatically, so update descriptions of changed rewards yourself. Dialogue Editor follows private village scripts and updates their integrity metadata, including when rewards are changed again later. Reward and dialogue saves use the normal backup/undo/redo system. Pending rewards are settled before switching variants/chapters or closing, and failed writes restore ROM memory.

Supported profile: the supplied 8 MiB FE4 ROM/event layout, including copier headers. Edited villages receive fixed private script allocations inside an initially empty PC `6F0000–6FFFFF` reserve. Original scripts and unselected event pointers remain intact; branch targets inside copied scripts are relocated, and instruction/metadata checks reject unsupported or stale data. No ROM expansion is needed. In-game verification used a disposable Prologue test ROM: a gold-only village granted a Speed Ring plus 1,000 extra gold, and a second test removed the Speed Ring from its original village. The default gold popup still reports the base payout. Other chapters’ condition/callback paths have not been exhaustively played through.

## Dialogue Editor

Open **Dialogue Editor** from the main menu. It contains **1,624 catalogued scene references**, grouped into the Prologue, Chapters 1–10, Final Chapter, intermission, epilogues, death/lover quotes, castle shops and attract scenes. Filter by chapter and search scene labels or decoded text. Select a scene, edit its text, then **Write dialogue to ROM**. **Import TXT… / Export TXT…** use UTF-8 text with the same visible command tags. Writes create automatic backups and undo/redo history; selecting another scene or closing settles pending changes. **Save & Launch (F5)** saves the scene before launching the configured emulator.

Normal letters, punctuation and Enter edit dialogue text directly. Commands remain visible as tags: `[Wait]` waits for player input, `[Scroll]` scrolls the active box, `[Left]` / `[Right]` select the dialogue slot, `[Portrait 0007]` loads a portrait, and `[PauseText 10]` pauses for hexadecimal 10 (16) frames. Arguments are hexadecimal; `[End]` must finish a normal script. Existing extended end commands and uncommon glyph bytes are preserved. Do not remove command tags accidentally: they control the surrounding scene. Existing `[RunASM …]` callbacks and `[PrintDialogue …]` references are protected from modification in this text editor. Event branching and changing which scenes events invoke are separate work.

The **text-only font preview** reads glyphs and widths from the ROM, with a count of lines over 240 pixels. Its three-line preview pages are viewing aids, not automatic in-game page breaks. Insert the appropriate Wait/Scroll tags and line breaks yourself. Portraits, alternate fonts, explicit positioning, dynamic name/number substitutions and script side effects are not simulated by the preview; placeholders can affect its width estimate. Test the edited scene in the emulator.

This first implementation targets the supplied **8 MiB Project Naga beta 7** dialogue engine, with or without copier headers. All catalogued original scripts decode/re-encode byte-for-byte. Saves isolate the selected scene pointer using private text storage, preserving original scripts, shared suffixes and other scene references. An initially empty managed reserve at PC `7D0000–7D7FFF` and `7D9000–7DFFFF` leaves the growth patch untouched; metadata occupies 9 KiB, leaving 51 KiB for edited text. Allocations reuse released space, never cross the reserved gap or a half-bank, and do not expand the ROM. Storage conflicts, corrupt metadata, stale scenes and exhausted/fragmented space are rejected without partial writes. Editing one of several references to the same script isolates that reference; update other references separately if desired.

Verification includes all 1,624 script round trips, longer/shorter replacements, shared-script isolation, protected commands, private-area exhaustion/corruption, growth-patch coexistence, headered ROMs, backup/undo/redo and failed-save rollback. A relocated Prologue conversation was played in Snes9x with edited text and working portraits. Other chapters' event execution and callback paths have not been exhaustively played through. Implementation/reference notes: `research/dialogue-editor/README.md`.

## Character promotion targets

**Character Editor → Identity & settings → Promotion Class** edits the selected playable character’s promotion target directly, including children and substitutes. Choose a class or **None** and use the usual **Write to ROM** button. Stat and promotion edits save together with one automatic backup/history step; reload, discard, undo/redo and failed-save rollback include the promotion field. The legacy **Character Settings → FE4 Promotion Editor** accesses the same table, so both editors stay consistent after reload.

Promotion targets are indexed by stored character ID 1–63, not the displayed row or current class. The dropdown writes the existing separate promotion byte without changing character record sizes. The destination class’s **Promotion-Into Level** controls the required level. If changing a character ID, save/reload that identity change before editing its promotion target; simultaneous ID/promotion changes are rejected to prevent changing another character’s target unintentionally. No ROM expansion is needed.

## Startup ROM selector

The builder starts on a **ROM Selector** screen. Choose **Browse for ROM…**, or **Open last ROM** to reopen the last successfully loaded file, then the main menu appears. The file browser remembers that ROM’s folder between sessions. The path is stored in `data/rom-selector.json`; no ROM is loaded automatically at startup. Canceling or failing to open a file keeps the selector available. If the remembered ROM has moved, browse for its new location; missing folders fall back to an existing parent directory. A settings write failure does not block opening a ROM.

## Stat Bonus Editor

Open **Stat Bonus Editor** from the main menu, or use **Edit bonuses…** beside an item’s Stat Bonus dropdown. Select a weapon profile or ring effect, edit its amounts, and click **Write bonuses to ROM**. Saves overwrite the opened ROM with automatic backups and undo/redo; the window settles pending edits before switching effects or closing. Item dropdown labels refresh from the edited ROM.

Weapon profiles `01–0D` expose Strength, Magic, Skill, Speed, Defense and Resistance independently. Their six weapon-boost bytes share a table with holy blood definitions; the editor preserves the separate growth and weapon-rank fields. Safeguard (`0E`) and Barrier Blade (`0F`) edit their existing Defense/Resistance amount. Ring effects edit their existing stat’s amount; change the item’s bonus ID in Item Editor to choose a different target stat. None (`00`) has no editable amount. Effects are shared: the window lists items referencing the same data, so modifying Balmung’s profile also changes another item assigned that profile.

Ordinary stat increases accept 0–255; very large amounts can exceed the in-game numeric display. Movement is limited to 0–3 to avoid exceeding the native movement lookup; both native movement calculations are updated together. Rings and the two special swords store amounts in native code rather than a data table, so their instruction signatures are checked and unsupported code is rejected. This supports the supplied 8 MiB Project Naga beta 7 layout, with or without copier headers; no ROM expansion is needed. HP/Luck bonuses, new profiles, per-item private effects and changing which stats a fixed ring effect targets are not included.

Emulator checks on disposable ROMs: Steel Sword assigned an edited profile grants Sigurd +3 Strength/+4 Speed, and the edited Power Ring grants Seliph +9 Strength. Tests cover isolated byte changes, live labels, all native amount locations, invalid/stale data, backup/undo/redo, headered ROMs, and failed-save rollback. The normal growth-display patch remains installable after editing these bonuses.

## Optional ROM patches: display growth rates

Open **Patches** from the main menu, then **Install: Display growth rates**. This writes an optional native game-code patch to the opened ROM, with the usual automatic backup and undo/redo history. In the game, open a player unit’s normal status page and press **SNES Y** to switch between stats and growth percentages. The heading changes to **Growths %**; HP shows its growth in the header. Press Y again to return. Closing the screen, changing units or opening another status page returns to normal stats. Growths use the game’s own calculation routines, including holy blood bonuses and inherited growths. Enemy records are excluded.

Version 2 fixes leftover equipment/status boost digits beside growth percentages. ROMs with version 1 show **Update: Display growth rates** in the Patches window. Updating creates one backup/history step, remains removable, and requires no ROM expansion. Restart/reload the ROM in the emulator after updating. Verified against the supplied Seliph save state with Power/Skill/Speed/Barrier/Shield Rings: growth view hides bonus indicators and normal stats restore them on repeated toggles.

This first patch targets the supplied **8 MiB Project Naga beta 7** profile, with or without a 512-byte copier header. The installer checks required executable routines, hook bytes and an empty 4 KiB reserve at unheadered PC `0x7D8000–0x7D8FFF`. It preserves editable character data and does not expand the file. Other translations and hacks that change the required code are rejected. **Remove patch** restores the original hooks and reserve after checking patch integrity. Existing save files are usable; load an ordinary in-game save or open the status screen again after loading an older emulator save state.

Verified in the Snes9x libretro core: Sigurd’s growths (including 110% HP), Noish’s growths, Seliph’s second-generation status screen with ring boosts, repeated Y toggles, unit cycling, closing/reopening the status window, and switching to/from holy blood. Automated tests cover installation/removal/upgrades, headered ROMs, backups, undo/redo, conflicts, and save failures. Second-generation inherited growths call the native routines; other parent pairings have not been exhaustively tested. Implementation notes: `research/growth-display/README.md`.

## Chapter maps and unit placement

In **Map Editor**, use **Resize map…** to set a chapter’s visible width/height and left/top origin. FE4 stores a fixed 64×64 terrain grid and separate camera bounds; resizing edits those native bounds, as the original Prologue does for its 64×32 area. Width accepts 16–64 tiles and height 14–64, with the entire rectangle inside the grid. The 16×14 minimum fits the SNES viewport. Changes appear immediately in the editor but stay staged until **Write tiles to ROM**. Cancel leaves the size unchanged; chapter switching/closing offers Save/Discard/Cancel, and saved resizes support automatic backups and undo/redo. No ROM expansion is needed.

Tiles outside the rectangle remain stored: enlarge the bounds or enable **Full 64×64** to inspect them. A resize does not shift terrain, units, castles or event coordinates, and does not change AI/cursor boundary code or scripted camera movements. The dialog counts army-table deployments outside the proposed area (including reinforcements); scripted placements and event objectives need separate review. This feature changes the chapter camera area, rather than rewriting FE4’s fixed-grid engine. A 40×24 Prologue ROM was checked in Snes9x: the native header loader sets scroll limits to X=0…384 and Y=0…160 pixels as expected.

Open **Map Army Editor** from the main menu or from a chapter in the Army Editor. Open **Map Editor** separately to paint chapter tiles. All twelve chapter backgrounds are rendered directly from the opened ROM's compressed layout, chapter graphics, palettes and shared metatile dictionary. The Prologue defaults to its 64×32 camera bounds; **Full 64×64** reveals its unused lower area, shaded as outside normal bounds. Other standard chapters show 64×64.

Choose a deployment group or search the deployment list. Units use their actual class map sprites decoded from the opened ROM, including gender and character-specific overrides such as Sigurd/Seliph's mounted sprites. Small corner badges identify deployment groups, and a yellow outline marks the selected placement tile. Drag a unit onto a tile, or select its list entry and use the X/Y controls. Changes are staged until **Write positions to ROM**. Unit moves change only deployment coordinate bytes and save as one backup/history step. The map window includes **Undo / Redo** and settles staged moves before switching chapters, closing, or undoing committed edits.

Sprite previews use the first native standing frame: infantry sprites are 16×16 and mounted sprites are 16×24. Standing graphics, class/gender assignments, character overrides and palettes are read from the opened ROM. Walking frames use the native object templates to retain all body pieces. Automatic colors use blue for faction slot 0 and red for other slots; the color selector previews other factions. Event allegiance changes are not simulated. Unsupported hacked references show a marked placeholder. Previews do not modify the ROM.

In **Class Editor**, select a class and click **Sprite sheets…**. The viewer includes character/gender variants, faction palettes, all three standing frames and all sixteen walking frames arranged as four direction rows. **Export sheet PNG…** exports the selected tab at native pixel size with transparency. The viewer is read-only.

Use zoom, scrollbars, mouse wheel and right-drag panning to navigate. Double-click a deployment or use **Center selected unit** to locate it. **Grid** shows tile boundaries; **Terrain** switches to a color-coded terrain view. Hover reports coordinates, terrain and event-dependent blocking flags. Coordinates outside 0–63 are rejected for new moves; existing off-map positions remain intact unless deliberately edited. Placements outside a chapter's normal camera bounds are indicated, rather than silently clamped.

These are army-table deployment groups, including reinforcements. Groups can spawn at different times, so overlapping positions are valid. Player/recruitment positions embedded directly in event scripts are not included yet. The background is the base chapter layout: event-triggered map changes, water animation, class-based pathfinding and active blocking-flag state are not simulated. The Map Army Editor moves existing deployments. The separate Map Editor paints tiles and resizes camera bounds. Creating new units and changing the underlying 64×64 terrain storage dimensions are not supported. Bounds, tile graphics, palettes, AI, leaders and equipment are preserved when writing positions.

Format references: https://gitlab.com/robertsstuff/sfc-mapconv (`doc/game-specific/fe4.txt`, `src/extract/extract/fe4.cpp`), https://github.com/ulti-mage/FireEmblem4 and the supplied ROM's map-loading code. The renderer combines 256 chapter-specific metatiles with 768 shared metatiles, each built from four SNES 4bpp subtiles. Runtime needs no network access. Other hacks that relocate map tables or use 128-column maps need an additional profile.

Validation: `python scripts/run_tests.py`.

## Working with several editor windows

Normal editor windows leave the main menu and sibling editors interactive. You can keep Portrait Editor and Dialogue Editor open together in either opening order. File pickers, confirmation prompts and selection dialogs still block input temporarily while they need an answer; dismissing them does not make an editor modal again.

Exiting FE4Builder or opening another ROM closes editor windows through their normal pending-change prompts. Stay/Cancel keeps the current ROM and pending editor open. If an editor saves while the same ROM is being reopened, the main window loads those newly saved bytes. Existing stale-data checks still apply: in particular, a portrait draft opened before another editor saves may require reopening Portrait Editor before it can be written. Its rejected save retains the draft, and Export sheet can preserve the imported artwork. An old portrait window cannot save or launch a different ROM.

## Player weapon / item slots

In **Item Editor → Player Weapon Editor**, each list row is one persistent player item slot, numbered **01–8E** (for example `07 Thunder`). The displayed name and inventory icon follow the item type currently assigned to that slot. Each row edits exactly one assignment byte; the original two-slots-per-record presentation is no longer used. Writing retains normal backups and undo/redo.

The **Appearances of player item slot** notes follow the slot ID across the current ROM's player starting inventories, shop lists, village rewards (including private Village Rewards editor scripts), ordinary event item-grant commands, and generic/special enemy drop fields. Two slots containing the same weapon type keep separate occurrence lists. Locations refresh after ROM changes; item names also follow edited item-name assignments. Chapter hints use live deployment groups and decoded direct event deployments where available. Undeployed records remain visible with an unknown chapter rather than an invented one.

Each appearance has a **Go to location** button. Character, enemy and shop links open the source record and focus its slot field; village links select the matching reward; event links select the event and highlight the live command bytes. The Back button returns from record links to the selected player slot.

Slots can be claimed once per generation. The notes list possible sources, including later fallback opportunities when an earlier village, drop or event was missed. Sources in the same chapter are not assigned a fabricated execution order. Potential parent inheritance is listed before ordinary generation-2 sources for slots obtainable in generation 1. Eligibility uses the current item type/rank and the native routine's explicit holy-weapon exception operands where recognized. The notes identify current generation-1 starting holders and link to inheritance settings. Actual pairing, parent ownership (including personal supply), child class/blood and whether a source succeeds depend on the played save; the ROM alone cannot establish them. If the slot is not inherited, an ordinary generation-2 source can supply it.

Event grants are decoded at live command boundaries and pointers, not searched as arbitrary byte patterns or inferred from historical script annotations. **Coverage notes** report unsupported/truncated scripts and unresolved deployment/village layouts. Arbitrary ASM callbacks and save-state gameplay are not simulated, so a custom ASM item grant needs a supported decoder before its location can be included. Location indexing is read-only and does not rewrite event scripts or move item ownership.

## Portrait previews and importing

Character records now show a live portrait preview, with **Preview / Import portrait…** opening the selected portrait. Class records show their class portrait. The main menu also has a standalone **Portrait Editor** for all 248 portrait IDs.

The integrated workspace uses FE4 Modding Studio's searchable slot browser and portrait storage engine inside FE4Builder. It shows the **current ROM portrait**, the **Complete PNG sheet** (including staged edits), and an assembled **Talking preview** to its right. Animate talking cycles the normal face and both mouth frames; choose a fixed frame to inspect it. Importing a different slot keeps the other staged slots. **Undo slot** discards only the selected slot's pending replacement.

**Import PNG…** detects both complete artist layouts automatically:

- **Studio 64×64:** the 48×64 face at the left, with the native animation tiles in a 16×64 strip at the right.
- **FE4Builder 64×80:** the 48×64 face at the top-left, with two 32×16 mouth frames side by side below it. The unused top-right 16×64 padding is ignored.

Choose the **Complete PNG sheet / export layout** before **Export sheet…**; Studio is the default. Exports include the staged replacement when present and use a transparent indexed palette. Exporting and reimporting an unchanged template preserves duplicate palette entries. Legacy 48×64 faces (static-mouth fallback) and native 128×32 sheets are also accepted. No cropping or resizing is performed. The preview assembles FE4's mouth frames over the face; it does not simulate full in-game dialogue timing.

Colors are rounded to SNES precision. Original shared-grey and the documented five-site unlocked palette profiles are supported; unknown or partial palette patches are rejected. Shared grey retains the on-ROM index-14 word; unlocked palettes allow all 15 opaque colors. Excess colors require **Allow color reduction** and should be checked in the preview. Partial alpha is rejected. Transparent pixels use index 0; opaque RGB images use their top-left color as the background key.

**Write Portrait to ROM / Ctrl+S** writes all staged slots through FE4Builder's normal backup and undo-history system. **Save & Launch (F5)** saves through the same path and launches the configured emulator. Closing with pending edits offers Write / Discard / Stay. A replacement affects all characters assigned that portrait ID. Shared graphics and palettes are isolated as necessary; all 248 portrait outputs are verified before writing, and copier headers and ROM size are preserved. Portrait writes update the ROM checksum. Failed planning or saves retain staged imports; stale in-memory or externally changed ROMs are not overwritten.

Studio's **Optimize portrait storage when writing**, **Preview packing…**, and **Reserve space…** controls are retained. Optimization re-encodes and packs unique sheets using only directly read portrait bytes inside the supported original portrait windows; unknown gaps and other subsystems are preserved. If conservative writing needs separate storage, reserve a uniformly blank, mapped, headerless range you have verified belongs to your project. Blank bytes alone do not prove that a region is unused. Reservations clear after a successful write. Optimization remains optional, and previewing does not enable it.

The **Portrait space** report shows original/new sizes and savings for the selected slot and all portraits together. Sizes measure compressed graphics, including compressed-lookback dependencies; palette data and pointer tables are excluded. Shared bytes count once in totals, so a slot can shrink while the total grows if its shared graphics must be split. Negative savings mean growth. With optimization enabled, sizes are calculated in the background for the staged repack; after writing they reflect the saved ROM. Planning still checks that the data fits before writing.

Original sizes are captured the first time this version opens the portrait editor for each ROM path and saved in the local `FE4Builder/data/portrait-sizes.json` config. They remain the baseline across writes and future sessions; moving/copying the ROM to another path starts a separate baseline. The first successful optimized write displays the original total, new total and bytes saved. Its shown state is saved per ROM, so previews and failed writes do not consume the report. The optimization checkbox stays enabled after writing, including Save & Launch, without treating the already-saved optimization as an unwritten edit. Local size history is not included in release packages.

The portrait workspace is packaged inside FE4Builder and requires only Python/Tkinter, without the separate Studio folder or Pillow. The original Studio snapshot is retained for later feature integration. Loader, decoder and palette-profile guards follow that snapshot; hacks with relocated tables or changed decoders require another profile.

ROM-free regression checks: `python3 FE4Builder/scripts/run_tests.py test_portrait_workspace.py` from the repository root (use `xvfb-run -a` on headless Linux). These use generated tile data to exercise both layouts, palettes, shared assets, packing, headers, backups, undo/redo, failed saves and UI integration. They do not replace testing your ROM and talking frames in an emulator.

## Backups, undo/redo and change history

Every changed **Write to ROM** operation creates a full copy of the existing file before overwriting it. Backups and `history.json` live beside the ROM under `FE4Builder Backups/<ROM-path ID>/`; the history window shows the exact folder. Names use timestamped unique filenames and backups are never automatically deleted. If a backup or the recovery journal cannot be written, the ROM write is blocked. Saving without byte changes creates no extra backup or history step. Overwriting an existing **Save edited ROM as…** destination also backs up that destination; exporting a new file does not alter the opened ROM's undo timeline.

Use **Undo / Ctrl+Z**, **Redo / Ctrl+Y**, or **Edit → Change history / Backups…**. Undo and redo apply to committed ROM edits, not individual keystrokes. They immediately save the restored state to the opened ROM and create another backup. Field edits and name changes (including menu repacking) each form one history step. History survives closing and reopening the same ROM at the same path. New edits after undo discard the redo branch while retaining those earlier actions in the audit history. Existing edits from before this feature was installed cannot be reconstructed.

The history screen shows edit descriptions, changed field values, byte ranges, backup filenames and times in America/Santiago. Select an action and use **Restore selected backup** to recover the ROM state immediately before that action. Restoration is backed up and can itself be undone. Backups associated with new history records are checked for integrity before restoration. The recovery journal also allows a saved edit to be recovered into history if finalizing the history file was interrupted.

External file changes are detected before overwriting or undo/redo; reopen the changed ROM to start a new undo timeline. Unsaved fields are settled before history actions. Keep the backup folder with the ROM to retain its recovery data; moving the ROM to another path currently starts a separate history timeline. Each full backup takes approximately the ROM's file size on disk.

Validation: `python scripts/run_tests.py`.

## Editing actual character names

Use **Character Name Editor** on the main menu, or **Edit character name…** beside a selected character's fields. This opens a text entry with a live preview rendered from the opened ROM's own font. **Write to ROM** saves directly to the opened file.

This implementation supports the 63 playable name IDs in **Project Naga beta v7**, including headered copies. It edits actual stored name bytes, both main graphics variants, generation-menu graphics, resurrection names and castle-dialogue name strings. Names that fit use their existing space. Wider names enable **Write to ROM** and show a confirmation before enlarging their allocation and repacking that generation's reserved menu graphics. Other characters' tile pixels are preserved; the name tilemaps and width bytes are updated. Main graphics pointers and ROM length remain unchanged. Some game menus may clip very wide names.

The provided ROM is already 8 MiB, the standard ExHiROM image limit. Appending bytes beyond it would not create addressable game data, so the warning accurately explains reuse of existing reserved space rather than claiming file growth. The eight-byte stored-name limit remains: accepting more than eight encoded characters requires engine changes, not just extra graphics space. Graphics are limited to eight tiles (64 pixels), including the resurrection question mark. Unsupported input or exhausted menu capacity is rejected before modifying any bytes. Supported input is English letters, digits and basic punctuation; spaces and accents are not implemented. Young and adult Finn share their main graphics, so renaming either updates both.

Names literally written into story dialogue are not automatically replaced. Enemy name text and other translations/Japanese ROMs need additional layout profiles. No emulator validation has been performed yet. Reference layouts and encoding come from https://github.com/Miacidae/Project-Naga-beta-v7 (`MenuText/Tilemaps/Names.asm`, `Names_Menus.asm`, `Names_Question.asm`, `Dialogue/Others/Character_Names.asm`, `Dialogue/Encodings.asm`, and the font width table). Downloads in `research/` are reference material; runtime rendering reads the ROM and does not require downloaded graphics or extra packages.

Run `python scripts/run_tests.py` to verify layout recognition, original-font rendering, isolated edits, atomic rejection, Finn's shared names, header handling and save/reload.

The main menu also includes Item Editor, Shop Editor, Enemy Editor, Holy Character Editor, Love Editor, Character Settings, Children Settings, Class Settings, and Music & Other Tables. Together with the dedicated character/class screens and chapter-grouped Army Editor, these expose all 137 base Nightmare modules. Select the module/table within each category, search its records, and edit its fields with the same write/save controls. Generic record labels fill gaps in incomplete upstream name lists; extra labels beyond a module's declared count are ignored. Signed fields support negative values. Graphics and pointer modules expose numeric tables, not image previews or asset import. Editing code-related settings and pointers requires understanding the selected module; no automatic relocation or table expansion is performed. This covers the downloaded modules' capabilities, not every possible FE4 feature.

Double-click **Launcher** (the Windows shortcut) to start FE4Builder, or run `python src/FE4Builder.py` from this folder. The launcher and app use Sigurd’s native standing sprite as their icon. Requires Python 3.10+ with Tkinter (available on this computer). No third-party packages are required. Keep the sibling `Nightmare Modules` folder in place.

1. Open a FE4 `.sfc` or `.smc` ROM.
2. Choose **Character Editor** or **Army Editor** from the main menu. Select a table and record. Search filters the active table. **Main Menu** returns to the editor selection.
3. Edit base stats, growths, class, level, identity, skills, holy blood or starting equipment. Dropdown labels come from the original modules; editable dropdowns also accept decimal or `0x` hexadecimal values.
4. Click **Write to ROM** to save the current record directly to the opened ROM file, overwriting it. Keep your own backup if needed. Failed writes leave the fields available for retry; external file changes are detected before overwriting.
5. Alternatively, click **Save edited ROM as…** to create an edited copy. This does not change which file is open: subsequent **Write to ROM** actions still target the opened file. Saving a copy also applies the current record fields.

Seven tables cover generation 1, generation 2 static characters/substitutes, and children. Children only have the fields actually stored in their records; their inherited stats are not fabricated. Names use the upstream modules' spellings. `Char Name` edits a name identifier, not the ROM's text. Equipment values refer to player inventory slots as defined by the modules. Skill and blood dropdowns retain the upstream combination labels and allow raw numeric values.

The Army Editor now groups deployments by Prologue, Chapters 1–10 and Final Chapter. Lists show group ID, group name and character. Fields include character, coordinates, leader, AI, faction slot and formation ID. The advanced table exposes 58 relative pointers at unheadered file offset 0x1C000. Group membership follows ulti-mage/FireEmblem4 TABLES/EVENTUNIT/UNITGroupPointers.csv (https://github.com/ulti-mage/FireEmblem4). Each opened ROM is scanned through its own pointers and 0xFFFF end markers, excluding terminators. The final unused group has 13 entries without a terminator, as documented in the disassembly. Invalid layouts are rejected. The supplied ROM contains 1,328 deployments. Research files and army_groups.json are local references; no network is needed at runtime. Group resizing and renumbered or relocated pointer tables are not supported.

Copier headers are detected by file size, and module offsets are adjusted by 512 bytes for unheadered ROMs. The supplied Project Naga ROM's Sigurd record was checked at file offset `0x3B267` (base HP 35). Internal title validation rejects unrelated games, but arbitrary hacks that relocate tables are not supported. ROM checksum bytes are preserved, not recalculated. Portrait rendering, text editing, enemy character stats, inheritance simulation, and other editors are future work.

Validation: `python scripts/run_tests.py`. Tests use the project ROM read-only and temporary copies, covering character and army parsing, byte-isolated edits, header handling, save/reload, source-copy preservation, original-file overwrite, external-change detection, and atomic rejection of invalid field values.



### Tileset viewer / exporter

Open **Tileset Viewer / Exporter** from the main menu, or **Choose map tile...** from the Map Editor. Choose a chapter to preview its palettes. Browse all assembled 16×16 tiles, chapter-specific tiles (IDs 000–0FF), or shared tiles (100–3FF). Raw 8×8 graphics have separate all/shared/chapter views and a palette selector. Click a tile to inspect its ID, terrain, visible map usage, and component graphics. Export the current sheet or selected tile as a native-size PNG without the preview grid. This viewer never writes ROM data.


### Painting chapter maps

In **Map Editor**, click **Choose map tile...**, then click an assembled 16×16 tile from the current chapter. The tileset window stays open; clicking another tile updates the brush immediately. Click or drag on the map to paint. Clicking either window brings it to the front, so the picker can stay open while painting. Use the separate **Map Army Editor** for deployments. Right-click a map cell to pick its current tile as the brush, then left-click elsewhere to paint it. Right-drag pans without changing the brush. Painting preserves each cell's upper blocking/event bits; terrain comes from the new tile's terrain entry.

Click **Write tiles to ROM** to save painted tiles. Army positions are saved separately through the Map Army Editor. Backups and undo/redo cover the entire batch. Switching chapters or closing asks whether to save or discard staged changes. Layouts are verified after recompression and stored privately per chapter in an empty reserved 128 KiB area at PC 7A0000–7BFFFF of an 8 MiB ExHiROM ROM, without growing the file. Repeated saves reuse fixed slots. Occupied storage, shared compressed dependencies, or stale data cancel the write. Tile definitions, palettes, and scripted event map changes are not edited by painting.


## Folder layout

- **Launcher.lnk** — the Windows launcher shortcut, displayed as Launcher.
- **src/** — application source code.
- **data/** — chapter/deployment metadata used by the program.
- **assets/** — Sigurd’s standing-sprite PNG and multi-size Windows icon.
- **tests/** — verification scripts.
- **scripts/** — the launch command, test runner, and shortcut generator.
- **research/** — reference documents, downloaded sources and decoding experiments.

Run `python scripts/run_tests.py` to check the program, or add a test filename pattern such as `test_portraits.py`. If the folder is moved and the shortcut no longer resolves, run `powershell -ExecutionPolicy Bypass -File scripts/create_launcher.ps1` to regenerate it. ROMs, backups, and the sibling Nightmare Modules directory stay in their existing locations.


## Linked editors

Click a blue **Class** or **Equipment** label (or its **Edit...** button) to open the exact class or item record. Player equipment slots are resolved through the ROM’s current inventory table; weapons/staves, rings, broken weapons and the Circlet open their matching modules. Empty equipment slots have no target. Click the character’s portrait preview or **Portrait Editor…** to open that portrait directly.

The **Back** button returns from a linked class/item editor to the previous record and search. Unsaved field changes use the existing Save / Discard / Cancel prompt before navigation; links follow the resulting saved reference. Closing the portrait dialog returns to the character. Linked item/class edits affect all users of that item type or class.


## Validation and field explanations

The **Field help / Validation** panel starts collapsed. Click its [+] button to expand it, then hover over or focus a field to read its explanation and stored range. Click [-] to collapse it again. Error/warning counts remain visible on the collapsed button. The live summary flags unknown options, unused skill/blood bits, simultaneous minor/major blood flags, equipment versus base class ranks, inconsistent targeting ranges and invalid supported pointers.

**Check record / Shared data...** checks the current draft and explains class users, shared inventory slots, item-type instances, and portrait graphics/palette aliases where supported. **Edit → Check map and portrait pointers...** checks loaded ROM data: all army groups, twelve chapter layouts/resources and 248 portrait graphics/palettes. Both reports are read-only.

Errors block applying or saving the record. Warnings remain visible and allow intentional hacks. New out-of-range deployment coordinates are errors; existing off-map coordinates are warnings and can be preserved. Pointer validation is limited to documented formats: 24-bit definition addresses and relative army group pointers. Three-byte code patches and undocumented bank-relative tables are not guessed. Blood, inheritance, personal weapon restrictions and events are not a full simulation; equipment compatibility findings are warnings. Fields without a documented explanation say so explicitly.


Personal **Skills 3** bit **04** is named **Escape (retreat on defeat)**. It selects special defeat handling; character-specific event scripts control departures. First-generation Finn, Quan and Ethlyn use it. Validation warns when the flag is absent from their records. See `research/escape-skill.md` for the disassembly evidence and limits.


## Item icons and weapon previews

Character equipment fields show live thumbnails. **Browse...** opens a searchable visual list with weapon-type filters, a larger preview and a compact stat summary. Player equipment browsing selects an existing inventory slot; the slot and item IDs are shown separately, so duplicate instances of the same weapon stay distinct. Choosing an entry changes only the current form until it is written normally. Click the thumbnail or **Edit...** to open the item-type stats.

The Item Editor displays a larger native inventory icon and live Might / Hit / Weight / Uses / Price / Range summary. Its **Preview** selector switches between **Inventory icon** and the larger **Held weapon** artwork. **Browse items...** navigates to the selected weapon, staff, ring or Circlet record, with **Back** returning to the previous editor. The item sprite/palette editor previews its draft sprite assignments.

Equipment thumbnails, browser rows and browser previews use the real 16×16 inventory icons decoded from the opened ROM, including tomes, rings, broken weapons, staves and the Circlet. All 138 item types are resolved through the game’s item-to-icon table; some items intentionally share an icon. Icons are shown with nearest-neighbor scaling and transparent backgrounds. Held-weapon artwork remains an optional separate preview; items without held artwork show their real inventory icon instead. Previews and browsing do not write graphics or change inventory assignments by themselves. Unsupported hacked sprite references show an unavailable preview instead of crashing.


## Emulator launch and testing

Press **F5** or click **Save & Launch** to validate and save the current edits directly to the opened ROM, then launch that exact file in your emulator. Automatic backup/history behavior is the same as **Write to ROM**. Launch controls are available in the main window and in the map, army placement, portrait and name editors; those popup editors save their own pending work first. Invalid fields or failed saves prevent launch. If the emulator fails to start after saving, the edits stay saved and the program reports the launch error.

**Emulator → Emulator settings...** chooses an existing emulator executable. This installation is configured for `C:\Games\Snes\snes9x-x64.exe`. Settings are stored in `data/emulator.json`. Additional arguments use one argument per line; `{rom}` is replaced with the saved ROM’s absolute path. Snes9x needs just `{rom}`. Paths containing spaces do not need quotes. If the placeholder is omitted, the ROM path is appended. Commands are passed as argument lists without a shell. Other emulators can be configured with their own flags or core arguments.

The emulator remains open when FE4Builder closes. After further edits, Save & Launch starts another test session; use the emulator’s normal controls to reset/load the game. Emulator preferences, in-game saves and save states are managed by the emulator. Automated tests verify save/backup ordering, aborted saves, argument boundaries and actual subprocess dispatch with a harmless stand-in; they do not claim in-game validation of edited ROM behavior.

## Intro cinematic and title screen

Open **Intro & Title Editor** from the main menu with the 8 MiB Project Naga beta 7 ROM. The resource list includes the Nintendo splash, title background, English logo and subtitle graphics, title/splash palettes, all thirteen opening captions, and identified intro artwork/effect layers. Export a native-size PNG, edit it, then import it and click **Write to ROM**. **Save & Launch (F5)** saves the staged resource and opens the ROM in the configured emulator. Switching resources or closing prompts to save/discard staged changes. Backups and undo/redo include relocated graphics and pointers.

For captions, type a replacement in **Replacement caption** and click **Preview text** before saving. The editor renders the ROM's English font into the actual caption graphics; a single line must fit 248 pixels. Existing captions can also be edited as 256×16 PNGs. Caption text is stored as graphics, so the original wording is displayed in the preview rather than extracted into the text box.

Screen imports rebuild the selected layer's tilemap with mirrored-tile sharing, retaining palette assignments, priority and its existing VRAM tile budget. Over-budget imports are rejected; replacing ROM storage does not increase VRAM capacity. Title background imports preserve the separate cloud graphics. Tile-sheet imports retain dimensions and tile positions. Keep the exported indexed PNG palette when editing cinematic sheets: these show gray palette indices because their changing scene palettes are not yet decoded. The game continues to use its original colors. The title's sheet palette selector only changes the preview/export colors; use the palette resources to change actual colors. Palette PNGs contain one pixel per entry, with enlarged swatches in the viewer.

This edits artwork layers and captions, with reversible artist layouts for logo graphics. It does not combine the whole animated cinematic or all title-screen layers into a single replacement image. Scene order, timing, music, transitions, object positions and animation scripts remain unchanged. Supported resource sizes and loader instructions are checked before edits. Compressed replacements are verified and allocated in an empty reserved area at PC **700000–79FFFF**, separate from map/portrait storage, without growing the ROM. Occupied storage, conflicting pointers or stale data abort writes. Tests cover export/import round trips for every listed resource, screen rebuilding, caption rendering, private allocation, copier headers, save/reload, backup/undo/redo and GUI save/launch integration. In-game playback of replacement artwork still needs checking in the emulator.


### Assembled logo layouts

The English and sword/original logo entries start in **Readable layout**, assembled in their native game positions. The English view follows the ROM's live title tilemap, including the lettering, subtitle, trademark and copyright. The original view shows the complete sword, crest and Japanese banner in one captured frame of the flag animation. Its placement template comes from the running ROM's sprite/OAM data, rather than inferred adjacent tile groups. Final native palettes are read from the opened ROM. Auxiliary tiles no longer clutter these views; **Raw tiles** includes all stored graphics and supports previous raw-sheet exports.

**Export PNG...** exports the assembled layer. **Import PNG...** translates edits back to the original pixels, preserving unused or occluded data and keeping the ROM's tilemap, sprite positions and animation unchanged. Keep PNG dimensions and transparency. Painting outside the native artwork area is rejected because there is no tile to store those pixels. Re-export assembled PNGs made with the earlier arrangement before editing; that arrangement had different dimensions and positions.

Shared tiles can appear more than once: editing one copy updates its other copies automatically. If two changed copies request different values for the same stored pixel, import reports the conflict and preserves the staged data. Erasing an overlapping sprite pixel clears its contributing pixels so the old artwork underneath does not reappear. Imported changes remain staged until **Write to ROM** or **Save & Launch**.
# Chapter Event Viewer

Open **Maps & Events → Chapter Event Viewer** to browse 557 named events across the twelve chapters. Select the chapter overview for conditions such as turns, conversations, deaths, villages and castle captures; select an event for its annotated actions. Search matches both event names and commands. Linked scenes open directly in the Dialogue Editor; Village Rewards and Army Editor shortcuts are also available.

This first version is read-only. Symbolic scripts come from the FireEmblem4 disassembly (commit `387b2e4c63b72b0d3f2854eaa69f26946d83b383`), bundled in `data/events.json`; they are reference annotations, not a live decompiler. The viewer reads current event pointers and bytes and compares them against the development reference ROM. Changed or relocated scripts are prominently flagged; their annotations are historical. Byte spans use the next catalogued pointer, capped at 4096 bytes, and can contain padding. Five unnamed/unmapped table entries are not catalogued. Trigger blocks are checked at their reference locations; relocated chapter trigger tables are not followed. No event editing or simulation is provided yet.



### AI Viewer

Open **Maps & Events → AI Viewer**, or **Inspect selected AI…** on a Load Unit Direct command. The latter opens the faction/group selected in the current draft without applying it. The viewer is read-only; writing AI scripts is a later step.

Browse chapter → faction → AI group. It reads faction headers, AI script pointers and command operands from the opened ROM, including copier-header ROMs. The supported reference has 72 faction definitions and 199 script entries. Conditional branches show both reachable paths, including commands after an earlier END reached by another branch. Known operands include named character targets, turns, event flags, formations and location IDs. Unknown or partly understood commands retain explicit uncertainty labels and native source notes; raw bytes and PC/SNES addresses are available for inspection. A source name is not a verified high-level behavior preset.

Assigned units shows potential matches from Army records and supported direct-spawn events, not emulator state. Chapter/faction names and slot associations come from the reference disassembly: runtime faction replacements, AI changes and unsupported event deployments are not simulated, and edited faction-loading events may invalidate those associations. Variant definitions may show the same assignment matches. Coverage failures are reported. Group 0 has no normal script lookup; the ordinary AI loop processes groups 1–8, despite the deployment nibble accepting 0–15.

Shared script uses lists exact entry-pointer matches; double-click a use to navigate to it. Different entries may also share branch targets. Reload refreshes data after changes elsewhere. Invalid pointers, unknown opcodes, overlapping commands and bounded traversal keep malformed scripts from being followed indefinitely; no ROM bytes are changed.

Opcode formats, source comments and faction labels are reproducibly generated by `research/build_ai_catalogue.py` from the local FireEmblem4 disassembly's `SAFEGUARD/AI.h`, `TABLES/CHAPTER/FactionGroupPointers.csv` and chapter event sources. Runtime viewing does not require the research source tree.


Ordinary **Dialogue** commands now offer named scene choices and **Find dialogue…**, with chapter filtering, search over scene names and readable text, and a text preview. The supported translation currently provides 1,624 valid catalogue choices. Choosing a scene stages its full 24-bit pointer; unknown current pointers may remain unchanged, but new values must be supported catalogue scenes. Only the pointer operand changes.

**Open in Dialogue Editor…** settles pending event edits, then opens the text reference belonging to this event command. Saving text uses the existing dialogue copy-on-write storage, backups and undo history; returning reloads the event so a relocated text pointer is reflected immediately. This avoids accidentally editing only the catalogue source reference after choosing a shared scene. Portraits, speakers and control tags remain in the dedicated Dialogue Editor. Scene selection/text editing requires its supported Project Naga dialogue profile.


## Shareable releases

Run `python FE4Builder/scripts/build_release.py` from the project root to create the Windows ZIP, Linux tar.gz and SHA-256 checksums in `releases/`. These are portable **source** distributions requiring Python 3.10+ and Tkinter, with no pip dependencies. Each includes a platform launcher, setup instructions, static metadata, FE4 Nightmare modules, notices and a file-hash manifest. Explicit allowlists exclude ROMs, research, saves, history, local settings and caches. The Windows package also includes the existing licensed Snes9x audio DLL; Linux omits that binary and offers audio through an optional native core and WAV player. Packages include Ubuntu setup/launch instructions. A Windows/Ubuntu 22.04 ROM-free CI workflow is provided; the actual Linux GUI/audio still needs verification on Ubuntu.


**Run Event Condition / Set Talk Target** now exposes named **Initiator** and **Target** dropdowns for the four existing Prologue assignments. Only named one-byte character IDs are offered; Target also includes None to clear the stored target. The direction matters, and later assignments replace the initiator’s previous target. This edits talk-target information, not the actual conversation trigger or dialogue: use Recruitment & Conversations for those. The two opcode bytes, other condition variants, command order and script size remain unchanged. Saves use the normal backup/undo system.


**Dialogue with BG** exposes the dialogue scene (with the same name/text search and linked Dialogue Editor), a named background selector (Fountain, Gate, Alley, Throne, Hallway, Cloister), and native fade timing (1–255). Dialogue Type is displayed read-only and its byte stays protected while its modes are investigated. The seven existing commands in supported Prologue scripts are edited in place; unknown current scene/background values may be preserved but new selections must be verified options. Test scene transitions in-game. End Event and Restore Phase Music also have read-only descriptions.


**Fill Event Unit Slot** exposes a named character and **Slot 1 / Slot 2** selector for its two supported Prologue commands. The slot is encoded as 0/1 automatically. It records the existing unit reference and current coordinates; it neither deploys nor moves a unit, and later fills replace the slot contents. Fill again after movement when fresh coordinates are needed. **Set Camera to Event Unit Slot 1** has a read-only description explaining its cursor-focus behavior and invalid-coordinate no-op. The related **Map Scroll to Event Unit Slot 1** help describes its speed operand. Neither has a separate Slot 2 counterpart in the native event command set.


## Dialogue Background Editor

Open **Graphics & Text → Background Editor**, or **Edit background…** beside the Background field in Dialogue with BG. Choose Fountain, Gate, Alley, Throne, Hallway or Cloister to see its assembled 256 × 88 artwork. Export PNG produces the image at native resolution; Import PNG stages an opaque image of exactly that size. Export first as a template. The preview reflects how the import is mapped to the existing 16-color subpalette for each 8×8 tile; arbitrary new colors are approximated. Palette editing is not included in this first version. The Fountain retains its native palette animation, so its in-game colors can vary from the static preview.

Write to ROM / Ctrl+S saves the staged artwork to the opened ROM with automatic backup and undo history; F5 saves and launches. Changing the selected background or closing offers Write/Discard/Stay when an import is pending. Reload discards the staged replacement after confirmation. Failed writes restore the in-memory ROM and retain the draft. All scenes that select the edited background ID use the replacement.

The editor supports the verified 8 MiB Project Naga loader, with or without a copier header. It reads the native long-pointer descriptor table at PC 0ABACF. Descriptor offsets 3, 6 and 12 select the background tile sheet, raw palette and 32×11 picture tilemap. Full dialogue frames, portraits, text-box graphics, shared original streams, native animation code, scene dialogue and event timing are preserved. Background ID 6 originally aliases Cloister but is not offered as a separately verified scene ID; replacing ID 5 isolates its descriptor without changing that alias.

Changed art is recompressed into one private 64 KiB slot per background at PC 690000–6EFFFF, separate from the builder’s village/dialogue, intro, map, portrait and patch storage. The editor validates unused space before claiming it, stores an ownership checksum, rejects stale/corrupted data and verifies the saved streams. The two compressed streams are kept within native 32 KiB half-bank boundaries. No ROM expansion occurs; occupied storage is rejected rather than overwritten. Native backgrounds are preserved in their original locations.


**Load Unit by Group** now exposes a named deployment group, named one-based entry, Start X/Y and entrance movement speed (0–7) for all 33 existing loads in supported Prologue scripts, including expanded loop commands. Changing the group refreshes the available entries. Read-only help shows the selected record’s character, destination, faction, AI, commander flag and formation. Change those shared deployment values in Army Editor. The native handler derives sprite color from allegiance, so the otherwise overridden color byte stays protected; upper speed flags are preserved. Invalid group/entry combinations and stale Army data are rejected before writing. Load Unit by Group Silent remains read-only with an explanation.


## Ubuntu 22.04 support

Use `sh "Setup Ubuntu.sh"` and `sh Launcher.sh` from the repository root. The portable smoke suite is `xvfb-run -a python3 FE4Builder/scripts/run_tests.py --portable`. Source and release launchers share the same Python version/Tk checks and do not depend on the current working directory. Linux mouse-wheel events are supported in the character form, shared panels and map/tile/sprite/intro canvases, while preserving popup and Army-form scroll exclusions. Emulator settings accepts native executables and scripts. UI preferences and backup-history identities distinguish case-sensitive Linux ROM paths. Full setup, optional native audio, Studio snapshot launchers and development test instructions are in the root LINUX.md.

Move Temporary by Script supports character, starting coordinates, initial speed, sprite color and the offscreen disappearance flag. Its existing route is shown as readable movement/facing/pause steps. Basic parameters preserve the movement pointer and route bytes; unsupported route bytes stop the preview instead of guessing. Shared routes are never changed by these parameter edits.

### Movement route editor

Select Move Temporary by Script and choose Edit movement route. The window lists verified Prologue events/command numbers using the same route; other chapters and custom scripts are not fully indexed. Edit movement steps, waits, speed changes, facing and halt points, ending with End. Every write creates a private copy for this command, so other callers and original route bytes remain intact. Private copies use a checked 64 KiB area at PC 0x5F0000 in supported 8 MiB ROMs; occupied/corrupt storage is rejected. Backups and ROM undo/redo include both the route and pointer. Unknown route instructions stay read-only. Storage is append-only and reports full rather than overwriting older copies.

Set/Unset Flag if in Chapter now provide chapter selectors and chapter-local flag IDs 0-79. Known Prologue flag names come from matching source commands to verified ROM operands. Unnamed flags stay visibly unnamed; changing chapter refreshes flag names. Original unsupported values may be preserved, but new out-of-range values are rejected.
