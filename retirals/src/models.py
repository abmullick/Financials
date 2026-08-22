from pydantic import BaseModel, model_validator, Field
from enum import Enum
from typing import Optional, Literal

class AdHocExpense(BaseModel):
    age: int = Field(..., gt=0, le=120, description="Age for the ad-hoc expense")
    amount: float = Field(..., ge=0, description="Amount of the ad-hoc expense")
    inflation_rate: Optional[float] = Field(None, ge=0, le=0.5, description="Specific inflation rate for this expense, if different from the general rate.")

class StressScenario(str, Enum):
    NORMAL = "Normal"
    MILD_CRASH = "Mild Crash (-10% for 2 yrs)"
    SEVERE_CRASH = "Severe Crash (-20% for 2 yrs)"

class ReturnDistribution(str, Enum):
    NORMAL = "normal"
    LOGNORMAL = "lognormal"

class PlannerInputs(BaseModel):
    current_age: int = Field(43, gt=0, le=120)
    retirement_age: int = Field(54, gt=0, le=120)
    life_expectancy: int = Field(90, gt=0, le=120)
    current_annual_expenses: float = Field(1200000.00, gt=0, le=1e9)
    avg_inflation_rate: float = Field(0.06, ge=0, le=0.5)
    current_corpus: float = Field(4000000.00, ge=0, le=1e12)
    annual_contribution: float = Field(700000.00, ge=0, le=1e9)
    pre_retirement_return: float = Field(0.09, ge=-0.5, le=0.5)
    post_retirement_return: float = Field(0.08, ge=-0.5, le=0.5)
    contribution_increase: float = Field(0.01, ge=0, le=0.5)
    ltcg_exemption: float = Field(125000.00, ge=0, le=1e7)
    one_time_lumpsum: float = Field(0.0, ge=0, description="One-time lumpsum added at retirement (e.g., gratuity).")
    stress_scenario: StressScenario = StressScenario.NORMAL
    adhoc_expenses: list[AdHocExpense] = Field(default_factory=lambda: [
        AdHocExpense(age=58, amount=2500000.00),
        AdHocExpense(age=75, amount=1000000.00)
    ], max_items=50)
    # Portfolio Allocation
    allocation_equity: float = Field(0.60, ge=0, le=1.0)
    allocation_debt: float = Field(0.30, ge=0, le=1.0)
    allocation_arbitrage: float = Field(0.10, ge=0, le=1.0)
    # Equity sub-allocation (LTCG/STCG split)
    equity_ltcg_split: float = Field(0.70, ge=0, le=1.0)
    equity_stcg_split: float = Field(0.30, ge=0, le=1.0)
    # Tax rates by asset class
    tax_ltcg: float = Field(0.125, ge=0, le=1.0)
    tax_stcg: float = Field(0.20, ge=0, le=1.0)
    tax_debt: float = Field(0.20, ge=0, le=1.0)
    tax_arbitrage: float = Field(0.20, ge=0, le=1.0)
    # Pension Inputs
    include_pension: bool = Field(False)
    pension_start_age: int | None = Field(60, gt=0, le=120)
    annual_pension: float = Field(600000.0, ge=0)
    pension_increase: float = Field(0.05, ge=0, le=0.5)
    pension_tax_rate: float = Field(0.20, ge=0, le=1.0)
    reinvest_pension_surplus: bool = Field(True)
    # Monte Carlo Parameters
    num_simulations: int = Field(1000, ge=100, le=50000, description="Number of Monte Carlo simulation paths.")
    volatility_equity: float = Field(0.18, ge=0, le=1.0, description="Annual volatility for equity allocation.")
    volatility_debt: float = Field(0.06, ge=0, le=1.0, description="Annual volatility for debt allocation.")
    volatility_arbitrage: float = Field(0.08, ge=0, le=1.0, description="Annual volatility for arbitrage allocation.")
    return_distribution: ReturnDistribution = Field(ReturnDistribution.LOGNORMAL, description="Distribution type for return simulation: normal or lognormal.")
    monte_carlo_seed: Optional[int] = Field(None, description="Optional random seed for reproducible simulations.")

    @model_validator(mode="after")
    def validate_plan(self):
        if self.retirement_age <= self.current_age:
            raise ValueError("Retirement age must be greater than current age.")
        if self.life_expectancy < self.retirement_age:
            raise ValueError("Life expectancy must be greater than or equal to retirement age.")

        adhoc_ages = []
        for expense in self.adhoc_expenses:
            if not (self.current_age <= expense.age <= self.life_expectancy):
                raise ValueError(f"Ad-hoc expense age ({expense.age}) must be between current age ({self.current_age}) and life expectancy ({self.life_expectancy}).")
            if expense.age in adhoc_ages:
                raise ValueError(f"Duplicate ad-hoc expense age found: {expense.age}.")
            adhoc_ages.append(expense.age)

        allocation_total = self.allocation_equity + self.allocation_debt + self.allocation_arbitrage
        if abs(allocation_total - 1.0) > 0.01:
            raise ValueError(f"Portfolio allocation (equity + debt + arbitrage) must sum to approximately 100%. Current total: {(allocation_total * 100):.1f}%.")
        
        equity_split_total = self.equity_ltcg_split + self.equity_stcg_split
        if abs(equity_split_total - 1.0) > 0.01:
            raise ValueError(f"Equity sub-allocation (LTCG + STCG) must sum to approximately 100%. Current total: {(equity_split_total * 100):.1f}%.")
        
        if self.include_pension:
            if self.pension_start_age is None:
                raise ValueError("Pension start age is required when pension is included.")
            if self.pension_start_age < self.current_age:
                raise ValueError("Pension start age cannot be in the past.")
            if self.pension_start_age > self.life_expectancy:
                raise ValueError("Pension start age cannot be after life expectancy.")
            if self.annual_pension <= 0:
                raise ValueError("Annual pension must be a positive value when pension is included.")

        return self
