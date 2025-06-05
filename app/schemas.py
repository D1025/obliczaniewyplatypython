from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict

from pydantic import BaseModel, Field, condecimal, conint


# ------------------------------------------------------------------
#  ENUMS
# ------------------------------------------------------------------

class ContractType(str, Enum):
    EMPLOYMENT = "UMOWA_O_PRACE"
    B2B = "B2B"
    COMMISSION = "ZLECENIE"
    WORK = "DZIELO"


class SettlementFrequency(str, Enum):
    MONTHLY = "MIESIĘCZNA"
    WEEKLY = "TYGODNIOWA"
    BIWEEKLY = "DWUTYGODNIOWA"


class CurrencyCode(str, Enum):
    PLN = "PLN"
    EUR = "EUR"
    USD = "USD"


# ------------------------------------------------------------------
#  SECTION 1: EMPLOYEE
# ------------------------------------------------------------------

class Employee(BaseModel):
    firstName: str
    lastName: str
    contractType: ContractType


# ------------------------------------------------------------------
#  SECTION 2: POSITION / PAY BAND
# ------------------------------------------------------------------

class Position(BaseModel):
    positionId: str
    positionName: str
    grade: Optional[str] = None
    payBand: Optional[str] = None
    minRate: Optional[Decimal] = None
    maxRate: Optional[Decimal] = None
    currency: CurrencyCode = CurrencyCode.PLN
    baseRate: Decimal = Field(..., description="Kwota bazowa brutto (mies. lub godz.)")


# ------------------------------------------------------------------
#  SECTION 3: SETTLEMENT PERIOD
# ------------------------------------------------------------------

class Period(BaseModel):
    payPeriodStart: date
    payPeriodEnd: date
    settlementFrequency: SettlementFrequency = SettlementFrequency.MONTHLY
    workingDaysInPeriod: Optional[int] = None
    normHoursInPeriod: Optional[Decimal] = None


# ------------------------------------------------------------------
#  SECTION 4: OVERTIME
# ------------------------------------------------------------------

class Overtime(BaseModel):
    overtime50h: Decimal = 0
    overtime100h: Decimal = 0
    overtimeNightH: Decimal = 0
    overtime50Multiplier: condecimal(gt=1) = 1.5
    overtime100Multiplier: condecimal(gt=1) = 2.0
    overtimeLimitMonthly: Optional[Decimal] = None


# ------------------------------------------------------------------
#  SECTION 5: TRAVEL / DELEGATIONS
# ------------------------------------------------------------------

class Travel(BaseModel):
    travelDaysDomestic: Decimal = 0
    travelDaysAbroad: Decimal = 0
    dietRateDomestic: Decimal = 0
    dietRateAbroad: Decimal = 0
    accommodationCost: Decimal = 0
    lumpSumTransport: Decimal = 0
    privateCarKm: Decimal = 0
    privateCarRatePerKm: Decimal = 0


# ------------------------------------------------------------------
#  SECTION 6: ALLOWANCES & BONUSES
# ------------------------------------------------------------------

class Allowances(BaseModel):
    seniorityBonusPct: Decimal = 0
    functionAllowance: Decimal = 0
    performanceBonus: Decimal = 0
    regulationBonus: Decimal = 0
    nightWorkAllowance: Decimal = 0
    weekendHolidayAllowance: Decimal = 0
    remoteWorkAllowance: Decimal = 0
    medicalBenefitValue: Decimal = 0
    companyCarBenefitValue: Decimal = 0


# ------------------------------------------------------------------
#  SECTION 7: DEDUCTIONS & CONTRIBUTIONS
# ------------------------------------------------------------------

class OtherDeduction(BaseModel):
    code: str
    amount: Decimal


class Deductions(BaseModel):
    employeeSocialInsurancePct: condecimal(ge=0) = 0
    healthInsurancePct: condecimal(ge=0) = 0
    incomeTaxAdvancePct: condecimal(ge=0) = 0
    ppkEmployeePct: condecimal(ge=0) = 0
    otherDeductions: List[OtherDeduction] = Field(default_factory=list)
    bailDeduction: Decimal = 0


# ------------------------------------------------------------------
#  SECTION 8: TAX PARAMETERS
# ------------------------------------------------------------------

class TaxThreshold(BaseModel):
    threshold: Decimal = Field(..., description="Kwota progu")
    rate: condecimal(ge=0, le=1) = Field(..., description="Stawka w udziale 0-1")


class TaxParameters(BaseModel):
    taxYear: conint(ge=2000)  # do rozszerzenia według potrzeb
    taxFreeAllowanceMonthly: Decimal
    costsOfIncomeMonthly: Decimal
    taxThresholds: List[TaxThreshold]


# ------------------------------------------------------------------
#  SECTION 9: TIMESHEET / CALENDAR (AGGREGATES)
# ------------------------------------------------------------------

class Timesheet(BaseModel):
    hoursWorked: Decimal
    hoursAbsencePaid: Decimal = 0
    hoursAbsenceUnpaid: Decimal = 0
    hoursSickLeave: Decimal = 0
    publicHolidaysInPeriod: int = 0


# ------------------------------------------------------------------
#  SECTION 10: META
# ------------------------------------------------------------------

class Meta(BaseModel):
    calculationId: str
    createdAt: datetime
    createdBy: str
    sourceSystem: Optional[str] = "WEB_UI"
    schemaVersion: str = "2025-06-01"


# ------------------------------------------------------------------
#  ROOT MODEL – PAYLOAD
# ------------------------------------------------------------------

class PayrollPayload(BaseModel):
    employee: Employee
    position: Position
    period: Period
    overtime: Overtime = Field(default_factory=Overtime)
    travel: Travel = Field(default_factory=Travel)
    allowances: Allowances = Field(default_factory=Allowances)
    deductions: Deductions = Field(default_factory=Deductions)
    tax: TaxParameters
    timesheet: Timesheet
    meta: Meta

    class Config:
        """Pydantic ustawienia globalne."""
        orm_mode = True
        json_encoders = {Decimal: lambda v: str(v)}  # unikamy utraty precyzji


class PayrollResult(BaseModel):
    gross: Decimal
    overtimePay: Decimal
    bonuses: Decimal
    details: Dict[str, Decimal]
    calculatedAt: datetime