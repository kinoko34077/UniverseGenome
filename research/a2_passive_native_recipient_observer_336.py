"""A2 E1a #336 — genuine passive native-selected-contact witness adapter.

Reuses the ALREADY ACCEPTED #317 ReadOnlyReaderProvenance observer.
Never creates a universe, calls a native step, changes source physics, or
constructs a mask. Caller alone may run a SYNTHETIC native step for tests.
A later original-seed alternate-physics study is separately HOLD-gated.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import patch

import core.physics as physics
from core.state import UniverseState
from research.a1_reader_provenance_317 import ReadOnlyReaderProvenance
from research.a2_matched_recipient_contract_336 import (
    _canonical_event, CONTACT_KEY, SCHEMA, MAX_NATIVE_EVENTS,
)


class PassiveNativeRecipientObserver:
    """Only observe actual native selected directed contacts for ONE state."""

    def __init__(self, state: UniverseState, *, event_limit: int = MAX_NATIVE_EVENTS):
        if state.config is None or state.config.latent_operator != "rotate_copy":
            raise ValueError("E1a fixture requires explicitly rotated RESEARCH state")
        if state.config.rotate_amount != 4:
            raise ValueError("E1a rotation must remain existing four-bit default")
        self.state = state
        self.prior = ReadOnlyReaderProvenance(state, event_limit=event_limit)
        self._observed_contexts: dict[tuple[int,...],dict[str,Any]] = {}
        self.events: list[dict[str,Any]] = []
        self._attached = False

    @contextmanager
    def attach(self) -> Iterator["PassiveNativeRecipientObserver"]:
        if self._attached or self.events or self._observed_contexts:
            raise ValueError("E1a observer is single-use for one physical continuation")
        # Save REAL native mask function BEFORE installing any wrapper.
        native_mask = physics.transmission_mask
        self._attached = True

        def read_only_mask(seed, generation, address, pair, bond_strength,
                           participant=None, *, source_trace=None):
            # Native source function is invoked exactly once, unchanged.
            mask = native_mask(
                seed, generation, address, pair, bond_strength,
                participant=participant, source_trace=source_trace,
            )
            if not self.prior._inside_transmit:
                return mask
            if participant is not self.state or source_trace is None:
                raise ValueError("E1a unexpected foreign/native mask context")
            source, recipient = map(int,pair)
            key = (
                int(generation), int(address), source, recipient,
                int(self.prior.epochs[source]), int(self.prior.epochs[recipient]),
            )
            if key in self._observed_contexts:
                raise ValueError("E1a duplicate authentic native contact key")
            state = participant
            self._observed_contexts[key] = {
                "native_generation":int(generation),
                "physical_address":int(address),
                "source_slot":source,
                "recipient_slot":recipient,
                "source_life_epoch":int(self.prior.epochs[source]),
                "recipient_life_epoch":int(self.prior.epochs[recipient]),
                "source_xy":[int(state.x[source]),int(state.y[source])],
                "recipient_xy":[int(state.x[recipient]),int(state.y[recipient])],
                "source_structure":int(state.structure[source]),
                "recipient_structure":int(state.structure[recipient]),
                "source_direction":int(state.direction[source]),
                "recipient_direction":int(state.direction[recipient]),
                "source_speed_code":int(state.speed_code[source]),
                "recipient_speed_code":int(state.speed_code[recipient]),
                "source_hp":int(state.hp[source]),
                "recipient_hp":int(state.hp[recipient]),
                "source_bond_strength":int(state.bond_strength[source]),
                "recipient_bond_strength":int(state.bond_strength[recipient]),
                "source_latent_before":int(state.latent[source]),
                "recipient_latent_before":int(state.latent[recipient]),
                "trace_bonus_shift":int(state.config.trace_bonus_shift),
                "source_trace_start":int(source_trace),
                "native_mask":int(mask),
                "native_operator":state.config.latent_operator,
                "rotate_amount":int(state.config.rotate_amount),
            }
            if int(bond_strength) != self._observed_contexts[key]["source_bond_strength"]:
                raise ValueError("E1a native bond provenance changed")
            return mask

        try:
            # Outer mask is a source-only logger. The inner original #317
            # observer itself calls the outer mask and checks source-native
            # selected directions and resulting cell array after transmit.
            with patch.object(physics,"transmission_mask",read_only_mask):
                with self.prior.attach():
                    yield self
            for old in self.prior.events:
                key = (
                    int(old["native_generation"]),int(old["address"]),
                    int(old["source_slot"]),int(old["recipient_slot"]),
                    int(old["source_epoch"]),int(old["recipient_epoch"]),
                )
                evidence=self._observed_contexts.pop(key,None)
                if evidence is None:
                    raise ValueError("E1a true native selected event lacked physical context")
                if (
                    old["source_trace_start"]!=evidence["source_trace_start"]
                    or old["native_mask"]!=evidence["native_mask"]
                    or old["source_latent_before"]!=evidence["source_latent_before"]
                    or old["recipient_latent_before"]!=evidence["recipient_latent_before"]
                ):
                    raise ValueError("E1a original A1 witness disagreed with native mask")
                evidence["recipient_latent_after"]=int(old["recipient_latent_after"])
                if tuple(evidence[f] for f in CONTACT_KEY)!=_canonical_event(evidence):
                    raise ValueError("E1a physical evidence validation failure")
                self.events.append(evidence)
            if self._observed_contexts:
                raise ValueError("E1a recorded foreign/non-selected contact")
        finally:
            self._attached = False

    @property
    def schema(self) -> str:
        return SCHEMA
