"""
Value-Added Services (VAS) fee revenue model.

Data-driven: iterates over cfg.VAS_ITEMS to compute per-deal annual
revenue for each fee stream.  Three items use volume-based models
(payout, payment failures, account updater); all others use a flat
per-customer rate derived from TAM_ARR / total_customers.

Build costs ($10K one-time for some items) are returned separately
so the engine can apply them to Y1 only.
"""
from __future__ import annotations
from dataclasses import dataclass, field

import config as cfg
from models.volume_forecast import VolumeForecastYear


@dataclass
class UpsideYear:
    year: int
    items: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    build_cost: float = 0.0


def compute_upside_per_deal(
    vol: VolumeForecastYear,
    total_customers: int = cfg.UPSIDE_TOTAL_CUSTOMERS,
    recommended_only: bool = False,
) -> UpsideYear:
    """Compute VAS fee revenue for a single deal for one year.

    Returns per-deal amounts (not yet scaled by deal count / retention).
    Build cost is the total one-time cost for all included items that
    require product investment, divided across total_customers.
    """
    items: dict[str, float] = {}
    build_cost_total = 0.0

    for item in cfg.VAS_ITEMS:
        if recommended_only and not item["recommended"]:
            continue

        name = item["name"]
        model = item["model"]
        tam_arr = item["tam_mrr"] * 12

        if model == "volume_payout":
            rev = vol.total * cfg.UPSIDE_PAYOUT_BPS
        elif model == "volume_failures":
            card_txns = vol.cc / cfg.UPSIDE_AVG_CARD_TXN_SIZE if cfg.UPSIDE_AVG_CARD_TXN_SIZE > 0 else 0
            ach_txns = vol.ach / cfg.ACH_AVG_TXN_SIZE if cfg.ACH_AVG_TXN_SIZE > 0 else 0
            bank_txns = vol.bank_network / cfg.ACH_AVG_TXN_SIZE if cfg.ACH_AVG_TXN_SIZE > 0 else 0
            total_txns = card_txns + ach_txns + bank_txns
            rev = total_txns * cfg.UPSIDE_PAYMENT_FAILURE_RATE * cfg.UPSIDE_PAYMENT_FAILURE_FEE
        elif model == "volume_updater":
            card_txns = vol.cc / cfg.UPSIDE_AVG_CARD_TXN_SIZE if cfg.UPSIDE_AVG_CARD_TXN_SIZE > 0 else 0
            rev = card_txns * cfg.UPSIDE_ACCOUNT_UPDATER_OPTIN * cfg.UPSIDE_ACCOUNT_UPDATER_FEE
        else:
            rev = tam_arr / total_customers

        items[name] = rev
        build_cost_total += item["build_cost"]

    return UpsideYear(
        year=vol.year,
        items=items,
        total=sum(items.values()),
        build_cost=build_cost_total,
    )
