# tag: hardware

When an item carries the `hardware` tag, ground the discussion in the physical
GPU, not the abstraction above it. Reason in the memory hierarchy (HBM, L2,
shared memory/SRAM, registers) and the roofline: is this work bound by memory
bandwidth or by compute, and what is its arithmetic intensity? Quantify with
the real numbers, each cited: bytes moved, achieved versus peak bandwidth,
occupancy, tokens or FLOPs per second on named silicon. A claim that something
is "fast" or "efficient" is not analysis until it names the bottleneck it
relieves and by how much.
