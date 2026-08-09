# Voice guide: Kernels

## How this series should sound

Write as a working kernel engineer teaching a peer. The reader is fluent in deep
learning and new to the GPU, so they can carry a hard idea and will not forgive
a paragraph that restates the previous one. Describe the machine, and leave the
reader's inexperience out of it.

Give your assessment of a number in the sentence that reports it. Boehm calls a
result "pretty bad" and puts the figure that justifies the verdict in the same
sentence. A lesson can work the same way: report the measurement, say what you
make of it, and do not hold the assessment back for a conclusion.

Build one picture and keep returning to it. Horace He runs a factory and a
warehouse across his whole piece, naming a real quantity inside each part of it,
so bandwidth costs arriving many sections later have somewhere to go. Choose
that picture before drafting and check it survives the hardest section. If it
does not return, cut it.

Report what did not work. Boehm spends a sentence on an optimization he removed
and names the cause he suspects. A lesson needs this more than a worklog does,
because the reader is trying to learn which choices a problem forces.

Warn at the point of use. Rush's general note about Python and CUDA sits in his
introduction, but the specific warning about list comprehensions sits in the
puzzle where someone would reach for one. Find the place this lesson's reader
will use an old habit, and interrupt them there rather than in a preamble.

Ask the reader's question in their own words before answering it. Upadhyay
writes "So, why can't we always reach 100% occupancy?" at the moment a reader
has formed it. A lesson that answers questions nobody asked yet reads as a
specification.

Prefer the concrete noun to the category. A warp, a bank conflict, and a store
to global memory happen at an address, so write them that way. When a number
decides the argument, put the number in the sentence rather than gesturing at a
benchmark below it. Keep the technical vocabulary in the prose. A lesson that
avoids it to stay accessible ends up sounding written from a distance.

## Simon Boehm, "How to Optimize a CUDA Matmul Kernel for cuBLAS-like Performance: a Worklog"

Source: <https://siboehm.com/articles/22/CUDA-MMM>

> "Pretty bad, considering that the A6000 is advertised as being able to achieve
> almost 30 TFLOPs. Just for comparison, 300 GFLOPs is also roughly the
> performance achieved by the optimized BLAS library on the 2015 Haswell CPU
> that I used in my earlier post on CPU matmul."

He gives his verdict and the figure that supports it in one sentence, then
spends the next sentence on a second comparison. "Pretty bad" is how an engineer
actually talks about their own result, and it sits in a sentence that is exact
about the hardware.

> "I like to think of the three dimensions x,y,z of threadId as being
> "column-major", due to the first dimension x being the one that's continuous
> in "warpspace". I don't know if others use that term, but it makes the concept
> more clear to me."

He offers a private mental model and admits it may be his alone. The reader gets
the idea and its standing at once, and nothing is dressed up as established
usage. A framing whose origin is stated is easier to trust than one asserted.

> "It didn't increase performance, presumably because L2 hit rate is already
> fairly high at 80%, so I ended up removing the swizzling code."

He spends a sentence on an optimization he threw away, and gives the cause he
suspects without claiming to have proved it. "Presumably" marks the part he did
not establish, inside the sentence rather than in a caveat after it.

## Horace He, "Making Deep Learning go Brrrr From First Principles"

Source: <https://horace.io/brrr_intro.html>

> "Hey! This is a very stupid arrangement. Why are we sending the same data to
> global memory and then back to the compute units, over and over? We should
> just keep the data at the factory, perform all of our compute, and then send
> it back!"

He interrupts his own explanation to react to it. The reader has just been shown
a diagram and is thinking exactly this, and he says it first, in the words
someone would use out loud. Set flat, the same words would read as analysis.

> "On the other hand, if you're spending all of your time performing big chonky
> matmuls (i.e. a compute-bound regime), then rewriting your model logic into
> C++ to reduce overhead won't help."

"Big chonky" sits in a sentence that is otherwise exact, next to a parenthetical
giving the formal term. The informal phrase costs the sentence no precision.

> "One way to think about compute is as a factory. We send instructions to our
> factory (overhead), send it materials (memory-bandwidth), all to keep our
> factory running efficiently (compute)."

He builds one picture and names a real quantity inside each part of it, so the
analogy does work from its first sentence. He returns to the factory when
bandwidth costs arrive many sections later.

## Abhinav Upadhyay, "What Every Developer Should Know About GPU Computing"

Source: <https://blog.codingconfessions.com/p/gpu-computing>

> "If you like numbers, let's talk about numbers. The performance of hardware
> for numerical computations is measured in terms of how many floating point
> operations it can do per second (FLOPS)."

He announces the turn toward hard figures instead of sliding into it, and he
does it in a friendly voice. The reader gets a moment to decide how closely to
read, which is a small courtesy most technical writing skips.

> "CPUs dedicate a significant amount of chip area towards features which will
> reduce instruction latency, such as large caches, less ALUs and more control
> units. In contrast, GPUs use a large number of ALUs to maximize their
> computation power and throughput. They use a very small amount of the chip
> area for caches and control units, the things which reduce the latency for
> CPUs."

Three sentences hold one contrast, and the third repeats "caches and control
units" and "latency" from the first instead of reaching for synonyms. The reader
tracks one comparison the whole way.

> "So, why can't we always reach 100% occupancy? The SM has a fixed set of
> execution resources, including registers, shared memory, thread block slots,
> and thread slots."

He asks the question the reader has just formed and answers it immediately.
Putting it in the reader's voice, with "we", makes the constraint arrive as
something they worked out.

## Sasha Rush, "GPU Puzzles"

Source: <https://github.com/srush/GPU-Puzzles>

> "It is hard to gain intuition working through abstractions. [...] This
> notebook is an attempt to teach beginner GPU programming in a completely
> interactive fashion. Instead of providing text with concepts, it throws you
> right into coding and building GPU kernels."

He says plainly what he is trying and takes responsibility for it. "An attempt"
is an unusual word to use about your own teaching material, and a reader who is
told that much will go along with being thrown in.

> "**Warning** This code looks like Python but it is really CUDA! You cannot use
> standard python tools like list comprehensions or ask for Numpy properties
> like shape or size (if you need the size, it is given as an argument)."

The warning sits in the puzzle where the habit would be used, not in the
introduction where he covers the same ground generally. He names the exact
constructs that stop working rather than the difference between the languages.

> "If you get an error it is probably because you did something fancy :)."

He tells the reader their error is expected and slightly their own fault, and
the smiley keeps it warm, so the puzzles read as an invitation instead of a
test.
