# Open design questions

Things noticed while fixing rules inconsistencies that need a design decision,
not a correction.

## The zweihander problem

The **Great** weapon category covers "two-handed swords, mauls, and great axes"
as one line: d10, length 4, 50sp.

That flattens a real distinction. A zweihander takes genuine instruction to use
and is useless for forcing a door. A greataxe needs far less training and will
happily chop one down — the Doors rule explicitly calls for "some sort of axe
for a wooden door". Both are Great weapons, so the rules cannot currently tell
them apart.

Options, none applied:

- Split **Great** into two entries (bladed vs hafted) with different asterisks
  and door-breaking behaviour.
- Keep one line and hang the difference off the *specific* weapon the player
  names, since the generic categories already require naming an actual weapon.
- Add a small weapon-property tag set (`*` for training, something for
  door-breaking) and let each named weapon carry its own tags.

## Smaller open items

- **Spear and Lance still carry the `(1/2H)` split** (d4/d6 at length 4/5, and
  d10 at length 5). Medium was collapsed to a flat d8 as instructed; these two
  were left alone because the Spear's two-handed mode has a distinct rules hook
  (attack from the second rank, receive a charge). Worth deciding whether they
  should collapse too.

- **Halflings.** "Halflings must wield Medium Weapons in two hands" became
  meaningless once Medium stopped splitting by hands, so the line now reads
  only "Halflings cannot wield Great Weapons." If the intent was a real
  restriction on Halflings and Medium weapons, it needs restating.

- **Which melee weapons carry the training asterisk.** Currently: Rapier,
  Garrote, Mancatcher, Whip, Weighted Net, Lance. All ranged weapons and all
  firearms are covered by a blanket note instead of per-row asterisks. Adjust
  the melee list to taste.

- **Blessing names.** Blessings 3 and 18 are still called *Charisma* and
  *Wisdom*, stats the game does not have. Their effects (+1 Leadership, +1
  Intelligence) are correct and were left alone; only the names are odd.

- **Firearms ignore 5 Armor Rating at short range** (Muskets and Long Rifles at
  any range) when the best armour in the game is AR 6. Deferred by request.

- **Status is unset on 49 of 66 career pages**, so those characters cannot roll
  starting money. Deferred by request.
