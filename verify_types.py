#!/usr/bin/env python3
"""Verify src/types/api.ts still matches the backend OpenAPI schema.

Run from the repository root with the backend's virtualenv active:

    python verify_types.py

Exits non-zero if any interface or enum has drifted, so it can gate CI.
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "backend"))

from app.main import app  # noqa: E402

TS_PATH = pathlib.Path(__file__).parent / "frontend" / "src" / "types" / "api.ts"

INTERFACES = [
    ("HealthResponse", "HealthResponse"),
    ("ProjectResponse", "Project"),
    ("DocumentResponse", "ProjectDocument"),
    ("AnalysisRunSummary", "AnalysisRunSummary"),
    ("AnalysisRunDetail", "AnalysisRunDetail"),
    ("AnalysisRunCreate", "AnalysisRunCreate"),
    ("CitationResponse", "Citation"),
    ("BusinessAnalysisResult", "BusinessAnalysisResult"),
    ("AnalysisFinding", "AnalysisFinding"),
    ("Assumption", "Assumption"),
    ("GovernanceReport", "GovernanceReport"),
    ("GovernanceEventResponse", "GovernanceEvent"),
    ("LedgerEntryResponse", "LedgerEntry"),
    ("LedgerAuditCheck", "LedgerAuditCheck"),
    ("GovernanceCatalogue", "GovernanceCatalogue"),
    ("GovernanceConstruct", "GovernanceConstruct"),
    ("DashboardSummary", "DashboardSummary"),
    ("RecentActivityItem", "RecentActivityItem"),
    ("SeverityBreakdown", "SeverityBreakdown"),
]

ENUMS = [
    ("WorkflowStatus", "WorkflowStatus"),
    ("WorkflowStage", "WorkflowStage"),
    ("FindingCategory", "FindingCategory"),
    ("FindingSeverity", "FindingSeverity"),
    ("DocumentIndexStatus", "DocumentIndexStatus"),
]


def ts_interface(source: str, name: str) -> tuple[set[str] | None, str | None]:
    match = re.search(
        r"export interface %s(?: extends (\w+))? \{(.*?)\n\}" % name, source, re.S
    )
    if not match:
        return None, None
    return set(re.findall(r"^\s{2}(\w+)[?]?:", match.group(2), re.M)), match.group(1)


def main() -> int:
    schemas = app.openapi()["components"]["schemas"]
    source = TS_PATH.read_text()
    problems: list[str] = []

    for api_name, ts_name in INTERFACES:
        expected = set(schemas[api_name].get("properties", {}))
        fields, base = ts_interface(source, ts_name)
        if fields is None:
            problems.append(f"{ts_name}: no such TypeScript interface")
            continue
        while base:
            inherited, base = ts_interface(source, base)
            fields |= inherited or set()
        if missing := expected - fields:
            problems.append(f"{ts_name}: missing {sorted(missing)}")
        if extra := fields - expected:
            problems.append(f"{ts_name}: not in the API {sorted(extra)}")

    for api_name, ts_name in ENUMS:
        expected = set(schemas[api_name]["enum"])
        match = re.search(r"export type %s =\s*(.*?)\n\n" % ts_name, source, re.S)
        actual = set(re.findall(r"'([^']+)'", match.group(1))) if match else set()
        if expected != actual:
            problems.append(f"{ts_name}: enum differs by {sorted(expected ^ actual)}")

    if problems:
        print("TypeScript types have drifted from the API:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(
        f"OK: {len(INTERFACES)} interfaces and {len(ENUMS)} enums match the API schema."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
