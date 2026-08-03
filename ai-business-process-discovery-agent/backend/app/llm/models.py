from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FindingCategory(str, Enum):
    PROCESS = "process"
    BOTTLENECK = "bottleneck"
    CONTROL = "control"
    RISK = "risk"
    DATA = "data"
    ROLE = "role"
    TECHNOLOGY = "technology"
    OPPORTUNITY = "opportunity"
    OTHER = "other"


class FindingSeverity(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(description="Source marker, for example Source 1")
    document_id: str | None = None
    chunk_id: str | None = None
    excerpt: str | None = None


class Assumption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class AnalysisFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: FindingCategory
    severity: FindingSeverity
    evidence_source_ids: list[str]
    recommendation: str = Field(min_length=1)


class BusinessAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    findings: list[AnalysisFinding]
    assumptions: list[Assumption]
    insufficient_evidence: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    provider_name: str | None = None
    model_name: str | None = None
