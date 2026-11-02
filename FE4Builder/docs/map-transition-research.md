# Event 3B runtime investigation

Tested with the existing local headless Snes9x libretro research core and Project Naga beta 7 reference ROM. This is an experiment report, not a claim of exhaustive opcode coverage. Original ROM and input savestates were read only. All patched ROMs, new states, captures and WRAM/VRAM dumps are disposable research files and must not be distributed.

## Method

32 parameter experiments: 20 runs at the first Prologue opening command (10 values with a naturally dark starting screen, then the same 10 with WRAM brightness buffer forced to 15); 10 runs on an already initialized map; one extended zero-timing run; one explicit fade-in follow-up. Three baseline/state-preparation runs preceded these experiments. Values: 00, 01, 02, 04, 3F, 40, 41, 80, 81, C1.

The normal input sequence completed the opening via its alternate branch, bypassing the second 3B. To isolate a real visible-map context, the map experiments load the state after baseline frame 9194 and explicitly redirect wActiveEventOffset to the second 3B at offset 337. Thus these are controlled re-entry tests, not untouched full-chapter playthroughs. The initial-brightness tests also explicitly patch buffer 000070; do not mistake them for natural transitions.

Runner traces every frame: active event pointer/offset (001738/001736), brightness/forced blank (000070), internal map mode (000D77), fade input (00033F), main-loop state (000302/000304). Captures include screenshots and WRAM/VRAM. Right/Down inputs at frames 1100 and 1160 check subsequent cursor movement.

## Measured visible-map transitions

| Byte | Internal mode | First black frame | Full brightness after black | Event advances beyond transition |
|---|---:|---:|---:|---:|
| 00 | 0 | 3841 | 3866 | 3867 |
| 01 | 0 | 16 | 41 | 42 |
| 02 | 0 | 31 | 56 | 57 |
| 04 | 0 | 61 | 86 | 87 |
| 3F | 0 | 946 | 971 | 972 |
| 40 | 2 | Not within 1400 | Not within 1400 | Not within 1400 |
| 41 | 2 | 16 | 50 | 51 |
| 80 | 3 | Not within 1400 | Not within 1400 | Not within 1400 |
| 81 | 3 | 16 | No automatic return within 1400 | 16 |
| C1 | 3 | 16 | No automatic return within 1400 | 16 |

Frame numbers start at 1 after the state is restored. Zero mode 0 was extended to 4500 frames. Native code uses an eight-bit fade countdown; zero behaves as a 256-frame interval, not an instant transition. 63 is slow but valid. Do not label 00 a permanent hang.

01 and 41 produced visually matching maps after completion and both accepted directional cursor input: cursor offsets changed from (192,144) to (224,160). 81/C1 stayed black; cursor offsets did not change in those runs. In a follow-up disposable script, adding FD 46 01 FD FF FF after 81 restored brightness and directional movement, again (192,144) to (224,160). This does not prove that bit 80 permanently disables input; it suppresses the automatic reveal and changes event waiting behavior.

The dark-start tests completed even with timing zero, because no visible fade-out was needed. The following script's explicit fade-in made the mode-3 maps visible later. This explains why original 80 usage can be valid while blindly using it on a bright map appears stalled.

## Native-code cross-check

SRC/Events.asm rsEventCommand3B (91/C7A7) masks input with 003F for fade timing. Bit 80 selects internal mode 3 and takes precedence over bit 40; otherwise bit 40 selects mode 2, neither selects mode 0. Both high bits together behave like 80, confirmed by 81/C1 traces.

The command schedules procMainLoopChangeFadeByTimer with target 80/B122, plus an event-wait process 82/8A30. Mode 0 calls 88/8082; modes 2/3 take the additional 88/9268, 87/EAF1 (update locations), 86/C629 and 88/8082 setup path. Their complete semantic differences have NOT been demonstrated by these screenshots; avoid promising a universal rebuild/refresh result.

SRC/TempStuff.asm rsUnknown81AD28 skips automatic procFadeIn when internal mode is 3. The event wait process also branches on bit 80: clear waits for full brightness; set can release the event once forced blank is cleared. Runtime observations match both branches.

## Recommended description and editing boundary

Suggested cautious label: Map transition / reinitialize map. One packed byte: fade interval bits 0-5, additional setup bit 6, leave-dark/early event continuation bit 7 (dominates bit 6). Keep current opcode name available. Prefer timing 1-63 for visible fades; preserve existing zero values because dark-start scenes use them intentionally. Do not expose mode names as fully verified gameplay semantics yet. No builder editing support was added during this investigation.

Outputs: summary.json (first matrix), map-summary.json (visible-map matrix), per-case trace.json and headless-* captures. runner.py adapts the existing growth-display/run_game.py. matrix.py and map_matrix.py reproduce the matrices after generating the stated baseline states. These scripts reference local research prerequisites and are not release dependencies.

Original ROM SHA-256 after testing: 21cbb4d2ac2adfa8b72c6dc339f960dae0570db149b89b518ce86e6089142691

## Follow-up: terrain reloading and bridge flags

The builder now uses the display name Map Transition, retains EVENT_3B as legacy metadata, shows its packed operand read-only and provides the measured timing/mode explanation. No write capability was enabled.

12 valid follow-up runs (6 terrain-marker and 6 bridge-flag controls), plus 6 preliminary marker runs repeated after correcting the flag offset. The preliminary flag probes mistakenly patched 52BD (part of the chapter event pointer); their flag conclusions were discarded, and all cases rerun with the correct flag-byte address 52C4 = chapter entry 52BB + TemporaryEventFlags offset 7 + flag-byte index 2. Marker-only results agreed in both batches. This correction is retained for reproducibility.

Terrain experiment: replace aMapData[0] at WRAM 7F2400 from 0102 to 0010 before controlled map re-entry. At frame 300, 01 retained 0010; 41 and 81 restored 0102. This confirms that the extra setup path reloads the chapter terrain map, not merely screen brightness. This is one chapter/context, and does not establish every side effect or dynamic-map behavior across chapters.

Bridge experiment: set Bridge Raised (23) and clear Bridge Lowered (22) by writing 80 to 7E52C4; clear active-map-change bookkeeping at 7E4EA5. The bridge at (12,15) lives at WRAM 7F2B98. After transition alone (01,41 or81), tile 00BD remained, active-change bits zero. With a separate 4A 5C Update Location and Map Change Events after the transition, all three variants changed the tile to 02D1 and set active-change bit 0. Positive controls demonstrate that Map Transition is NOT a substitute for applying changed bridge flags. Scripts bridge_matrix.py and rebuild_matrix.py and corresponding JSON summaries reproduce these observations.

No broad claim is made about all location records, map-change bookkeeping already active before reloading, other chapters, or the unlabelled subroutines on the reload path. Those remain future testing targets.

## Persistence tests: already-applied changes

36 distinct scenario/mode combinations were tested with a no-transition control and 01/41/81: raised bridge with consistent state; raised bridge after clearing its condition flag; raised bridge after clearing its active-change ledger; destroyed village; closed village; castle ownership change; hidden unit; synthetic deployment relocation; bridge raised then lowered. Additional hidden-unit repeats and four exploratory SET_UNIT_POSITION runs were also performed. The latter did not produce the intended (58,14) positive-control coordinate (returned 4,0), so they are NOT evidence for a correctly applied relocation. They were replaced with explicitly labelled synthetic deployment-table relocation tests, which did reach (58,14).

Custom bounded test scripts live at PC/SNES 5E9000 in disposable ROMs. They run native Update Location and Map Change Events, yield/pause 50 frames, perform the chosen transition and hold the event in a 1000-tick pause. The pause isolates transitions from normal player/AI turn events. Event pointer/offset are explicitly redirected to the test script in the existing initialized Prologue state. These are controlled experiments, not organic playthroughs of village destruction or castle seizure.

Bridge: native update first applies the raised tile 02D1 and active-map-change bit 0. All modes preserve that tile. Clearing Bridge Raised after it was applied still preserves it: active-map-change bookkeeping, rather than current trigger flags alone, drives restoration. Clearing the ledger after the update makes 41/81 reload the base 00BD tile, while 01/control retain the raw 02D1 tile. This intentionally inconsistent control demonstrates why unrecorded RAM map changes can disappear. Raising and then lowering through two native updates leaves ledger 03 and tile 00BD; all modes preserve the final lowered state and ledger. This specifically rules out accidentally restoring the earlier raised bridge in this tested history.

Location positive controls: Prologue location IDs 3 (village at 49,7) and 2 (Evans) were changed using documented location RAM state bits. Destroyed village uses state 08, closed village 20, and changing Evans owner to player uses owner 0. Native location update produces respectively six ruined village tiles, one closed village tile, and one changed castle banner tile compared with the original map. All modes preserve the applied 64x64 terrain image and the complete 16-byte location-state table. No resurrection/reopening or ownership reset was observed. This tests stored ruined/closed states, not burn timers/animations or rewards.

Deployment arrays: all 72 deployment slots were compared for state, X/Y tile coordinates, unit references and faction. No differences occurred in any persistence scenario. Hidden test sets Hidden (0040) alongside Alive (0080) in slot 71 state and buffered state at frame10; snapshot15 and snapshot350 both retain 00C0 for all modes. Synthetic relocation sets slot71 tile coordinates to (58,14) and pixel coordinates to (928,224); those tile coordinates persist. This is an isolated deployment-table probe and does not certify all private character-coordinate fields, animations, guards or unit statistics.

Native coordinates/symbols: aMapData WRAM 7F2400 (64x64 words); bridge (12,15) at 7F2B98; active-change ledger 7E4EA5; chapter temporary-flag byte 7E52C4; locations 7E4E45; deployment tables 7E438B onward. Traces/captures and summaries: persistence_matrix.py / persistence-summary.json; unit_matrix.py / unit-persistence-summary.json; history_matrix.py / bridge-history-summary.json. Summary assertions check locations, deployment fields, bridge tiles and ledger transitions. Input ROM hash remains unchanged.

Conclusions apply to this initialized Prologue state. Other chapters, castle guard assignments, destroyed castles, scripted movement in flight, and location money/visit rewards remain untested. Modes stay read-only; the result is evidence about preservation, not a universal safety guarantee.

## Chapter 6 and moving-sprite follow-up

28 targeted runs:8 Chapter6 (terrain marker/destroyed village x control/01/41/81),8 initial Prologue motion (moving/halted x four modes),8 extensions to2000 frames,4 finished-route controls. Chapter6 uses a copied/decompressed existing Seliph savestate. Button0 (B) closes the status screen; screenshot baseline frame500 and chapter ID6 confirm a real map. An initial wrong-button preparation remained on the status screen and was discarded. The original ROM and source savestate remain read-only.

Chapter6 explicitly activates a controlled script at5E9000 using lActiveEventPointer/offset and event-active flags1. This is harness setup, not normal chapter event editing. Native interpreter progress was traced. A terrain marker at7F2400 survives01 but reloads to035A with41/81, agreeing with Prologue. Native location update applies ruined-village state to location5. All modes preserve prepared terrain/location states and deployment states, X/Y, references and factions across72slots. Four existing guards (slots20,44,65,66) retain guard bit004. This confirms guard-state preservation, not guard assignment, seizing or battle behavior. Chapter6 has no map-change entries, so it cannot independently validate bridge ledger behavior.

Motion script uses native character-sprite registration4A49(character1), temporary movement27 from(20,20),speed1,blue2,route5E9800,wait decompressed29. Moving route:Right10,End; halted route:Right1,Halt,Down4,End. Moving case waits10ticks before transition; halted case uses2A to wait for Halt. Then transition, yield,Continue2B,yield,Wait2A,yield,long1000tick pause. Control substitutes FD FD for3Bxx. Per-frame sprite traces record all active references and route/position bookkeeping.

At2000frames controls complete and clear all references. Moving control reaches(480,320); halted control reaches(336,384). All transition variants01/41/81 leave an active reference001E in slot4: moving cases stop near(323,320), halted cases at(336,320), and the later2A wait never clears within2000frames. Continue2B does not recover them. Event offset27(moving) or25(halted) points at the instruction after that wait's yield; the wait process blocks execution of the following pause. This is a tested stall, not an infinite-time proof.

Finished-route positive control usesRight1,End and2A BEFORE transition. All four modes clear references and advance beyond the later movement wait to the long pause (offset29 atframe800). Mode81 leaves brightness dark as expected. Thus deployment-data preservation does not imply temporary animation preservation. Practical rule: finish temporary routes at End before Map Transition; Halt alone is insufficient in these tests.

Scripts/summaries: chapter6_matrix.py/chapter6-summary.json; motion_matrix.py/motion-summary.json; motion_followup.py/finished-summary.json; motion-*-long traces and sprite-trace.json. Output assertions check actual chapter, terrain reload, unchanged location/deployment state, guard bits, completion of controls and orphan references in interrupted cases. Other chapters, guards during a fight, rewards and every possible movement process remain untested.

## Final focused matrix: Chapter1, dialogue, camera, repetition and player control

20 distinct scenario/mode combinations: Chapter1 recorded forest opening, dialogue queued without yield, camera scroll queued without yield, three sequential repeated transitions, and properly yielded dialogue then camera then transition. Each runs control/01/41/81; mode81 has an explicit fade-in after its transition so return-to-control is testable. One overlapping81 dialogue case was additionally extended to6000frames. The initial20 runs sent A after some events had completed, accidentally opening menus; these runs were discarded and all20 repeated with corrected input policy. Runner event_only_a only sends configured A presses while event flags are nonzero; non-dialogue cases have no A presses at all. Right and Down occur at1100/1200. This correction prevents equating an open menu with a broken transition.

Chapter1: existing objective-testing transition state is advanced through opening skip to an actual Chapter1 map, then600 more frames to settle the phase banner. Controlled custom script activates through pointer/offset/event flags1. Temporary flag6 (Open Forest) is set, active-map-change ledger cleared, native update4A5C applies two tiles at(14,43)/(14,44). Before and after each mode, both are0112 and ledger is01. This is a second chapter with recorded terrain changes, distinct from the Prologue bridge. All four cases complete and accept directional input.

Dialogue: synthetic native dialogue at5E9900 encodes Left/OpenBox/Portrait0001/Start/Transition test./Wait/End through the production text codec. Queued cases deliberately place3B directly after0C(pointer) without FD yield. Control,01,41 complete under scripted A input.81 leaves brightness0,event flags5 and offset7, unable to reach its following explicit fade-in. Extending to6000frames with ongoing A presses did not recover it. Screenshot remains black. This is an intentionally unsafe overlap, not a normal correctly-yielded dialogue sequence. The sequential case uses FD after dialogue and FD after camera; all modes complete, reveal and accept directional input.

Camera: ordinary40 scroll targets(48,10),speed1. It is queued before transition in the overlap cases. All four cases complete and accept cursor movement. At frame1000 the no-transition camera target is pixels(768,160); modes01/41/81 queued results are(768,64). In the properly yielded dialogue+camera case, control/81 retain(768,160), while01/41 end at(768,64). Thus native map setup can recenter the view: completion does not guarantee retention of the exact camera target. Use explicit camera placement after transition if required; this matrix does not certify every scripted scroll mode.

Repeated: three transitions with a yield and20tick pause between each;81 additionally fades in each time. All variants reach event flags0,brightness15 and directional input changes cursor offsets from(192,144) to(224,160). Across all20 cases, only queued dialogue+81 fails the completion/control assertions. This is evidence for the tested sequences, not a universal safety guarantee.

Reproduction retained locally: final_matrix.py, runner.py (including event_only_a), final-summary.json, per-case ROM/config/captures/traces, chapter1-ready preparation outputs and dialogue-overlap-long follow-up. Do not distribute generated ROMs or savestates. The small source-free report may be shared separately. Original input ROM and savestates remained unchanged.

Practical constraints now supported: finish temporary sprite routes at End; yield for dialogue completion before transitioning; yield for camera movement when ordering matters; explicitly fade in after leave-dark mode; expect native recentering; keep proper map-change/location state for terrain persistence. Broader chapter coverage and every runtime interaction are still outside the test scope.

## Limited editor implemented after the research

The supported Prologue command editor now edits four Map Transition instances through two packed controls. Fade interval accepts1-63 for new values; original0 can be retained. Modes0/1/2 correspond to raw high bits00/40/80. Existing combined C0 bits can be preserved, but cannot be newly selected; bit80 dominates them natively. Both controls update one operand byte while preserving the opcode and surrounding event layout. No dialogue, wait, route or fade-in commands are inserted automatically.

The editor shows sequencing and timing explanations and the resulting packed parameter. Failed saves restore memory; original-ROM saving includes backups/undo/redo. Tests cover all four references, headered/headerless layouts, shared-byte masks, every exposed mode, interval boundaries, stale snapshots, preserving legacy0/C0, invalid values, GUI warnings and save rollback/history.

Three additional emulator smoke runs generated ROM copies through production EventCommands.write rather than direct raw patching. Native mode/state results matched all three choices: mode0 -> map state0,brightness15; mode1 ->state2,brightness15; mode2 ->state3,brightness0 atframe400. These use the same controlled re-entry state as the earlier map matrix; they are integration smoke checks, not extra chapter coverage. Raw traces remain in research/event-3b/production-mode-* and production-summary.json. Original ROM unchanged.
