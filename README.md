# ai_scribe
Randomization of FFVI AI scripts

Requires `numpy`, `networkx`, and `pandas` libraries at a minimum.

Run with:
```bash
python -m ai_scribe
```

## Resources

This program makes use of the Cecilbot data files, which can be found on the Beyond Chaos discord and are maintained by Cecil188.

## TODO

### Batch 7

 - [x] Save filename with original + 'batch_number.seed_number'
 - [x] Fix the script shortening bug with adding 0xFF to disallowed_commands
 - [.] Suppress Escape
   - Alternatively, could just reduce its weight
 - [] Suppress target self
 - [] Add 0xFC subflag byte to translate
 - [] Check on Whelk randomization
   - [ ] Don't randomize alter formation?
 - [x] Cyan = "3" add him in the area
 - [] Enlengthen the counter block programmatically
 - [] See if you can manually increase early area MP pools
   - https://www.tales-cless.org/ff6hack/#part5
 - [] separate out the main and counter block predicates
 - [x] remove same special events as BC
    - [x] Fix Merchant event removal
    - [] Fix ZoneEater event removal
 - [x] randomize boss messages
 - [x] Fix Kefka alias mixup
 - [] Command / message themes: take Cactuar and "build up" script monsters together
 - [] Consider how much you really want to randomize 0xF5 in boss scripts
 - [] See if there's a way to hide stronger skills behind conditionals more often

### Batch 8

 - [ ] Look at TunnelArmor in seed 0, did desperation attack
 - [ ] Check graph connections when themes are added
 - [ ] Tusker doesn't do all its attacks
 - [ ] Probably need to have "fused" commands read on parsing
 - [ ] theme only single enemy
 - [ ] generate from template with theme
 - [ ] Can we cluster "similar" command structures?
   - Graph similarity?
   - Cluster by edit distance: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.similarity.graph_edit_distance.html#networkx.algorithms.similarity.graph_edit_distance
   - have `from_template` expand with similar scripts
