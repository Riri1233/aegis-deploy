from __future__ import annotations
from .models import RedFlag, LegalConclusion

def clamp(n:int)->int: return max(0,min(100,n))

def conclusion(score:int, flags:list[RedFlag], context:str)->LegalConclusion:
    high = score >= 65 or any(f.level == "critical" for f in flags)
    decision = "Enhanced due diligence required" if high else ("Manual review" if score >= 35 else "Proceed with standard due diligence")
    return LegalConclusion(
        decision=decision,
        summary=(f"По результатам анализа {context} выявлен "
                 f"{'повышенный' if high else 'умеренный' if score>=35 else 'низкий'} уровень риска. "
                 "Система формирует документируемый evidence trail и перечень действий для юриста/комплаенс-офицера."),
        applicable_law=["173-ФЗ о валютном регулировании", "183-ФЗ об экспортном контроле", "115-ФЗ AML/KYC", "КоАП РФ", "УК РФ ст. 189", "OFAC 50 Percent Rule", "EU/UK sanctions regimes"],
        required_actions=sorted({d for f in flags for d in f.requested_documents}) or ["Сохранить evidence trail", "Провести стандартный KYC"],
        can_continue_without_edd=not high,
    )

def counterparty_risk(profile:dict, sanction_hits:list):
    score=10; flags=[]
    if sanction_hits:
        score += 70
        flags.append(RedFlag(level="critical", title="Совпадение с санкционным списком", description="Обнаружено сходство с записью в санкционной базе. Требуется ручная верификация и остановка операции до проверки.", legal_basis=["OFAC SDN", "EU Consolidated List", "UK OFSI"], requested_documents=["Юридическое заключение по санкционному статусу", "Документы о структуре владения"]))
    name=(profile.get('name') or '').upper()
    if any(x in name for x in ['BANK','БАНК','GAZPROMBANK','VTB','СБЕР']):
        score += 15
        flags.append(RedFlag(level="medium", title="Финансовая организация", description="Контрагент относится к финансовому сектору; требуется расширенная AML/KYC проверка и анализ санкционного профиля.", legal_basis=["115-ФЗ", "санкционные режимы OFAC/ЕС/UK"], requested_documents=["KYC анкета", "санкционная справка", "сведения о корреспондентских банках"]))
    if str(profile.get('status','')).lower() not in ['active','действующее','действующая']:
        score += 35
        flags.append(RedFlag(level="high", title="Неактивный или неопределённый статус", description="Статус юрлица требует проверки по ЕГРЮЛ/ЕГРИП.", legal_basis=["ГК РФ", "115-ФЗ"], requested_documents=["Свежая выписка ЕГРЮЛ/ЕГРИП"]))
    return clamp(score), flags

def vessel_risk(req):
    score=15; flags=[]
    flag_map={'pa':'Панама','lr':'Либерия','mn':'Монголия','ae':'ОАЭ','ru':'Россия','tr':'Турция','no':'Норвегия'}
    if req.flag in {'pa','lr','mn','ae'}:
        score+=15; flags.append(RedFlag(level="medium", title="Открытый/высокорисковый флаг", description=f"Флаг {flag_map.get(req.flag, req.flag)} требует проверки владельца, оператора и страховщика судна.", legal_basis=["IMO/FAL guidance", "OFAC maritime sanctions advisories"], requested_documents=["Certificate of Registry", "P&I insurance certificate", "DOC/SMC оператора"]))
    if req.ais_gap:
        score+=30; flags.append(RedFlag(level="high", title="AIS gap", description="Пропуски AIS могут указывать на попытку скрыть маршрут или STS-операции.", legal_basis=["IMO AIS guidance", "OFAC maritime advisories"], requested_documents=["AIS history", "портовые заходы", "коносаменты"]))
    if req.flag_changes:
        score+=18; flags.append(RedFlag(level="medium", title="Частая смена флага", description="Смена флага является типичным индикатором уклонения от мониторинга.", legal_basis=["EU Regulation 2023/2874", "OFAC maritime advisories"], requested_documents=["flag history", "previous vessel names"]))
    if req.opaque_ownership:
        score+=22; flags.append(RedFlag(level="high", title="Непрозрачная структура владения", description="Требуется идентифицировать registered owner, beneficial owner, manager и operator.", legal_basis=["KYC/UBO due diligence", "OFAC 50 Percent Rule"], requested_documents=["ownership chain", "manager/operator details", "beneficial owner declaration"]))
    if req.sts_operations:
        score+=20; flags.append(RedFlag(level="high", title="STS-операции", description="Перегрузка судно-судно требует проверки происхождения груза и соответствия price cap / санкционным ограничениям.", legal_basis=["OFAC oil price cap guidance", "EU sanctions regime"], requested_documents=["STS declaration", "cargo origin documents", "bills of lading"]))
    if req.non_western_insurance:
        score+=10; flags.append(RedFlag(level="medium", title="Страхование вне западного P&I рынка", description="Нужно проверить страховое покрытие, страховщика и применимость санкционных ограничений.", legal_basis=["IMO/FAL guidance", "OFAC maritime advisories"], requested_documents=["P&I certificate", "insurance policy", "insurer sanctions check"]))
    return clamp(score), flags

def payment_risk(req):
    score=10; flags=[]
    bank=(req.sender_bank+' '+req.receiver_bank).lower()
    if any(x in bank for x in ['gazprom', 'газпром', 'vtb', 'втб']):
        score+=45; flags.append(RedFlag(level="high", title="Подсанкционный/высокорисковый банк", description="Вероятен отказ корреспондентского банка или блокировка платежа.", legal_basis=["OFAC SDN/SSI", "EU/UK sanctions"], requested_documents=["маршрут платежа", "банк-корреспондент", "инвойс", "контракт"]))
    if req.currency.lower() in ['usd','eur']:
        score+=25; flags.append(RedFlag(level="medium", title="Западная валюта расчётов", description="USD/EUR повышают риск прохождения через корреспондентскую инфраструктуру США/ЕС.", legal_basis=["173-ФЗ", "OFAC/EU sanctions compliance"], requested_documents=["обоснование валюты", "correspondent bank details"]))
    return clamp(score), flags

def route_risk(req):
    score=10; flags=[]
    high_transit={'tr':'Турция','ae':'ОАЭ','am':'Армения','ge':'Грузия','kz':'Казахстан','hk':'Гонконг'}
    for t in [req.transit_1, req.transit_2]:
        if t and t!='none' and t in high_transit:
            score+=15; flags.append(RedFlag(level="medium", title=f"Транзит через {high_transit[t]}", description="Юрисдикция используется в схемах реэкспорта; требуется подтверждение конечного пользователя.", legal_basis=["anti-circumvention guidance OFAC/EU", "183-ФЗ"], requested_documents=["End-User Statement", "маршрутные документы", "no re-export clause"]))
    if req.goods_category in ['dual','aero']:
        score+=30; flags.append(RedFlag(level="high", title="Товар повышенного экспортного контроля", description="Категория товара требует идентификационной экспертизы и проверки лицензирования.", legal_basis=["183-ФЗ", "ПП РФ №312", "EU Dual-Use Regulation 2021/821", "BIS CHPI"], requested_documents=["идентификационное заключение", "EUC/EUS", "техническая спецификация"]))
    if req.destination in ['ir','by']:
        score+=35; flags.append(RedFlag(level="critical", title="Высокорисковая юрисдикция назначения", description="Необходима остановка операции до углубленного санкционного анализа.", legal_basis=["OFAC/EU/UK sanctions regimes"], requested_documents=["санкционное заключение", "legal memo"]))
    return clamp(score), flags
