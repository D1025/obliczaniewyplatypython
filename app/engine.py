from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from clips import Environment
from app.schemas import PayrollPayload, PayrollResult

_clips_env = Environment()
_clips_env.load("./app/rules/payroll.clp")

# ───────────────────────────────────────────────────────────
#  POMOCNICZE FUNKCJE
# ───────────────────────────────────────────────────────────

def _dec(val) -> Decimal:
    """Konwertuje wartości CLIPS-owe na Decimal (2 miejsca)."""
    return Decimal(str(val)).quantize(Decimal("0.01"))


def _slot_names(fact) -> list[str]:
    """Lista slotów danego facta."""
    return [s.name for s in fact.template.slots]


# ───────────────────────────────────────────────────────────
#  WPROWADZANIE FAKTÓW DO CLIPS
# ───────────────────────────────────────────────────────────

def _push_facts(env: Environment, p: PayrollPayload) -> None:
    env.assert_string(
        f'(employee (first-name "{p.employee.firstName}") '
        f'(last-name "{p.employee.lastName}") '
        f'(contract-type {p.employee.contractType.value}) '
        f'(is-student {"TRUE" if p.employee.isStudent else "FALSE"}))'
    )

    env.assert_string(
        f'(position (base-rate 6000) (currency {p.position.currency.value}) (fte 1))'
    )

    env.assert_string(
        f'(period (start "{p.period.payPeriodStart}") (end "{p.period.payPeriodEnd}"))'
    )

    ot = p.overtime
    env.assert_string(
        f'(overtime (fifty {ot.overtime50h}) (hundred {ot.overtime100h}) '
        f'(night {ot.overtimeNightH}) (mult50 {ot.overtime50Multiplier}) '
        f'(mult100 {ot.overtime100Multiplier}))'
    )

    tr = p.travel
    env.assert_string(
        f'(travel (dom-days {tr.travelDaysDomestic}) (abrd-days {tr.travelDaysAbroad}) '
        f'(dom-rate {tr.dietRateDomestic}) (abrd-rate {tr.dietRateAbroad}) '
        f'(accomodation {tr.accommodationCost}) (lump-sum {tr.lumpSumTransport}) '
        f'(private-km {tr.privateCarKm}) (km-rate {tr.privateCarRatePerKm}))'
    )

    al = p.allowances
    env.assert_string(
        f'(allowances (seniority-pct {al.seniorityBonusPct}) '
        f'(function-allow {al.functionAllowance}) (perf-bonus {al.performanceBonus}) '
        f'(regulation-bonus {al.regulationBonus}) (night-allow {al.nightWorkAllowance}) '
        f'(weekend-allow {al.weekendHolidayAllowance}) (remote-allow {al.remoteWorkAllowance}) '
        f'(medical {al.medicalBenefitValue}) (car {al.companyCarBenefitValue}))'
    )

    de = p.deductions
    env.assert_string(
        f'(deductions-pct (zus {de.employeeSocialInsurancePct}) '
        f'(health {de.healthInsurancePct}) (ppk {de.ppkEmployeePct}) '
        f'(bail {de.bailDeduction}))'
    )

    ts = p.timesheet
    env.assert_string(
        f'(timesheet (hours-worked {ts.hoursWorked}) '
        f'(norm-hours {ts.publicHolidaysInPeriod or 160}))'
    )


# ───────────────────────────────────────────────────────────
#  ZBIERANIE WYNIKÓW Z CLIPS
# ───────────────────────────────────────────────────────────

def _collect_results(env: Environment) -> Dict[str, Dict[str, Decimal]]:
    comp = ded = summ = contrib = None
    for fact in env.facts():
        name = fact.template.name
        if name == "components":
            comp = {s: _dec(fact[s]) for s in _slot_names(fact)}
        elif name == "deductions":
            ded = {s: _dec(fact[s]) for s in _slot_names(fact)}
        elif name == "contributions":
            contrib = {s: _dec(fact[s]) for s in _slot_names(fact)}
        elif name == "summary":
            summ = {"net": _dec(fact["net"])}
    return {"components": comp, "deductions": ded,
            "contributions": contrib, "summary": summ}


# ───────────────────────────────────────────────────────────
#  GŁÓWNA FUNKCJA
# ───────────────────────────────────────────────────────────

def run_payroll(payload: PayrollPayload) -> PayrollResult:
    env = _clips_env
    env.reset()
    _push_facts(env, payload)
    env.run()

    facts = _collect_results(env)

    comp = facts["components"]
    contrib = facts["contributions"] or {"social": Decimal(0),
                                         "health": Decimal(0),
                                         "ppk": Decimal(0)}

    details: Dict[str, Decimal] = {
        "baseSalary": comp["base-salary"],
        "travelPay": comp["travel-pay"],

        # nowo dodane składki
        "socialInsurance": contrib["social"],
        "healthInsurance": contrib["health"],
        "ppkContribution": contrib["ppk"],

        # pozostałe potrącenia
        **(facts["deductions"] or {}),
        "net": facts["summary"]["net"],
    }

    return PayrollResult(
        gross=comp["gross"],
        overtimePay=comp["overtime-pay"],
        bonuses=comp["allow-pay"],
        details=details,
        calculatedAt=datetime.now(timezone.utc),
    )