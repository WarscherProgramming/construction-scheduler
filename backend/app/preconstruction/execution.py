"""Bounded execution budgets, phase timing, and cost accounting primitives.

Pure helpers with no ORM, session, configuration import, network, or provider
access. Everything here is deterministic: the same inputs always produce the
same budget decision, the same controlled phase names, and the same cost
arithmetic.

Cost is accounted in integer micro-units from explicitly configured rates. When
no rate is configured the cost is reported as unconfigured rather than being
estimated, so an operator never sees a fabricated number.
"""

from dataclasses import dataclass, field
from time import perf_counter


EXECUTION_METRICS_VERSION = "preconstruction-execution-1"

# Controlled execution kinds. A metrics row always points at exactly one
# existing execution record; there is no free-form kind.
EXECUTION_KINDS = {
    "preparation_run": "Content preparation run",
    "analysis_attempt": "Provider analysis attempt",
    "scope_comparison": "Deterministic scope comparison",
    "evaluation_run": "Evaluation suite run",
}

# Controlled phase names. Timing is only ever recorded against these, so a
# metrics payload can never carry an arbitrary caller-supplied key.
EXECUTION_PHASES = (
    "resolve",
    "manifest",
    "match",
    "validate",
    "persist",
    "serialize",
    "provider",
    "total",
)

# Reasons an execution stopped early. Each is surfaced to the operator instead
# of silently truncating.
BUDGET_STOP_REASONS = {
    "pair_budget_exceeded": "Comparison pair budget exceeded",
    "assertion_budget_exceeded": "Assertion budget exceeded",
    "runtime_budget_exceeded": "Runtime budget exceeded",
    "candidate_limit_reached": "Candidate limit reached",
    "finding_limit_reached": "Finding limit reached",
}


@dataclass(frozen=True)
class PairBudget:
    """A deterministic decision about whether a comparison fits its budget.

    ``estimated_pairs`` is the exact number of requirement/coverage comparisons
    the deterministic engine would perform, so the decision is arithmetic
    rather than a heuristic.
    """

    left_count: int
    right_count: int
    estimated_pairs: int
    maximum_pairs: int
    within_budget: bool

    def payload(self) -> dict:
        return {
            "left_count": self.left_count,
            "right_count": self.right_count,
            "estimated_pairs": self.estimated_pairs,
            "maximum_pairs": self.maximum_pairs,
            "within_budget": self.within_budget,
        }


def estimate_pair_budget(
    left_count: int, right_count: int, maximum_pairs: int
) -> PairBudget:
    """Exact pair count for a coverage comparison, checked against the budget."""
    estimated = max(0, left_count) * max(0, right_count)
    return PairBudget(
        left_count=left_count,
        right_count=right_count,
        estimated_pairs=estimated,
        maximum_pairs=maximum_pairs,
        within_budget=estimated <= maximum_pairs,
    )


class PhaseTimer:
    """Accumulates monotonic per-phase durations in whole milliseconds.

    Only names in ``EXECUTION_PHASES`` are accepted. Durations use
    ``perf_counter`` so a system clock change cannot produce a negative value.
    """

    def __init__(self) -> None:
        self._durations: dict[str, float] = {}
        self._started = perf_counter()

    def record(self, phase: str, seconds: float) -> None:
        if phase not in EXECUTION_PHASES:
            raise ValueError(f"Unknown execution phase: {phase}")
        self._durations[phase] = self._durations.get(phase, 0.0) + max(0.0, seconds)

    def measure(self, phase: str) -> "_PhaseContext":
        return _PhaseContext(self, phase)

    def total_ms(self) -> int:
        return int(max(0.0, perf_counter() - self._started) * 1000)

    def payload(self) -> dict[str, int]:
        """Phase durations in milliseconds, ordered by the controlled tuple."""
        resolved = {
            phase: int(self._durations[phase] * 1000)
            for phase in EXECUTION_PHASES
            if phase in self._durations
        }
        resolved["total"] = self.total_ms()
        return resolved


class _PhaseContext:
    def __init__(self, timer: PhaseTimer, phase: str) -> None:
        if phase not in EXECUTION_PHASES:
            raise ValueError(f"Unknown execution phase: {phase}")
        self._timer = timer
        self._phase = phase
        self._start = 0.0

    def __enter__(self) -> "_PhaseContext":
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self._timer.record(self._phase, perf_counter() - self._start)
        return False


@dataclass
class ExecutionMetrics:
    """One execution's measured cost. Written once and never updated."""

    execution_kind: str
    execution_id: int
    phase_durations: dict[str, int] = field(default_factory=dict)
    duration_ms: int = 0
    query_count: int | None = None
    response_bytes: int | None = None
    input_units: int | None = None
    output_units: int | None = None
    estimated_cost_micros: int | None = None
    manifest_reused: bool = False
    budget_stop_reason: str | None = None

    def __post_init__(self) -> None:
        if self.execution_kind not in EXECUTION_KINDS:
            raise ValueError(f"Unknown execution kind: {self.execution_kind}")
        for phase in self.phase_durations:
            if phase not in EXECUTION_PHASES:
                raise ValueError(f"Unknown execution phase: {phase}")
        if (
            self.budget_stop_reason is not None
            and self.budget_stop_reason not in BUDGET_STOP_REASONS
        ):
            raise ValueError(f"Unknown budget stop reason: {self.budget_stop_reason}")


def estimate_cost_micros(
    input_units: int | None,
    output_units: int | None,
    input_micros_per_unit: int,
    output_micros_per_unit: int,
) -> int | None:
    """Integer micro-unit cost, or ``None`` when no rate is configured.

    Returning ``None`` rather than zero keeps "no rate configured" distinct
    from "this execution genuinely cost nothing", so an operator is never shown
    a fabricated figure.
    """
    if input_micros_per_unit <= 0 and output_micros_per_unit <= 0:
        return None
    return (
        max(0, input_units or 0) * max(0, input_micros_per_unit)
        + max(0, output_units or 0) * max(0, output_micros_per_unit)
    )


def format_cost_micros(value: int | None) -> str | None:
    """Safe display string for a micro-unit cost. No currency is implied."""
    if value is None:
        return None
    return f"{value / 1_000_000:.6f}"


# --- import-time validation -------------------------------------------------

if len(set(EXECUTION_PHASES)) != len(EXECUTION_PHASES):
    raise RuntimeError("Duplicate execution phase name")
if "total" not in EXECUTION_PHASES:
    raise RuntimeError("A total phase is required")
if not EXECUTION_KINDS:
    raise RuntimeError("At least one execution kind is required")
