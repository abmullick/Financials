from models import PlannerInputs

def calculate_blended_tax_rate(inputs: PlannerInputs) -> float:
    """Calculates the blended effective tax rate based on portfolio allocation."""
    equity_ltcg_portion = inputs.allocation_equity * inputs.equity_ltcg_split
    equity_stcg_portion = inputs.allocation_equity * inputs.equity_stcg_split
    
    blended_tax_rate = (
        equity_ltcg_portion * inputs.tax_ltcg +
        equity_stcg_portion * inputs.tax_stcg +
        inputs.allocation_debt * inputs.tax_debt +
        inputs.allocation_arbitrage * inputs.tax_arbitrage
    )
    return blended_tax_rate