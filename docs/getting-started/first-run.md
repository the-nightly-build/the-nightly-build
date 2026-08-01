# Run the first article

The first run is a capability and editorial test. Run it in the
exact environment that will execute the schedule, not in the setup chat or a
different local shell.

Before triggering it, keep `autopublish: false` on the series used for the
test. The run must:

1. Check out current `main` and `library` state.
2. Run `nb sync` and `nb duty` successfully.
3. Reach real web sources from the scheduled runtime.
4. Complete the editorial roles and their recorded artifacts.
5. Push a generated branch and open a real Article PR against `library`.
6. Pass the full proof and rendered-browser check in CI.

Review the article and its rendering. If it misses editorial intent, improve
the press and run the test article again. If a capability fails, fix only that
boundary and resume from it; do not silently substitute the setup environment.

Setup is ready only after the scheduled runtime returns a passing PR. Merge it
manually. Enable `autopublish: true` per series only when you trust both its
editorial output and its operating boundary.
