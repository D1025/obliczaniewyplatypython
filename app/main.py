from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import PayrollPayload, PayrollResult
from app.engine import run_payroll

# ──────────────────────────────────────────────────────────────────
#  Inicjalizacja FastAPI
# ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Payroll-CLIPS PoC",
    version="0.1.0",
    description="Prosty serwer HTTP demonstrujący kalkulator "
                "wynagrodzeń z użyciem silnika reguł CLIPS."
)

# ──────────────────────────────────────────────────────────────────
#  Konfiguracja CORS
# ──────────────────────────────────────────────────────────────────
origins = ["*"]  # TODO: ogranicz w produkcji

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────
#  Endpoint HTTP
# ──────────────────────────────────────────────────────────────────
@app.post("/calculate", response_model=PayrollResult, tags=["Payroll"])
def calculate(req: PayrollPayload):
    """
    Przyjmuje payload z danymi płacowymi i zwraca wynik obliczeń
    (brutto, dodatki, potrącenia, netto).
    """
    try:
        return run_payroll(req)
    except Exception as ex:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(ex)) from ex


# ──────────────────────────────────────────────────────────────────
#  Ułatwienie do lokalnego uruchamiania `python -m app.main`
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
