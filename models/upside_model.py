"""
Upside revenue streams — new fee-based revenue opportunities.

Converts portfolio-level TAM estimates to per-deal annual revenue using
total active customers as denominator.  Volume-based items (payout,
payment failures, account updater) scale with the per-deal volume
forecast; per-customer items (seat fee, dispute threshold) are flat
annual amounts per surviving deal.

All streams are modeled as 100% margin (no incremental COGS).
"""
from __future__ import annotations
from dataclasses import dataclass

import config as cfg
from models.volume_forecast import VolumeForecastYear


@dataclass
class UpsideYear:
    year: int
    payout_fee: float
    seat_fee: float
    dispute_threshold_fee: float
    payment_failure_fee: float
    account_updater_fee: float
    min_volume_penalty: float
    total: float


def compute_upside_per_deal(
    vol: VolumeForecastYear,
    total_customers: int = cfg.UPSIDE_TOTAL_CUSTOMERS,
) -> UpsideYear:
    """Compute upside revenue for a single deal for one year.

    Volume-based items use the deal's forecasted volume for that year.
    Per-customer items are constant annual amounts derived from
    portfolio totals / total_customers.
    """
    users_per_customer = cfg.UPSIDE_TOTAL_USERS / total_customers
    dispute_pct = cfg.UPSIDE_DISPUTE_CUSTOMERS / total_customers

    payout = vol.total * cfg.UPSIDE_PAYOUT_BPS

    seat = users_per_customer * cfg.UPSIDE_SEAT_FEE_MONTHLY * 12

    dispute = dispute_pct * cfg.UPSIDE_DISPUTE_FEE_MONTHLY * 12

    card_txns = vol.cc / cfg.UPSIDE_AVG_CARD_TXN_SIZE if cfg.UPSIDE_AVG_CARD_TXN_SIZE > 0 else 0
    ach_txns = vol.ach / cfg.ACH_AVG_TXN_SIZE if cfg.ACH_AVG_TXN_SIZE > 0 else 0
    bank_txns = vol.bank_network / cfg.ACH_AVG_TXN_SIZE if cfg.ACH_AVG_TXN_SIZE > 0 else 0
    total_txns = card_txns + ach_txns + bank_txns

    failures = total_txns * cfg.UPSIDE_PAYMENT_FAILURE_RATE * cfg.UPSIDE_PAYMENT_FAILURE_FEE

    updater = card_txns * cfg.UPSIDE_ACCOUNT_UPDATER_OPTIN * cfg.UPSIDE_ACCOUNT_UPDATER_FEE

    min_vol = cfg.UPSIDE_MIN_VOLUME_PENALTY_MRR * 12 / total_customers

    total = payout + seat + dispute + failures + updater + min_vol

    return UpsideYear(
        year=vol.year,
        payout_fee=payout,
        seat_fee=seat,
        dispute_threshold_fee=dispute,
        payment_failure_fee=failures,
        account_updater_fee=updater,
        min_volume_penalty=min_vol,
        total=total,
    )
