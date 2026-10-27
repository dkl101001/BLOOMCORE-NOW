"""Conservative source-independence accounting."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceAssertion:
    assertion_id: str
    relation_state: str
    parent_assertion_ids: list[str] = field(default_factory=list)


class LineageGraph:
    """Count evidence roots, never URLs.

    UNKNOWN and SUSPECTED_COMMON_ORIGIN add no confirmed corroboration. A
    derivative inherits its parents' roots, so five mirrors of one OSM object
    remain one lineage.
    """

    CONFIRMED = {"ORIGINAL", "INDEPENDENT_CONFIRMED"}
    DERIVATIVE = {"SAME_ARTIFACT", "CONFIRMED_DERIVATIVE"}
    ZERO_WEIGHT = {"UNKNOWN", "SUSPECTED_COMMON_ORIGIN"}

    def __init__(self) -> None:
        self.assertions: dict[str, SourceAssertion] = {}

    def add(self, assertion: SourceAssertion) -> None:
        allowed = self.CONFIRMED | self.DERIVATIVE | self.ZERO_WEIGHT
        if assertion.relation_state not in allowed:
            raise ValueError(f"unsupported relation state {assertion.relation_state}")
        if assertion.assertion_id in assertion.parent_assertion_ids:
            raise ValueError("self-derived assertion")
        self.assertions[assertion.assertion_id] = assertion

    def roots(self, assertion_id: str, trail: frozenset[str] = frozenset()) -> set[str]:
        if assertion_id in trail:
            raise ValueError("lineage cycle")
        assertion = self.assertions[assertion_id]
        if assertion.relation_state in self.ZERO_WEIGHT:
            return set()
        if assertion.relation_state in self.CONFIRMED:
            return {assertion_id}
        roots: set[str] = set()
        for parent in assertion.parent_assertion_ids:
            roots |= self.roots(parent, trail | {assertion_id})
        return roots

    def independence_bounds(self, assertion_ids: list[str]) -> tuple[int, int]:
        confirmed: set[str] = set()
        unresolved = 0
        for assertion_id in assertion_ids:
            assertion = self.assertions[assertion_id]
            confirmed |= self.roots(assertion_id)
            if assertion.relation_state in self.ZERO_WEIGHT:
                unresolved += 1
        return len(confirmed), len(confirmed) + unresolved

