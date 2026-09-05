from models import PlannerInputs

def calculate_portfolio_expected_return(inputs: PlannerInputs) -> float:
    """
    Calculate the weighted expected portfolio return based on asset allocations and returns.
    
    Formula:
        allocation_equity * return_equity +
        allocation_debt * return_debt +
        allocation_arbitrage * return_arbitrage +
        allocation_reit * return_reit
    
    Args:
        inputs: PlannerInputs object containing allocation and return fields
        
    Returns:
        float: The weighted expected portfolio return
    """
    return (
        inputs.allocation_equity * inputs.return_equity +
        inputs.allocation_debt * inputs.return_debt +
        inputs.allocation_arbitrage * inputs.return_arbitrage +
        inputs.allocation_reit * inputs.return_reit
    )