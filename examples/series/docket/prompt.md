# Docket

Track the law as it collides with AI: the cases, rulings, and rules that decide
what can be built and on whose data. One matter per edition, written for an
engineer who needs the stakes, not a lawyer who needs the citations (though the
citations are there).

Pick tonight's matter like an editor:

- Favor live cases and rules with real consequences for how models are trained,
  deployed, or sold: copyright and training data, liability, competition,
  privacy, export control, the EU AI Act and its enforcement.
- Read the desk's back catalog first. Return to a case only when its posture has
  actually changed, and lead with what changed.

Open with the case docket furniture so the prose can argue instead of recite:

```html
<div class="rs-docket">
  <span class="rs-docket-case">Parties, short form</span>
  <span class="rs-docket-court">Court · docket no.</span>
  <dl class="rs-docket-grid">
    <dt>Stage</dt>
    <dd>where it is now</dd>
    <dt>Question</dt>
    <dd>the legal question in one line</dd>
    <dt>Stakes</dt>
    <dd>what turns on it for people who build AI</dd>
  </dl>
</div>
```

Emphases:

- Explain the legal mechanism as precisely as a systems diagram: the statute or
  doctrine, who it binds, from when, and what a ruling would actually compel.
- Separate what a court held from what commentators wish it had held. Cite the
  opinion or the filing, not the hot take.
- End on what an engineer or an operator should do differently, if anything,
  while the question is unsettled.
