# Classics

Reference replications of landmark experiments, each a standalone alhazen project built
from the original paper's methods section. Each folder's `docs/listing.json` states its
status (`original-protocol`, `adaptation`, `demo`), and its `docs/methods.md` lists the
deviations from the original and every assumption the paper did not state. None of them has
recorded participant data: tests and simulated sessions verify the software only.

A folder whose `docs/listing.json` says `"listed": false` is **unlisted**: its code, tests and
documentation stay here and it runs like any other folder, but the Alhazen Experiment Platform
does not list it (a platform's classics sync skips it and takes an earlier listing of it off
Browse; copies people already made keep working). Set it back to `true` to list it again.

| Experiment | Original | Status | Hardware beyond a display | Deviations | Assumed, not in the paper |
|---|---|---|---|---|---|
| [Stroop color-word interference (Stroop, 1935), trial-wise by key](stroop-1935/) | 1935 | `adaptation` | keyboard | 8 | 17 |
| [Sperling partial report (Sperling, 1960, Experiments 3 and 4)](sperling-1960/) | 1960 | `adaptation`, unlisted | keyboard | 11 | 30 |
| [Sternberg memory scanning](sternberg-1966/) | 1966 | `original-protocol` | keyboard | 5 | 30 |
| [Mental rotation of 3-D objects](shepard-metzler-1971/) | 1971 | `original-protocol` | keyboard | 7 | 28 |
| [Posner spatial cueing](posner-1980/) | 1980 | `original-protocol` | keyboard, eye tracker | 4 | 27 |
| [Feature vs conjunction search](treisman-gelade-1980/) | 1980 | `original-protocol` | keyboard | 7 | 40 |
| [Oculomotor delayed response](funahashi-1989/) | 1989 | `adaptation`, unlisted | keyboard, eye tracker, reward | 7 | 14 |
| [Motion coherence discrimination (Britten et al.)](britten-1992/) | 1992 | `adaptation` | keyboard, eye tracker, reward | 13 | 34 |
| [Attention-based motion (Cavanagh)](cavanagh-1992/) | 1992 | `adaptation` | keyboard | 5 | 49 |
| [Attentional blink (Raymond, Shapiro & Arnell, 1992, Experiment 2)](raymond-shapiro-arnell-1992/) | 1992 | `original-protocol` | keyboard | 6 | 25 |
| [Flicker change blindness](rensink-oregan-clark-1997/) | 1997 | `adaptation` | keyboard | 8 | 34 |
| [Saccade planning and attention (Moore & Fallah)](moore-fallah-2001/) | 2001 | `adaptation`, unlisted | keyboard, eye tracker, reward, microstimulation | 7 | 32 |
| [FEF microstimulation gating (Moore & Armstrong)](moore-armstrong-2003/) | 2003 | `demo`, unlisted | eye tracker, reward, microstimulation, recording | 7 | 30 |
| [Double-drift: perception vs saccades (Lisi & Cavanagh 2015)](lisi-cavanagh-2015/) | 2015 | `original-protocol` | keyboard, eye tracker | 7 | 38 |
