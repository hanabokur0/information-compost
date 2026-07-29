# Protocol: The Compost Cycle

Version: `0.1.0`

The Compost Cycle is the minimal operating procedure of Information Compost.
It defines when to record, when to normalize, when to wait, and when to invite
reflection.

The protocol is intentionally small:

```text
Act
  ↓
Capture
  ↓
Normalize
  ↓
Pause
  ↓
Review
  ↓
Return
```

Its purpose is not to produce a conclusion after every event. Its purpose is to
preserve enough distance between action and interpretation that new thought can
still belong to the person who acted.

## 1. Protocol boundary

This protocol is for:

- preserving traces of completed or interrupted action;
- separating observed facts from later interpretation;
- reviewing one or more Receipts without turning them into a diagnosis;
- allowing a question, artifact, or small experiment to emerge after a pause.

This protocol is not for:

- real-time emergency decisions;
- medical, legal, financial, or safety-critical diagnosis;
- continuous behavioral surveillance;
- scoring a person's worth, character, or productivity;
- replacing consent with an automated recommendation.

When immediate action is required, use an appropriate operational or emergency
procedure first. Composting can happen later.

## 2. Roles

### Human

The human owns:

- whether an event should be recorded;
- which traces may be included;
- how long to pause;
- whether an interpretation is accepted, rejected, or left open;
- whether a question becomes a next action.

### Normalizer

The normalizer may:

- make field shapes consistent;
- normalize timestamps and identifiers;
- add declared defaults;
- validate the Receipt against the schema;
- reject unknown or unsafe structural input.

The normalizer must not invent facts or interpret personality.

### AI mirror

The AI mirror may:

- summarize evidence;
- distinguish facts, inferences, and unknowns;
- identify tentative repetition across Receipts;
- surface contradictions and missing context;
- draft non-prescriptive questions for human review.

The AI mirror must not silently convert a pattern into an identity claim or a
question into an instruction.

## 3. Stage A — Act

Live or work before optimizing the record.

The action may be deliberate, accidental, incomplete, ordinary, or apparently
unimportant. A Receipt does not require a major achievement.

Examples include:

- cooking a meal;
- abandoning a task;
- taking a walk;
- sending a proposal;
- buying an object;
- noticing physical fatigue;
- making, revising, or publishing an artifact.

### Guard

Do not reshape ordinary life merely to produce more impressive Receipts. The
archive should follow life; life should not become a performance for the
archive.

## 4. Stage B — Capture

Record the smallest useful trace soon enough that it is not lost.

At minimum, capture:

- when the action occurred;
- a short factual summary;
- at least one trace;
- any context that materially changes how the event could be understood.

A compact raw note is sufficient:

```yaml
occurred_at: 2026-07-29T18:30:00+09:00
summary: Walked to the supermarket after work.
notes:
  - Chose ingredients instead of prepared food.
context:
  energy: low
  weather: hot
```

### Capture rules

1. Prefer observable language.
2. Preserve uncertainty instead of filling gaps.
3. Separate bodily sensation from medical interpretation.
4. Keep source references when they may matter later.
5. Do not infer a stable personality from one event.

Compare:

```text
Observed: I reopened the document three times and did not edit it.
Inferred: I may have been avoiding the task.
Unknown: Whether fatigue, uncertainty, or another interruption was the cause.
```

The three statements belong in different fields.

## 5. Stage C — Normalize

Convert the raw note into the canonical Receipt structure.

```bash
python tools/normalize_receipt.py raw.yaml \
  --default-offset +09:00 \
  --output receipt.yaml
```

Normalization should make a Receipt easier to compare without changing what
happened.

A successful normalization may:

- create a stable Receipt ID;
- add the schema version;
- normalize date-time values;
- convert notes into typed traces;
- add empty uncertainty and reflection fields;
- validate the result.

### Normalization invariant

> Structural completion is allowed. Semantic invention is not.

If a required fact is missing, record it as unknown or return an error. Do not
manufacture a plausible value.

### Validation failure

When validation fails:

1. retain the raw input;
2. report the invalid field;
3. correct the structure or mark the missing value explicitly;
4. run validation again;
5. never discard a trace silently.

## 6. Stage D — Pause

Do not require immediate interpretation.

A pause may be:

- several deliberate breaths;
- a walk;
- sleep;
- the end of a work session;
- a day or week of waiting;
- an intentionally open state with no scheduled revisit.

Record the pause when useful:

```yaml
pause:
  status: completed
  method: walking
  duration_minutes: 20
  revisited_at: 2026-07-30T08:00:00+09:00
```

### Choosing the pause length

Use a short pause when the event is ordinary and emotionally neutral. Use more
distance when:

- the event is emotionally charged;
- the first explanation feels unusually certain;
- an AI-generated interpretation is immediately persuasive;
- more comparable Receipts are likely to arrive;
- no decision is actually required yet.

A pause is complete when the human chooses to revisit the material. It is not
complete merely because a timer expired.

## 7. Stage E — Review

Review one Receipt for local clarity or several Receipts for tentative patterns.
The default review tool is [`prompts/quiet_mirror.md`](../prompts/quiet_mirror.md).

### Single-Receipt review

Use a single Receipt to ask:

- What is directly supported?
- Which interpretation was added later?
- What remains unknown?
- Is there a question worth preserving?

A single Receipt is usually insufficient evidence for a repeated pattern.

### Multi-Receipt review

Use multiple Receipts when looking for repetition or change. A candidate pattern
should cite the Receipt IDs that support it and should remain provisional when:

- the sample is small;
- the Receipts cover only one context;
- counterexamples exist;
- the traces were generated from the same original source;
- the available period is too short.

### Review outputs

A review may produce:

- a clearer observation;
- a tentative repeated pattern;
- a contradiction;
- an explicit unknown;
- a question for the human;
- no finding at all.

“No supported pattern yet” is a valid result.

## 8. Stage F — Return

Return the review to life without turning it into an order.

The human may choose to:

- leave the Receipt open;
- correct an inaccurate interpretation;
- collect more traces;
- write a journal entry or story;
- extract a reusable work protocol;
- define a small next experiment;
- do nothing.

A next experiment should be small, reversible, and attributable to the human's
choice. The AI may help phrase it only when explicitly asked.

Example:

```yaml
reflection:
  status: reviewed
  observation: Evening cooking occurred on two low-energy days.
  repeated_pattern: null
  new_question: Does preparing one ingredient earlier change the evening choice?
  next_experiment: null
  non_prescriptive: true
  confidence: low
```

The question is preserved. No action has been assigned.

## 9. Completion criteria

One compost cycle is complete when all of the following are true:

- the original action and at least one trace remain recoverable;
- facts, inferences, and unknowns are distinguishable;
- the Receipt passes schema validation;
- any reflection is marked non-prescriptive;
- the human has reviewed, rejected, deferred, or left open the reflection;
- no automated conclusion has been mistaken for consent.

The cycle does not require a breakthrough, recommendation, or behavior change.

## 10. Minimal practice

For a first use, do only this:

1. Record one ordinary action.
2. Add one trace and one piece of context.
3. Normalize the file.
4. Wait until the next day.
5. Review it with the Quiet Mirror prompt.
6. Keep one question or explicitly keep none.

The protocol should earn complexity through repeated use. Do not add scoring,
classification, automation, or dashboards before the basic cycle produces
useful Receipts.

## 11. Revision rule

The protocol itself may change through practice.

When revising it, preserve:

- the reason for the change;
- the Receipt or failure that motivated it;
- the previous behavior;
- the new behavior;
- any new risk introduced by the revision.

Git history is part of the compost. A protocol change should remain traceable to
the experience that made the change necessary.
