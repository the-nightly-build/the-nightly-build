# Voice guide: Kernels

## How this piece should sound

Write as a working kernel engineer teaching a peer. The reader is fluent in
deep learning and new to the GPU, so they can carry a hard idea and will not
forgive a paragraph that restates the previous one. Explain the machine. Never
explain the reader's inexperience.

Say what you think of a number in the same breath as the number. Boehm calls a
result "pretty bad" and has justified it by the end of the next sentence. A
lesson can do the same: give the reading, then the comparison that makes it a
reading, and do not save the assessment for a conclusion.

Build one picture and keep returning to it. He runs a factory and a warehouse
across his whole piece, naming a real quantity inside each part of it, so the
bandwidth costs that arrive much later land somewhere the reader already has.
Choose that picture before drafting and check it survives the hardest section.
An analogy introduced once and abandoned is worse than none.

Report what did not work. Boehm spends a sentence on an optimization he removed
and names the cause he suspects. This matters more in a lesson than in a
worklog, because a reader who sees only the choices that worked cannot tell
which of them were forced.

Put the warning where the reader will actually fail. Rush says the code looks
like Python but is really CUDA at the moment before someone reaches for a list
comprehension, not in a preface about how the languages differ. Find the place
this lesson's reader will use an old habit, and interrupt them there.

Prefer the concrete noun to the category. A warp, a bank conflict, and a store
to global memory happen at an address, so write them that way. When a number
decides the argument, put the number in the sentence rather than gesturing at a
benchmark below it. Keep the technical vocabulary in the prose. A lesson that
avoids it to stay accessible ends up sounding written from a distance.

## Simon Boehm, "How to Optimize a CUDA Matmul Kernel for cuBLAS-like Performance: a Worklog"

```text
Source: https://siboehm.com/articles/22/CUDA-MMM

"Pretty bad, considering that the A6000 is advertised as being able to achieve
almost 30 TFLOPs. Just for comparison, 300 GFLOPs is also roughly the
performance achieved by the optimized BLAS library on the 2015 Haswell CPU that
I used in my earlier post on CPU matmul."
He gives his opinion of the number before the evidence for it, and the evidence
lands in the next sentence. "Pretty bad" is how an engineer actually talks about
their own result, and it sits inside a sentence that is exact about the
hardware.

"I like to think of the three dimensions x,y,z of threadId as being
"column-major", due to the first dimension x being the one that's continuous in
"warpspace". I don't know if others use that term, but it makes the concept
more clear to me."
He offers a private mental model and admits it may be his alone. The reader gets
the idea and its standing at once, and nothing is dressed up as established
usage. A writer who says where a framing came from is easier to trust on the
things they then state flatly.

"It didn't increase performance, presumably because L2 hit rate is already
fairly high at 80%, so I ended up removing the swizzling code."
He spends a sentence on an optimization he threw away, and gives the cause he
suspects without claiming to have proved it. A reader who sees only the changes
that worked cannot tell which of them were forced.
```

## Horace He, "Making Deep Learning go Brrrr From First Principles"

```text
Source: https://horace.io/brrr_intro.html

"Hey! This is a very stupid arrangement. Why are we sending the same data to
global memory and then back to the compute units, over and over? We should just
keep the data at the factory, perform all of our compute, and then send it
back!"
He interrupts his own explanation to react to it. The reader has just been shown
a diagram and is thinking exactly this, and he says it first, in the words
someone would use out loud. The exclamation marks carry it. The same words set
flat would read as analysis.

"On the other hand, if you're spending all of your time performing big chonky
matmuls (i.e. a compute-bound regime), then rewriting your model logic into C++
to reduce overhead won't help."
"Big chonky" sits inside a sentence that is otherwise exact, next to a
parenthetical giving the formal term. He does not choose between sounding like
a person and being correct.

"One way to think about compute is as a factory. We send instructions to our
factory (overhead), send it materials (memory-bandwidth), all to keep our
factory running efficiently (compute)."
He builds one picture and names each real quantity inside it, so the analogy is
load-bearing from the first sentence. He returns to the factory when bandwidth
costs arrive much later, and by then the reader has somewhere to put them.
```

## Abhinav Upadhyay, "What Every Developer Should Know About GPU Computing"

```text
Source: https://blog.codingconfessions.com/p/gpu-computing

"If you like numbers, let's talk about numbers. The performance of hardware for
numerical computations is measured in terms of how many floating point
operations it can do per second (FLOPS)."
He announces the turn toward hard figures instead of sliding into it, and he
does it in a friendly voice. The reader gets a moment to decide how closely to
read, which is a small courtesy most technical writing skips.

"CPUs dedicate a significant amount of chip area towards features which will
reduce instruction latency, such as large caches, less ALUs and more control
units. In contrast, GPUs use a large number of ALUs to maximize their
computation power and throughput. They use a very small amount of the chip area
for caches and control units, the things which reduce the latency for CPUs."
Two long clauses set the contrast and a shorter third closes it by repeating the
exact terms from the first. Nothing is renamed on its second appearance, so the
reader tracks one comparison rather than two.

"So, why can't we always reach 100% occupancy? The SM has a fixed set of
execution resources, including registers, shared memory, thread block slots, and
thread slots."
He asks the question the reader has just formed and answers it immediately.
Putting it in the reader's voice, with "we", makes the constraint arrive as
something they worked out.
```

## Sasha Rush, "GPU Puzzles"

```text
Source: https://github.com/srush/GPU-Puzzles

"It is hard to gain intuition working through abstractions. This notebook is an
attempt to teach beginner GPU programming in a completely interactive fashion.
Instead of providing text with concepts, it throws you right into coding and
building GPU kernels."
He says plainly what he is trying and owns it. "An attempt" is an unusual word
to use about your own teaching material, and a reader who is told that much is
willing to be thrown in.

"This code looks like Python but it is really CUDA! You cannot use standard
python tools like list comprehension"
A warning written the moment before the reader would have hit the wall, in the
place they will actually be looking. He knows exactly which habit is about to
fail and stops it on the spot, instead of filing it in a general note about how
the two languages differ.

"If you get an error it is probably because you did something fancy :)."
He tells the reader their error is expected and slightly their own fault, and
the smiley keeps it warm, so the puzzles read as an invitation instead of a
test.
```
