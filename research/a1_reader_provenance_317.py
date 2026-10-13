"""A1 #317: read-only provenance of ACTUAL source-selected latent transmission.

No physics, source RNG, selection, D1 default, seed, or result is modified.
An event is an observed SOURCE mask updating the OPPOSITE destination slot.
Trace is the value at the START of the native physical step (pre-write).
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import core.physics as physics
from core.state import Lifecycle, UniverseState

SCHEMA = "UG_A1_NATIVE_SELECTED_READER_PROVENANCE_V1"
EVENT_LIMIT = 200000
PAIR_FIELDS = ("native_generation", "address", "source_slot", "recipient_slot",
               "source_epoch", "recipient_epoch")
NONTRACE_FIELDS = ("source_xy", "bond_strength", "shift",
                   "source_latent_before", "recipient_latent_before")


class ReadOnlyReaderProvenance:
    """Scope instrumented execution to ONE cloned physical state.

    Caller must independently compare authoritative snapshots against
    uninstrumented source-native continuation. Historical data remain untouched.
    """

    def __init__(self, state: UniverseState, *, event_limit: int = EVENT_LIMIT):
        if event_limit <= 0:
            raise ValueError("event_limit must be positive")
        self.state = state
        self.event_limit = event_limit
        self.epochs = [0 if life != Lifecycle.FREE else -1 for life in state.lifecycle]
        self.events: list[dict[str, Any]] = []
        self.free_events: list[dict[str, int]] = []
        self._inside_transmit = False

    @contextmanager
    def attach(self):
        native_mask = physics.transmission_mask
        native_transmit = physics._transmit_latent
        native_free = UniverseState.free
        native_spawn = UniverseState.spawn

        def observed_mask(seed, generation, address, pair, bond_strength,
                          participant=None, *, source_trace=None):
            # Always call the original function with identical arguments ONCE.
            mask = native_mask(
                seed, generation, address, pair, bond_strength,
                participant=participant, source_trace=source_trace,
            )
            if not self._inside_transmit:
                return mask
            if participant is not self.state or source_trace is None:
                raise ValueError("A1 requires native step trace_start and state")
            source, recipient = map(int, pair)
            trace = int(source_trace)
            shift = int(participant.config.trace_bonus_shift) if participant.config else 8
            base = 1 + (int(bond_strength) >> 4)
            width = min(16, base + (trace >> shift))
            if mask.bit_count() != width:
                raise ValueError("native mask bit-count / width mismatch")
            if len(self.events) >= self.event_limit:
                raise ValueError("A1 source event bound exceeded")
            self.events.append({
                "native_generation": int(generation),
                "address": int(address),
                "source_slot": source,
                "recipient_slot": recipient,
                "source_epoch": self.epochs[source],
                "recipient_epoch": self.epochs[recipient],
                "source_xy": [int(participant.x[source]), int(participant.y[source])],
                "source_trace_start": trace,
                "bond_strength": int(bond_strength),
                "shift": shift,
                "base_width": base,
                "effective_width": width,
                "native_mask": int(mask),
                "source_latent_before": int(participant.latent[source]),
                "recipient_latent_before": int(participant.latent[recipient]),
                # Filled only after native _transmit_latent has applied updates.
                "recipient_latent_after": None,
            })
            return mask

        def observed_transmit(state, config, pairs, pair_addresses, generation, trace_start):
            if state is not self.state or self._inside_transmit:
                raise ValueError("A1 unexpected nested or foreign transmission")
            start = len(self.events)
            before = tuple(state.latent)
            self._inside_transmit = True
            try:
                result = native_transmit(
                    state, config, pairs, pair_addresses, generation, trace_start,
                )
            finally:
                self._inside_transmit = False
            new_events = self.events[start:]
            if len(new_events) != 2 * result[0]:
                raise ValueError("A1 must observe both directed native masks per selected pair")
            if any(event["recipient_latent_before"] != before[event["recipient_slot"]]
                   for event in new_events):
                raise ValueError("A1 pre-latent capture drift")
            for event in new_events:
                event["recipient_latent_after"] = int(state.latent[event["recipient_slot"]])
            return result

        def observed_free(state, slot):
            if state is self.state:
                self.free_events.append({
                    "native_generation": int(state.generation),
                    "slot": int(slot),
                    "life_epoch": int(self.epochs[slot]),
                })
            return native_free(state, slot)

        def observed_spawn(state, *args, **kwargs):
            slot = native_spawn(state, *args, **kwargs)
            if state is self.state:
                self.epochs[slot] += 1
            return slot

        with patch.object(physics, "transmission_mask", observed_mask), \
             patch.object(physics, "_transmit_latent", observed_transmit), \
             patch.object(UniverseState, "free", observed_free), \
             patch.object(UniverseState, "spawn", observed_spawn):
            yield self


def compare_branches(b_events: list[dict], h_events: list[dict],
                     *, example_limit: int = 12) -> dict[str, Any]:
    """Classify *observed* contacts; do not infer causal memory/learning."""
    if example_limit < 0:
        raise ValueError("example_limit must be nonnegative")

    def keyed(events):
        result = {}
        for event in events:
            if any(field not in event for field in PAIR_FIELDS + NONTRACE_FIELDS):
                raise ValueError("A1 incomplete event schema")
            if event.get("recipient_latent_after") is None:
                raise ValueError("A1 missing native recipient post-latent")
            key = tuple(event[field] for field in PAIR_FIELDS)
            if key in result:
                raise ValueError("A1 duplicate physical-life-epoch event key")
            result[key] = event
        return result

    b_map, h_map = keyed(b_events), keyed(h_events)
    counts: Counter[str] = Counter()
    examples = []
    for key in sorted(set(b_map) | set(h_map)):
        b, h = b_map.get(key), h_map.get(key)
        if b is None or h is None:
            counts["unmatched_topology"] += 1
            continue
        counts["matched_selected_read_events"] += 1
        same_nontrace = all(b[field] == h[field] for field in NONTRACE_FIELDS)
        trace_diff = b["source_trace_start"] != h["source_trace_start"]
        width_diff = b["effective_width"] != h["effective_width"]
        mask_diff = b["native_mask"] != h["native_mask"]
        after_diff = b["recipient_latent_after"] != h["recipient_latent_after"]
        if not same_nontrace:
            counts["confounded_nontrace_state"] += 1
        if trace_diff:
            counts["matched_trace_different"] += 1
        if trace_diff and not width_diff and same_nontrace:
            counts["trace_different_quantized_same_width"] += 1
        if width_diff and same_nontrace:
            counts["unconfounded_width_opportunity"] += 1
        if mask_diff and same_nontrace:
            counts["unconfounded_mask_opportunity"] += 1
        if after_diff:
            counts["paired_recipient_latent_different"] += 1
        if trace_diff and same_nontrace and after_diff:
            counts["coincident_trace_latent_difference_not_causal"] += 1
        if (trace_diff or width_diff or after_diff) and len(examples) < example_limit:
            examples.append({
                "key": list(key), "same_nontrace": same_nontrace,
                "trace": [b["source_trace_start"], h["source_trace_start"]],
                "width": [b["effective_width"], h["effective_width"]],
                "mask": [b["native_mask"], h["native_mask"]],
                "recipient_latent_after": [
                    b["recipient_latent_after"], h["recipient_latent_after"]
                ],
            })
    return {
        "schema": SCHEMA,
        "b_events": len(b_events), "h_events": len(h_events),
        "counts": dict(sorted(counts.items())),
        "examples": examples,
        "interpretation": (
            "Observed source-native read opportunity only. Different branch "
            "state or latent output cannot establish trace-specific causal "
            "readout without a separately controlled physical intervention."
        ),
        "independent_confirmation": False,
        "learning_claim": False,
    }
