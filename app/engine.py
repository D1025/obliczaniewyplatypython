"""
app/engine.py
-------------

Warstwa silnika: FastAPI → CLIPS → wynik.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from clips import Environment

from app.schemas import PayrollPayload, PayrollResult

# ────────────────────────────────────────────────────────────────────
#  Inicjalizacja CLIPS
# ────────────────────────────────────────────────────────────────────
_clips_env = Environment()
_clips_env.load("./app/rules/payroll.clp")

# ────────────────────────────────────────────────────────────────────
#  Pomocnicze
# ────────────────────────────────────────────────────────────────────
def _dec(value: Any) -> Decimal:
    """Decimal z dwoma miejscami po przecinku."""
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _push_facts(env: Environment, p: PayrollPayload) -> None:
    """Serializacja payloadu do faktów CLIPS."""
    env.assert_string(
        f'(employee (first-name "{p.employee.firstName}") '
        f'(last-name "{p.employee.lastName}") '
        f'(contract-type {p.employee.contractType.value}))'
    )
    env.assert_string(
        f'(position (base-rate {p.position.baseRate}) '
        f'(currency {p.position.currency.value}) '
        f'(fte {getattr(p.employee, "fte", 1)}))'
    )
    env.assert_string(
        f'(period (start "{p.period.payPeriodStart}") '
        f'(end "{p.period.payPeriodEnd}"))'
    )

    ot = p.overtime
    env.assert_string(
        f'(overtime (fifty {ot.overtime50h}) (hundred {ot.overtime100h}) '
        f'(night {ot.overtimeNightH}) '
        f'(mult50 {ot.overtime50Multiplier}) (mult100 {ot.overtime100Multiplier}))'
    )

    tr = p.travel
    env.assert_string(
        f'(travel (dom-days {tr.travelDaysDomestic}) '
        f'(abrd-days {tr.travelDaysAbroad}) '
        f'(dom-rate {tr.dietRateDomestic}) (abrd-rate {tr.dietRateAbroad}) '
        f'(accomodation {tr.accommodationCost}) '
        f'(lump-sum {tr.lumpSumTransport}) '
        f'(private-km {tr.privateCarKm}) '
        f'(km-rate {tr.privateCarRatePerKm}))'
    )

    al = p.allowances
    env.assert_string(
        f'(allowances (seniority-pct {al.seniorityBonusPct}) '
        f'(function-allow {al.functionAllowance}) '
        f'(perf-bonus {al.performanceBonus}) '
        f'(regulation-bonus {al.regulationBonus}) '
        f'(night-allow {al.nightWorkAllowance}) '
        f'(weekend-allow {al.weekendHolidayAllowance}) '
        f'(remote-allow {al.remoteWorkAllowance}) '
        f'(medical {al.medicalBenefitValue}) '
        f'(car {al.companyCarBenefitValue}))'
    )

    de = p.deductions
    env.assert_string(
        f'(deductions-pct (zus {de.employeeSocialInsurancePct}) '
        f'(health {de.healthInsurancePct}) (tax-adv {de.incomeTaxAdvancePct}) '
        f'(ppk {de.ppkEmployeePct}) (bail {de.bailDeduction}))'
    )

    ts = p.timesheet
    env.assert_string(
        f'(timesheet (hours-worked {ts.hoursWorked}) '
        f'(norm-hours {ts.publicHolidaysInPeriod or 160}))'
    )


def _template_slot_names(fact) -> list[str]:
    """Zwraca listę nazw slotów z facta (poprawka: .slots – BEZ nawiasów)."""
    return [slot.name for slot in fact.template.slots]


def _collect_results(env: Environment) -> Dict[str, Any]:
    """Przekształca fakty wynikowe w słowniki Pythona."""
    comp = ded = summ = None

    for fact in env.facts():
        name = fact.template.name
        slots = _template_slot_names(fact)

        if name == "components":
            comp = {slot: _dec(fact[slot]) for slot in slots}
        elif name == "deductions":
            ded = {slot: _dec(fact[slot]) for slot in slots}
        elif name == "summary":
            summ = {"net": _dec(fact["net"])}

    if comp is None or summ is None:
        raise RuntimeError("Brak faktów 'components' lub 'summary' po CLIPS.")

    return {"components": comp, "deductions": ded, "summary": summ}


# ────────────────────────────────────────────────────────────────────
#  API dla FastAPI
# ────────────────────────────────────────────────────────────────────
def run_payroll(payload: PayrollPayload) -> PayrollResult:
    env = _clips_env
    env.reset()

    _push_facts(env, payload)
    env.run()

    facts = _collect_results(env)
    comp = facts["components"]

    return PayrollResult(
        gross=comp["gross"],
        overtimePay=comp["overtime-pay"],
        bonuses=comp["allow-pay"],
        details={
            "baseSalary": comp["base-salary"],
            "travelPay": comp["travel-pay"],
            **(facts["deductions"] or {}),
            "net": facts["summary"]["net"],
        },
        calculatedAt=datetime.now(timezone.utc),
    )
