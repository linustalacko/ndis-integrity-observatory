"""Pydantic case-file objects for the DA Assessment Copilot."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    claim: str
    source_type: str  # "arcgis" | "lep" | "dcp" | "submission" | "document"
    source_ref: str   # URL, clause id, or document + page
    quote: str | None = None


class PropertyContext(BaseModel):
    address: str
    lot_dp: str | None = None
    lots: list[str] = Field(default_factory=list)  # all lots for multi-lot sites
    lon: float
    lat: float
    lga: str | None = None
    lot_geometry: dict | None = None  # GeoJSON-ish esri geometry


class Control(BaseModel):
    name: str                 # "Height of Building"
    value: float | str | None
    unit: str | None = None   # "m", "m2", ":1"
    source_layer: str         # ArcGIS layer URL + id
    epi_name: str | None = None
    currency_date: str | None = None


class ControlsContext(BaseModel):
    zone_code: str | None = None
    zone_class: str | None = None
    permitted_uses: list[str] = Field(default_factory=list)
    prohibited_uses: list[str] = Field(default_factory=list)
    standards: list[Control] = Field(default_factory=list)
    heritage: list[dict] = Field(default_factory=list)
    applicable_sepps: list[str] = Field(default_factory=list)
    lep_name: str | None = None
    dcp_name: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class ProposalFacts(BaseModel):
    development_type: str | None = None
    storeys: int | None = None
    proposed_height_m: float | None = None
    gfa_m2: float | None = None
    fsr: float | None = None
    site_area_m2: float | None = None
    setbacks: dict = Field(default_factory=dict)
    dwelling_count: int | None = None
    extracted_from: list[str] = Field(default_factory=list)


class ComplianceFinding(BaseModel):
    control: str
    requirement: str
    proposed: str
    complies: bool | None = None  # None = needs human judgement
    breach_magnitude: str | None = None
    citation: Citation


class SubmissionIssue(BaseModel):
    theme: str
    count: int
    head_of_consideration: str
    draft_response: str
    citations: list[Citation] = Field(default_factory=list)


class CaseFile(BaseModel):
    property: PropertyContext
    controls: ControlsContext
    proposal: ProposalFacts | None = None
    compliance: list[ComplianceFinding] = Field(default_factory=list)
    submissions: list[SubmissionIssue] = Field(default_factory=list)
    draft_report_md: str | None = None
    audit_log: list[Citation] = Field(default_factory=list)
