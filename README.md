# Information Compost

> A repository-first protocol for transforming traces of everyday action into structured receipts, reflections, and reusable meaning.

**Information Compost** is a small, forkable repository for preserving the traces of daily action without turning AI into a life designer.

The project starts from a simple premise:

> Human beings act first. Meaning often arrives later.

Instead of asking AI to decide the best life, the user records what actually happened. AI may then organize, normalize, and connect those traces. The resulting Receipt is not a verdict. It is a quiet mirror that helps a person notice repeated patterns, unfinished questions, and possible next experiments.

## Core cycle

```text
Action
  ↓
Trace
  ↓
Receipt
  ↓
Normalization
  ↓
Pause / Breathing
  ↓
Reflection
  ↓
New Question
  ↓
Action
```

The pause is part of the protocol. Information does not always need to become advice immediately. Some observations should be left to mature.

## Why “compost”?

Information is usually treated as something to store, search, or optimize. This project treats it as material that can be:

1. collected from ordinary life,
2. separated from premature interpretation,
3. mixed with context,
4. left unresolved when necessary,
5. transformed into reflection, narrative, or a reusable protocol.

The goal is not to accumulate more data. The goal is to create better soil for thought.

## AI’s role

AI is allowed to:

- organize facts and timestamps;
- normalize inconsistent notes;
- identify repeated actions or conditions;
- connect related Receipts;
- surface uncertainty and missing context;
- generate a reflection without prescribing a conclusion.

AI must not:

- decide the user’s life goals;
- define the user’s personality as a fixed type;
- present one “optimal” life path;
- convert every silence into an interpretation;
- hide uncertainty behind confident language;
- issue commands unless the user explicitly requests operational assistance.

## Repository-first

Information Compost does not require a hosted service.

A user can fork this repository, keep it private, write Receipts locally, and review them with any compatible AI. Git history can itself become a Receipt of how the protocol changed through practice.

A web UI, API, or Cloudflare Worker may be added later, but they are optional adapters rather than the project’s center.

```text
Repository
├─ Protocol
├─ Schema
├─ Receipts
├─ Reflections
└─ Revision history
```

## Minimal repository

```text
information-compost/
├─ README.md
├─ requirements.txt
├─ docs/
│  └─ philosophy.md
├─ protocols/
│  └─ compost_cycle.md
├─ prompts/
│  └─ quiet_mirror.md
├─ schemas/
│  └─ receipt.schema.yaml
├─ examples/
│  └─ daily_life/
│     └─ sample_receipt.yaml
└─ tools/
   └─ normalize_receipt.py
```

## Minimal Receipt

A Receipt separates observed facts from interpretation.

```yaml
receipt:
  id: receipt-2026-07-29-001
  occurred_at: 2026-07-29T18:30:00+09:00
  action:
    summary: Walked to the supermarket after work.
  traces:
    - type: note
      value: Chose vegetables and tofu instead of prepared food.
  context:
    energy: low
    weather: hot
  reflection:
    status: pending
```

See [`schemas/receipt.schema.yaml`](schemas/receipt.schema.yaml) for the minimal machine-readable format and [`examples/daily_life/sample_receipt.yaml`](examples/daily_life/sample_receipt.yaml) for a complete example.

## Executable normalizer

[`tools/normalize_receipt.py`](tools/normalize_receipt.py) turns a small handwritten YAML note into the canonical Receipt structure and validates the result against the repository schema.

It is deliberately deterministic. It may normalize field shapes, timestamps, IDs, and defaults, but it does not invent facts, infer personality, or generate advice.

Install the two lightweight dependencies:

```bash
python -m pip install -r requirements.txt
```

Normalize a raw note:

```bash
python tools/normalize_receipt.py raw.yaml \
  --default-offset +09:00 \
  --output receipt.yaml
```

Normalize and validate an existing Receipt without writing a new file:

```bash
python tools/normalize_receipt.py \
  examples/daily_life/sample_receipt.yaml \
  --check
```

The raw input can use the full Receipt structure or this smaller form:

```yaml
occurred_at: 2026-07-29T18:30:00+09:00
summary: Walked to the supermarket after work.
notes:
  - Chose ingredients instead of prepared food.
context:
  energy: low
  weather: hot
```

Unknown fields are rejected rather than silently discarded. Raw evidence belongs in `traces`; situational information belongs in `context`.

## Operating protocol and AI mirror

[`protocols/compost_cycle.md`](protocols/compost_cycle.md) defines the minimal use sequence:

```text
Act → Capture → Normalize → Pause → Review → Return
```

The protocol separates immediate capture from later interpretation and treats leaving a Receipt open as a valid outcome.

[`prompts/quiet_mirror.md`](prompts/quiet_mirror.md) provides a reusable review prompt for one or more normalized Receipts. It requires evidence citations by Receipt ID, separates facts from inference, looks for counterevidence, and prevents embedded Receipt text from acting as instructions.

The Quiet Mirror produces a draft for human review. It does not mutate source Receipts, diagnose the user, or choose a required next action.

## Design principles

### 1. Observation before interpretation

Record what happened before explaining why it happened.

### 2. Uncertainty is valid output

`unknown`, `pending`, and `insufficient_context` are legitimate states.

### 3. Reflection is not diagnosis

Patterns may be surfaced, but identity should not be fixed from a small number of traces.

### 4. The user owns the archive

Receipts should remain portable, readable, and usable without a specific vendor.

### 5. Outputs should return to life

A compost cycle is incomplete if it produces only analysis. A Receipt may eventually become a question, a story, a practical protocol, or a small change in action.

## Possible outputs

Information Compost can produce several kinds of artifacts from the same Receipt archive:

- personal reflection;
- daily or weekly journal;
- Receipt Story;
- historical or social context note;
- reusable work protocol;
- unresolved-question list;
- evidence pack for a later decision.

These are outputs of the composting process, not mandatory conclusions.

## Current status

This repository begins with seven foundations:

- a README that defines the project boundary;
- a philosophy document;
- a minimal Receipt schema;
- one example Receipt;
- a deterministic Python normalizer with schema validation;
- an operating protocol for the full compost cycle;
- a constrained Quiet Mirror prompt for evidence-based review.

The next useful additions are automated tests and a compost-batch schema for storing multi-Receipt reviews without collapsing them into a personality diagnosis.

## License

Copyright 2026 hanabokur0.

This repository, including its code, schemas, prompts, protocols, documentation, and examples, is licensed under the [Apache License 2.0](LICENSE).

You may use, modify, and distribute the materials, including for commercial purposes, subject to the license terms. Preserve the license and applicable notices when redistributing modified or unmodified copies.

The license applies to the materials in this repository. It does not grant exclusive rights to general ideas, methods, project names, or third-party material that may be referenced in future Receipts.

