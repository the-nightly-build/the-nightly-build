# tag: benchmarks

When an item or article carries the `benchmarks` tag, treat every benchmark
number as a measurement with a method, not a fact on its own. State the eval
setup before the score: the baselines compared against, the hardware,
precision, batch size, and sequence lengths. Flag the usual failure modes by
name when they apply: training-set contamination, cherry-picked configs,
apples-to-oranges baselines, and metrics that miss what the reader actually
cares about. A number without its harness is a rumor; report it as one or not
at all.
