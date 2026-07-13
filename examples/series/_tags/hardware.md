# tag: hardware

When an item carries the `hardware` tag, ground the analysis in the physical
GPU, not the abstraction above it. Reason in the memory hierarchy (HBM, L2,
shared memory/SRAM, registers) and the roofline: is the work bound by memory
bandwidth or by compute, and what is its arithmetic intensity? Quantify and
cite each figure: bytes moved, achieved versus peak bandwidth, occupancy,
tokens or FLOPs per second on named silicon. "Fast" and "efficient" are not
analysis until the sentence names the bottleneck relieved and by how much.
