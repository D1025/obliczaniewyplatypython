from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from clips import Environment
from app.schemas import PayrollPayload, PayrollResult

_clips_env = Environment()
_clips_env.load("./app/rules/payroll.clp")

def _dec(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))

def _push_facts(env: Environment, p: PayrollPayload) -> None:
    env.assert_string(
        f'(employee (first-name "{p.employee.firstName}") '
        f'(last-name "{p.employee.lastName}") '
        f'(contract-type {p.employee.contractType.value}) '
        f'(is-student {"TRUE" if p.employee.isStudent else "FALSE"}))'
    )
    env.assert_string(
        f'(position (base-rate 6000) '
        f'(currency {p.position.currency.value}) '
        f'(fte 1))'
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
        f'(health {de.healthInsurancePct}) '
        f'(ppk {de.ppkEmployeePct}) '
        f'(bail {de.bailDeduction}))'
    )
    ts = p.timesheet
    env.assert_string(
        f'(timesheet (hours-worked {ts.hoursWorked}) '
        f'(norm-hours {ts.publicHolidaysInPeriod or 160}))'
    )

def _template_slot_names(fact) -> list[str]:
    return [slot.name for slot in fact.template.slots]

def _collect_results(env: Environment) -> Dict[str, Any]:
    comp = ded = summ = None
    for fact in env.facts():
        name = fact.template.name
        if name == "components":
            comp = {slot: _dec(fact[slot]) for slot in _template_slot_names(fact)}
        elif name == "deductions":
            ded = {slot: _dec(fact[slot]) for slot in _template_slot_names(fact)}
        elif name == "summary":
            summ = {"net": _dec(fact["net"])}
    return {"components": comp, "deductions": ded, "summary": summ}

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
