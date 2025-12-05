"Prison Break" by Lore Lock

The Damp Stone Cell is a room. "You wake up on a hard slab in a damp stone cell. The air is cold and smells strongly of brine and mold. [if the iron bars are closed]Iron bars block the north exit[end if]. The only other object is a cracked, moss-covered Stone Slab near your feet."

The Corridor is a room. "A dimly lit corridor, silent except for the drip of water. Torches flicker weakly on the walls."

The iron bars are a door. The iron bars are north of the Damp Stone Cell and south of the Corridor. The iron bars are locked.
The description of the iron bars is "Thick iron bars blocking the way. [if locked]They appear to be locked[end if]."

The rusty shiv is a thing. The rusty shiv unlocks the iron bars.
The description of the rusty shiv is "A jagged piece of metal, sharp enough to cut but not meant for heavy fighting."

The stone slab is a thing in the Damp Stone Cell. "A cracked, moss-covered Stone Slab lies near your feet."
The description of the stone slab is "It seems loose. You might be able to move it."
The stone slab is pushable.

Instead of pushing or pulling or turning the stone slab when the rusty shiv is off-stage:
    move the rusty shiv to the location;
    say "You shift the heavy stone slab. Underneath, you discover a rusty shiv!";
    now the stone slab is fixed in place.

[Flavor for the slab]
Instead of attacking the stone slab:
    say "It's stone. You'll only hurt your hands."

[Flavor for the bars - representing the High DC]
Instead of attacking or breaking the iron bars:
    say "The bars are solid iron. You can't break them."

Test me with "examine slab / push slab / take shiv / unlock bars with shiv / open bars / north".
