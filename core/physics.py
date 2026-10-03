"""Phase 1 physics boundary.

No physics step is implemented during Phase 0. Keeping the entrypoint explicit
prevents scaffold success from being confused with physical-simulation success.
"""


class PhysicsNotImplemented(RuntimeError):
    pass


def step(*_args, **_kwargs):
    raise PhysicsNotImplemented("Phase 1 minimal deterministic physics is not implemented")
