from fastapi import FastAPI, HTTPException
from datetime import datetime, timezone
from clips import Environment
from app.schemas import PayrollPayload, PayrollResult

app = FastAPI(title="Payroll-CLIPS PoC")

# 1️⃣  Tworzymy singleton środowiska CLIPS
clips_env = Environment()
clips_env.load("./app/rules/payroll.clp")

def run_engine(payload: PayrollPayload) -> PayrollResult:
    env = clips_env
    env.reset()

    # 2️⃣  Mapowanie JSON ⇒ Fakty
    emp = payload.employee
    pos = payload.position
    env.assert_string(f"""
        (employee (first-name "{emp.firstName}") (last-name "{emp.lastName}") (contract-type "{emp.contractType.value}") (base-rate {pos.baseRate}))
    """)

    ot = payload.overtime
    env.assert_string(f"""
        (overtime (fifty {ot.overtime50h}) (hundred {ot.overtime100h}))
    """)

    # 3️⃣  Odpalamy reguły
    env.run()

    # 4️⃣  Zbieramy fakty result
    gross = ot_pay = 0.0
    for fact in env.facts():
        if fact.template.name == "result":
            gross = float(fact["gross"])
            ot_pay = float(fact["overtime-pay"])
            break

    return PayrollResult(
        gross=gross,
        overtimePay=ot_pay,
        bonuses=payload.allowances.performanceBonus,
        details={"overtimePay": ot_pay},
        calculatedAt=datetime.now(timezone.utc)
    )

@app.post("/calculate", response_model=PayrollResult)
def calculate_payroll(req: PayrollPayload):
    try:
        return run_engine(req)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
