from models import PlannerInputs, StressScenario

def get_return_rate(age: int, inputs: PlannerInputs) -> float:
    """Determines the annual return rate, applying stress scenarios if applicable."""
    is_retired = age >= inputs.retirement_age

    if not is_retired:
        return inputs.pre_retirement_return

    # Apply stress scenarios for the first 2 years of retirement
    if age < inputs.retirement_age + 2:
        if inputs.stress_scenario == StressScenario.MILD_CRASH:
            return -0.10
        elif inputs.stress_scenario == StressScenario.SEVERE_CRASH:
            return -0.20

    return inputs.post_retirement_return