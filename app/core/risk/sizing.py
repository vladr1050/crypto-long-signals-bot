def position_size(account_value_usdc: float, risk_pct: float, entry: float, sl: float) -> float:
    """
    Returns base-asset quantity for spot.
    """
    if entry <= 0 or sl <= 0 or sl >= entry:
        return 0.0
    risk_amount = account_value_usdc * (risk_pct / 100.0)
    per_unit_risk = entry - sl
    qty = risk_amount / per_unit_risk
    return max(qty, 0.0)
