from __future__ import annotations
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .models import *
from .adapters import SanctionsAdapter, RegistryAdapter, VesselAdapter
from .risk_engine import counterparty_risk, vessel_risk, payment_risk, route_risk, conclusion, clamp
from .reporting import build_pdf_report

settings=get_settings()
app=FastAPI(title="Aegis Comply API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sanctions=SanctionsAdapter()
registry=RegistryAdapter()
vessels=VesselAdapter()

@app.get('/api/health')
def health():
    return {"status":"ok","service":"aegis-comply","version":"1.0.0"}

@app.post('/api/counterparty/check', response_model=CounterpartyResponse)
async def check_counterparty(req: CounterpartyRequest):
    profile, evidence = await registry.lookup(req.inn_or_ogrn, req.name)
    hits = sanctions.screen_name(profile.get('name') or req.name)
    score, flags = counterparty_risk(profile, hits)
    for h in hits:
        evidence.append(Evidence(source=h.source, status="hit", detail=f"Potential match: {h.name} ({h.score}%), program: {h.program}"))
    return CounterpartyResponse(query=req, profile=profile, score=score, red_flags=flags, evidence=evidence, legal_conclusion=conclusion(score, flags, 'контрагента'))

@app.post('/api/registry/source', response_model=SourceCheckResponse)
def registry_source(req: SourceCheckRequest):
    return registry.source_detail(req.source, req.inn_or_ogrn, req.name)

@app.post('/api/vessel/check', response_model=VesselResponse)
def check_vessel(req: VesselRequest):
    signals=req.model_dump(include={'ais_gap','flag_changes','opaque_ownership','sts_operations','non_western_insurance'})
    score, flags = vessel_risk(req)
    route = vessels.build_route(req.flag, req.name_or_imo, signals)
    evidence=[Evidence(source="AIS provider", status="ready", detail="Подключаемый слой AIS/IMO: MarineTraffic, Spire, VesselFinder или корпоративный провайдер."), Evidence(source="IMO/FAL + OFAC/EU maritime guidance", status="applied", detail="Применены индикаторы теневого флота: AIS gaps, STS, flag hopping, ownership opacity, P&I insurance.")]
    return VesselResponse(vessel={"name_or_imo":req.name_or_imo,"flag":req.flag,"signals":signals}, score=score, route=route, red_flags=flags, evidence=evidence, legal_conclusion=conclusion(score, flags, 'морского судна'))

@app.post('/api/payment/check', response_model=GenericRiskResponse)
def check_payment(req: PaymentRequest):
    score, flags = payment_risk(req)
    evidence=[Evidence(source="Bank sanctions screening", status="applied", detail="Сопоставление банка-отправителя и банка-получателя с SDN/SSI/EU/UK списками."), Evidence(source="Currency control", status="applied", detail="Проверена логика 173-ФЗ: валютная операция, подтверждающие документы, банк валютного контроля.")]
    return GenericRiskResponse(score=score, red_flags=flags, evidence=evidence, legal_conclusion=conclusion(score, flags, 'платёжного коридора'), details=req.model_dump())

@app.post('/api/route/check', response_model=GenericRiskResponse)
def check_route(req: RouteRequest):
    score, flags = route_risk(req)
    evidence=[Evidence(source="Anti-circumvention engine", status="applied", detail="Проверены транзитные юрисдикции, категория товара, назначение и признаки реэкспорта.")]
    return GenericRiskResponse(score=score, red_flags=flags, evidence=evidence, legal_conclusion=conclusion(score, flags, 'маршрута поставки'), details=req.model_dump())

@app.post('/api/case/analyze', response_model=GenericRiskResponse)
async def analyze_case(req: CaseRequest):
    cp = await check_counterparty(req.counterparty)
    all_flags=list(cp.red_flags); all_evidence=list(cp.evidence); total=cp.score
    count=1
    if req.payment:
        p=check_payment(req.payment); all_flags+=p.red_flags; all_evidence+=p.evidence; total+=p.score; count+=1
    if req.route:
        r=check_route(req.route); all_flags+=r.red_flags; all_evidence+=r.evidence; total+=r.score; count+=1
    if req.vessel:
        v=check_vessel(req.vessel); all_flags+=v.red_flags; all_evidence+=v.evidence; total+=v.score; count+=1
    score=clamp(round(total/count))
    return GenericRiskResponse(score=score, red_flags=all_flags, evidence=all_evidence, legal_conclusion=conclusion(score, all_flags, 'сделки ВЭД'), details={"counterparty":cp.profile})

@app.post('/api/report/pdf')
async def report_pdf(payload: dict):
    pdf = build_pdf_report(payload)
    return Response(pdf, media_type='application/pdf', headers={'Content-Disposition':'attachment; filename=aegis_compliance_report.pdf'})
