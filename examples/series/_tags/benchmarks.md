# tag: benchmarks

When an item or article carries the `benchmarks` tag, treat every number as a
measurement with a method, not a fact on its own. State the eval setup before
the score: everything another engineer would need to reproduce it and get the
same number. Then name the failure mode that actually threatens this
measurement, and go looking for the one the authors had the most reason not to
mention. A number without its harness is a rumor. Report it as one or not at
all.
