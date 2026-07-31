"""Offline deterministic Controlled Revision quality evaluation."""

from .benchmark import RevisionBenchmarkRunner, build_synthetic_corpus
from .evaluation import evaluate_scenario
from .history import (
    BenchmarkHistory,
    BenchmarkHistoryEntry,
    BenchmarkHistoryError,
    append_benchmark_history,
    create_benchmark_history,
    load_benchmark_history,
)
from .metrics import aggregate_benchmark
from .pricing import BenchmarkPricingSpecification, load_benchmark_pricing
from .results import BenchmarkResult, ScenarioEvaluation
from .scenario import (
    BenchmarkAcceptanceSpecification,
    BenchmarkMode,
    CandidateRevision,
    FailureCategory,
    ScenarioCategory,
    SyntheticRevisionScenario,
)

__all__ = [
    "BenchmarkAcceptanceSpecification",
    "BenchmarkHistory",
    "BenchmarkHistoryEntry",
    "BenchmarkHistoryError",
    "BenchmarkMode",
    "BenchmarkPricingSpecification",
    "BenchmarkResult",
    "CandidateRevision",
    "FailureCategory",
    "RevisionBenchmarkRunner",
    "ScenarioCategory",
    "ScenarioEvaluation",
    "SyntheticRevisionScenario",
    "aggregate_benchmark",
    "append_benchmark_history",
    "build_synthetic_corpus",
    "create_benchmark_history",
    "evaluate_scenario",
    "load_benchmark_history",
    "load_benchmark_pricing",
]
