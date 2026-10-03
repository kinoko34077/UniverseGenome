# Observation and GUI Specification

The GUI is an observer/control surface and does not own the authoritative simulation clock.

# 34. GUI overview

Specified for Phase 3.

## SPEC-UI-001
**Status: accepted**

Layout:

- 16 columns × 8 rows
- 128 universe thumbnails
- four categories grouped as two rows/category
- a few pixels of visual gap between universes/categories

Per-universe thumbnail:

- 8×8 summary
- about 2 fps

Initial visual mapping:

- activity → brightness
- highest hierarchy → hue

Do not reuse hue for category labeling; use border/label/layout for category identity.

---

---

# 35. GUI detail

## SPEC-UI-010
**Status: accepted**

Selected universe:

- 32×32 detail map
- about 8 fps

Modes:

- HP
- hierarchy
- latent bit 0..15
- activity
- bond/contact

---

## SPEC-UI-011 — HP mode
**Status: accepted-default**

Hue:

- high HP → blue
- medium HP → green
- low HP → red

Brightness:

- bond/contact strength

A nonzero minimum brightness must distinguish active unbonded cells from empty space.

---

## SPEC-UI-012 — Hierarchy mode
**Status: accepted-default**

- hue → hierarchy level
- brightness → bond/contact strength

---

## SPEC-UI-013 — Automatic alternation
**Status: accepted**

At 8 fps, initial automatic HP/hierarchy mode switch:

- every 4 rendered frames

If visually distracting, allow every 8 frames.

Manual mode lock is required.

---

---

# 36. GUI controls

## SPEC-UI-020
**Status: accepted**

Required controls:

- Run
- Pause
- 1 Step
- Reset
- Select Universe
- Clone for Observation
- Rewind
- Save Snapshot
- Load Snapshot

---

## SPEC-UI-021 — Rewind capacity
**Status: accepted**

Selectable:

- 128
- 256
- 512 generations

Use bounded ring/history storage, not unbounded generation retention.

The population runtime stores each retained checkpoint as compact deterministic
JSON text rather than a live nested Python dictionary. Runtime summaries expose
the retained entry count, serialized object memory estimate, a 256 MiB bound,
and whether the current estimate is within that bound. The 128/256/512 policy
therefore has executable memory evidence while preserving exact rewind and
snapshot round-trips.

---

## SPEC-UI-022 — Parameter edits
**Status: accepted**

Manual parameter changes do not mutate the constants of an already-running authoritative experiment.

Apply on next reset/spawn/new universe unless a future explicit live-edit mode is specified.

---

# 37. Current Phase 3 implementation contract

The accepted observer surface is implemented through the server-owned runtime
payload:

- every overview summary contains a bounded 8×8 spatial projection with
  activity, highest hierarchy, and occupancy values;
- detail cells expose HP, hierarchy level, latent, activity, and bond/contact
  values;
- overview polling is 500 ms and detail polling is 125 ms;
- HP/hierarchy automatic alternation occurs every four detail frames and can
  be manually locked;
- clone observation is an explicit selected observation target and does not
  mutate or advance the authoritative slot;
- the server history policy is bounded to 128, 256, or 512 generations, with
  the default observer runtime configured for 512.

---
