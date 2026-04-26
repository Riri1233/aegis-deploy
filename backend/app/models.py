from pydantic import BaseModel, Field
from typing import Any, Literal

class Evidence(BaseModel):
    source: str
    status: str
    detail: str
    url: str | None = None

class RedFlag(BaseModel):
    level: Literal["low", "medium", "high", "critical"]
    title: str
    description: str
    legal_basis: list[str] = []
    requested_documents: list[str] = []

class LegalConclusion(BaseModel):
    decision: str
    summary: str
    applicable_law: list[str]
    required_actions: list[str]
    can_continue_without_edd: bool

class CounterpartyRequest(BaseModel):
    inn_or_ogrn: str = Field(default="", description="ИНН или ОГРН")
    name: str = ""
    purpose: str = "Первичный legal due diligence"

class CounterpartyResponse(BaseModel):
    query: CounterpartyRequest
    profile: dict[str, Any]
    score: int
    red_flags: list[RedFlag]
    evidence: list[Evidence]
    legal_conclusion: LegalConclusion

class VesselRequest(BaseModel):
    name_or_imo: str
    flag: str = "pa"
    ais_gap: bool = False
    flag_changes: bool = True
    opaque_ownership: bool = True
    sts_operations: bool = False
    non_western_insurance: bool = True

class VesselResponse(BaseModel):
    vessel: dict[str, Any]
    score: int
    route: list[dict[str, Any]]
    red_flags: list[RedFlag]
    evidence: list[Evidence]
    legal_conclusion: LegalConclusion

class PaymentRequest(BaseModel):
    sender_bank: str
    receiver_bank: str
    currency: str
    operation_type: str = "trade"
    amount: float = 0
    goods: str = ""

class RouteRequest(BaseModel):
    origin: str
    transit_1: str | None = None
    transit_2: str | None = None
    destination: str
    goods_category: str = "general"

class CaseRequest(BaseModel):
    counterparty: CounterpartyRequest
    vessel: VesselRequest | None = None
    payment: PaymentRequest | None = None
    route: RouteRequest | None = None
    extra: dict[str, Any] = {}

class GenericRiskResponse(BaseModel):
    score: int
    red_flags: list[RedFlag]
    evidence: list[Evidence]
    legal_conclusion: LegalConclusion
    details: dict[str, Any] = {}

class SourceCheckRequest(BaseModel):
    source: str
    inn_or_ogrn: str = ""
    name: str = ""

class SourceCheckResponse(BaseModel):
    source: str
    title: str
    status: str
    risk: int
    summary: str
    findings: list[dict[str, Any]]
    documents: list[str]
    official_url: str | None = None
    checked_at: str | None = None
