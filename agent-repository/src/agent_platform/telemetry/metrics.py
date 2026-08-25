"""In-process metrics registry and instrumentation surface (masterplan
section 16.4, plan milestone M8.1).

The six metric families from masterplan section 16.4 are defined in
``METRIC_FAMILIES`` as code (single source of truth) and consumed by the
dashboard/alert configuration in ``agent-repository/ops/``. The registry
is a small, dependency-free collector that renders both the Prometheus
text exposition format (for scraping) and a JSON snapshot (for tests and
the control plane).

This is deliberately *not* a hard dependency on the OpenTelemetry SDK:
per masterplan section 28.3, framework coupling is kept behind a thin
adapter. An OTel adapter can later push these metrics without changing
call sites.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock

DEFAULT_HISTOGRAM_BUCKETS = (0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0)


class MetricKind(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    help: str
    kind: MetricKind
    family: str
    safety_relevant: bool = False


@dataclass
class _Sample:
    labels: tuple[tuple[str, str], ...]
    value: float = 0.0
    count: int = 0
    sum: float = 0.0
    buckets: dict[float, int] = field(default_factory=dict)


@dataclass
class Metric:
    name: str
    help: str
    kind: MetricKind
    samples: list[_Sample] = field(default_factory=list)

    def sample_for(self, labels: tuple[tuple[str, str], ...]) -> _Sample:
        for sample in self.samples:
            if sample.labels == labels:
                return sample
        sample = _Sample(labels=labels)
        self.samples.append(sample)
        return sample


class MetricsRegistry:
    """Thread-safe in-process collector with Prometheus + JSON rendering."""

    def __init__(self, definitions: list[MetricDefinition] | None = None):
        self._lock = Lock()
        self._metrics: dict[tuple[str, str], Metric] = {}
        self._definitions: dict[tuple[str, str], MetricDefinition] = {}
        for definition in definitions or []:
            self.register(definition)

    def register(self, definition: MetricDefinition) -> None:
        with self._lock:
            key = (definition.name, definition.kind.value)
            self._definitions[key] = definition
            self._metrics[key] = Metric(name=definition.name, help=definition.help, kind=definition.kind)

    def _metric(self, name: str, kind: MetricKind, help_text: str) -> Metric:
        key = (name, kind.value)
        metric = self._metrics.get(key)
        if metric is None:
            metric = Metric(name=name, help=help_text, kind=kind)
            self._metrics[key] = metric
            self._definitions[key] = MetricDefinition(
                name=name, help=help_text, kind=kind, family="", safety_relevant=False
            )
        return metric

    @staticmethod
    def _normalize_labels(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted((str(k), str(v)) for k, v in labels.items()))

    def inc(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            sample = self._metric(name, MetricKind.COUNTER, "").sample_for(self._normalize_labels(labels))
            sample.value += value
            sample.count += 1

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            sample = self._metric(name, MetricKind.GAUGE, "").sample_for(self._normalize_labels(labels))
            sample.value = value
            sample.count = 1

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            sample = self._metric(name, MetricKind.HISTOGRAM, "").sample_for(self._normalize_labels(labels))
            sample.count += 1
            sample.sum += value
            for bucket in DEFAULT_HISTOGRAM_BUCKETS:
                if value <= bucket:
                    sample.buckets[bucket] = sample.buckets.get(bucket, 0) + 1

    def collect(self) -> list[Metric]:
        with self._lock:
            return list(self._metrics.values())

    def get(self, name: str, kind: MetricKind) -> Metric | None:
        with self._lock:
            return self._metrics.get((name, kind.value))

    # -- rendering -------------------------------------------------------

    def render_prometheus(self) -> str:
        lines: list[str] = []
        for metric in self.collect():
            lines.append(f"# HELP {metric.name} {metric.help}".rstrip())
            lines.append(f"# TYPE {metric.name} {metric.kind.value}")
            for sample in metric.samples:
                labels = _format_labels(sample.labels)
                if metric.kind is MetricKind.HISTOGRAM:
                    for bucket in DEFAULT_HISTOGRAM_BUCKETS:
                        lines.append(f"{metric.name}_bucket{labels}le=\"{bucket}\"}} {sample.buckets.get(bucket, 0)}")
                    lines.append(f"{metric.name}_bucket{labels}le=\"+Inf\"}} {sample.count}")
                    lines.append(f"{metric.name}_sum{labels} {sample.sum}")
                    lines.append(f"{metric.name}_count{labels} {sample.count}")
                else:
                    lines.append(f"{metric.name}{labels} {_format_value(sample.value)}")
        return "\n".join(lines) + ("\n" if lines else "")

    def render_json(self) -> str:
        payload = []
        for metric in self.collect():
            entry = {
                "name": metric.name,
                "help": metric.help,
                "kind": metric.kind.value,
                "samples": [
                    {
                        "labels": dict(sample.labels),
                        "value": sample.value,
                        "count": sample.count,
                        "sum": sample.sum,
                    }
                    for sample in metric.samples
                ],
            }
            payload.append(entry)
        return json.dumps(payload, sort_keys=True, indent=2)


def _format_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}"


def _format_value(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return repr(value)


# -- metric family catalog (masterplan section 16.4) --------------------------

METRIC_FAMILIES: dict[str, list[MetricDefinition]] = {
    "reliability": [
        MetricDefinition("run_completion_total", "Runs reaching a terminal status.", MetricKind.COUNTER, "reliability"),
        MetricDefinition("run_dead_letter_total", "Runs routed to dead letter.", MetricKind.COUNTER, "reliability", safety_relevant=True),
        MetricDefinition("tool_failure_total", "Tool executions that failed.", MetricKind.COUNTER, "reliability"),
    ],
    "quality": [
        MetricDefinition("acceptance_total", "Outputs accepted by the QA gate.", MetricKind.COUNTER, "quality"),
        MetricDefinition("defect_escape_total", "Defects escaping the QA gate.", MetricKind.COUNTER, "quality"),
        MetricDefinition("grounded_claim_total", "Status-report claims with a source.", MetricKind.COUNTER, "quality"),
    ],
    "operations": [
        MetricDefinition("run_duration_seconds", "End-to-end run duration.", MetricKind.HISTOGRAM, "operations"),
        MetricDefinition("queue_latency_seconds", "Queue wait time before a worker lease.", MetricKind.HISTOGRAM, "operations"),
        MetricDefinition("availability_total", "Control-plane availability probes.", MetricKind.COUNTER, "operations"),
    ],
    "economics": [
        MetricDefinition("cost_per_accepted_spoc_usd", "Cost per accepted SPOC.", MetricKind.GAUGE, "economics"),
        MetricDefinition("budget_exhausted_total", "Runs exceeding their budget.", MetricKind.COUNTER, "economics", safety_relevant=True),
        MetricDefinition("rework_cost_usd", "Cost attributable to rework.", MetricKind.GAUGE, "economics"),
    ],
    "governance": [
        MetricDefinition("approval_lead_time_seconds", "Time from approval request to decision.", MetricKind.HISTOGRAM, "governance"),
        MetricDefinition("policy_denial_total", "Policy decisions that denied an action.", MetricKind.COUNTER, "governance", safety_relevant=True),
        MetricDefinition("unowned_artifact_total", "Artifacts with no owner.", MetricKind.GAUGE, "governance"),
    ],
    "project_value": [
        MetricDefinition("milestone_predictability_ratio", "Milestones delivered on forecast.", MetricKind.GAUGE, "project_value"),
        MetricDefinition("blocked_work_age_seconds", "Age of blocked work.", MetricKind.GAUGE, "project_value"),
        MetricDefinition("risk_closure_total", "Risks closed.", MetricKind.COUNTER, "project_value"),
    ],
}


def standard_platform_metrics() -> MetricsRegistry:
    """A registry pre-populated with every masterplan section 16.4 metric."""
    registry = MetricsRegistry()
    for definitions in METRIC_FAMILIES.values():
        for definition in definitions:
            registry.register(definition)
    return registry


def safety_relevant_metric_names() -> set[str]:
    return {
        d.name
        for definitions in METRIC_FAMILIES.values()
        for d in definitions
        if d.safety_relevant
    }
