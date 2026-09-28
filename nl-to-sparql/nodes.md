# notes for indexing

- rerunning indexing when already indexed hangs long time, and just reruns the indexing
- ctrl+c before indexing finished creates partially finished state, should be atomic
- if indexing fails before finishing, it leads to partial data. rerunning the indexing doesn't get rid of previous garbage, just adds to it

