---
name: dumb-fighter-test
description: Run the Dumb Fighter Test on a Vogelfrei dungeon or adventure: eight all-10-stat Mercenary fighters follow a fixed random, no-clever-solutions procedure to check whether the adventure punishes intelligent play. Use whenever the user names this test, asks for a dumb/basic fighter probe, or wants to compare a mindless party's result with real players.
---

# Dumb Fighter Test

Run a fully adjudicated expedition, not a thought experiment. Act as the
Referee; the party's decisions come only from the script below. The test asks
one design question: **does the adventure punish clever players?**

## 1. Establish the run

- Read the complete adventure, including its map, keyed encounters, hidden
  features, treasure, hazards, and completion condition. Keep hidden
  information out of party decisions: the fighters know only what they have
  perceived or found through the procedure.
- Get the character level from the request or prior context. Ask if it is
  missing. The current Warrior rules support levels 1–6; ask how to proceed
  rather than extrapolating beyond them.
- Use the adventure's stated success condition. For a pure treasure dungeon
  without one, success means returning to the entrance alive after filling
  every surviving fighter's backpack with treasure. State the condition used.
- Obtain a real-player result if available. It is necessary for the
  comparative verdict; its absence does not prevent the simulation.
- Use a seeded random-number generator for every random choice and die roll.
  Record the seed and consequential rolls. Run once unless multiple runs were
  requested; for multiple runs, fix all seeds beforehand and report every
  result rather than selecting one.

## 2. Build the control party

Create **eight identical Warrior (Mercenary) fighters** at the specified
level. Set every ability score to exactly **10**, with no swaps, rerolls,
personalities, or optimisation. Derive Wounds, Stamina, saves, WS, BS, and
other statistics from the current Vogelfrei rules. Apply the Mercenary's
weapon-switching trait. Spend post-level-1 Combat Skill Points alternately on
WS and BS, starting with WS, unless the user supplied another fixed template.

Unless the user supplies a premade kit, give every fighter:

- Polearm, light crossbow, quiver with 20 bolts, and minor weapon (dagger).
- Buff coat and travelling clothes.
- Backpack, six torches, tinderbox, 50' rope, crowbar, waterskin, and one
  day's standard rations.

Track ammunition, light, time, rest, encumbrance, storage, Wounds, and Stamina
under the normal rules. Do not add supplies or equipment during the run except
through play.

## 3. Explore by depth-first search

Enter through the **main entrance**. At every junction, choose uniformly at
random from the known unexplored exits. Continue depth-first; backtrack only
when the current branch has no unexplored exits, then return to the most
recent junction that still has one. A dangerous-looking route remains in the
random pool.

In every entered room, after resolving immediate encounters, search for both
treasure and secret doors using the normal search rules. Do not add trap
searches, listening, repeated searches, or other precautions.

Apply these encounter and interaction rules:

- Open every encountered door immediately. Force locked or stuck doors and
  every locked chest; never pause to listen, inspect, or find a smarter opening
  method.
- Fail every puzzle and riddle immediately and apply the consequences. No
  random guessing, experimentation, or outside knowledge can solve one.
- For an interactive object, choose randomly from the interactions explicitly
  offered by the adventure or item description. Skip options whose danger is
  obvious, such as jumping into a lava pool. Invent no additional uses.
- When a cliff, underwater tunnel, or similar route is randomly selected, each
  fighter with an obviously useful item, such as a flight or water-breathing
  potion, consumes it and attempts the route. Choose randomly among applicable
  items. The rest wait until those fighters return or die. If nobody has a
  usable item, treat that branch as exhausted and backtrack.

## 4. Fight without tactics

Attack every living thing immediately. The fighters never negotiate, surrender,
or flee from ordinary danger. Use only the following combat behaviour:

- Surround targets whenever space and movement allow.
- When several enemy groups are present, choose the target group randomly;
  choose individual targets randomly rather than by weakness or threat.
- Use polearms from the second rank when available. Missile weapons are
  allowed. Resolve the normal risks of firing into melee rather than avoiding
  them through targeting choices.
- Do not add aiming, bracing, defensive fighting, called shots, retreats,
  morale decisions, or other tactical plans. Apply mandatory rules and the
  Mercenary trait normally.

A clearly unbeatable, godly entity is the sole combat exception. If the
adventure provides clear interactions with it, choose one randomly. If it
provides none, try to run away. Do not relabel an ordinarily powerful monster
as godly to escape fighting it.

## 5. Use and loot items mechanically

- Drink every potion immediately when found, in random order if several are
  found together. The exception is a known potion with no combat purpose and
  no mobility use: leave it alone.
- At the start of each combat, every fighter with an applicable consumable
  rolls **1 in 6**; on success, use one randomly selected applicable
  consumable.
- Whenever a fighter dies, every other surviving fighter with an applicable
  consumable rolls **3 in 6**; on success, use one immediately. Choose random
  legal targets, but never target another party member. A wand is aimed at an
  enemy or another valid non-party target, never at a fighter.
- A fighter below 50% of maximum Wounds drinks an available healing potion,
  repeating until above 50% or no healing potions remain.

Wear any found equipment immediately, replacing the current item in that slot
without comparing quality or checking for curses. Leave obviously huge objects,
such as whole statues, behind. Load other treasure into available backpacks
without optimising value or arrangement. A backpack is full when its actual
storage capacity is exhausted; do not substitute an arbitrary coin total.

## 6. Handle NPCs and separation

- Allow every recovered human NPC who can accompany the party to do so. This
  is the exception to attacking living things on sight. Recovered NPCs follow
  the same combat script and provide no puzzle answers, plans, or warnings.
- If the party separates, retrieve lost members only when an immediately
  available method can do so within **1–2 Turns**, such as helping someone out
  of a pit. Otherwise, leave them and continue as separate groups.
- If a fighter is teleported or forcibly moved, the rest follow through the
  same mechanism. For other separations, split the party and run each group
  independently under the same rules.

## 7. Retreat only on the scripted conditions

When every surviving fighter's backpack is full of treasure, return to the
entrance by the known route. When every surviving fighter is at **4 or fewer
Wounds**, do the same. Otherwise continue looting and exploring. These
retreats, and the godly-entity exception, override the usual no-flee and DFS
rules. Combat and hazards encountered on the way out still apply.

## 8. Reach the verdict

Compare like with like: the same adventure, objective, and relevant real-player
outcome. Do not turn the result into a general difficulty rating or redesign
review.

- **Dumb party outperforms real players:** flag possible intelligence-punishing
  design. State that, under this test, either the real players performed worse
  than the fixed script or the adventure punishes intelligence. Cite the
  specific outcomes behind the comparison.
- **Dumb party succeeds without a real-player comparison:** conclude only that
  the adventure can be overcome by the scripted party. The
  intelligence-punishing question remains unresolved.
- **Dumb party does not outperform real players:** this run provides no
  evidence that the adventure punishes clever players.
- **Dumb party fails:** record the failure; by itself it says nothing about
  whether clever play is punished.

End with this compact report:

```markdown
# Dumb Fighter Test: <adventure>

**Verdict:** <possible intelligence-punishing design | no evidence from this run | unresolved without real-player result>
**Dumb-party result:** <success/failure/partial, one sentence>
**Real-player result:** <supplied result or "not supplied">
**Setup:** level <N>; seed <seed>; eight Mercenaries; <default/custom kit>
**Run record:** <survivors, rooms explored, treasure, and decisive events>
```

Keep the verdict limited to the intelligence-punishing question. The run record
is evidence, not a second set of conclusions.
