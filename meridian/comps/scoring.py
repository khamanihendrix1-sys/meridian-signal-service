from __future__ import annotations

from typing import TypedDict
from dataclasses import dataclass
from decimal import Decimal
from math import cos, radians, sin, sqrt


class CompAdjustment(TypedDict):
    factor: str
    delta: int
    reason: str


@dataclass
class CompScore:
    """Score and adjustment result for a candidate comparable."""
    distance_miles: float
    sold_date_delta_days: int
    raw_similarity: float
    adjustments: list[CompAdjustment]
    adjusted_price: Decimal


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in miles between two points."""
    r = 3958.8  # Earth radius in miles
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)

    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    c = 2 * sqrt(a and a or 0)
    return r * c


def score_comparable(
    *,
    subject_price: Decimal,
    subject_sqft: int | None,
    subject_beds: int | None,
    subject_baths: float | None,
    candidate_price: Decimal,
    candidate_sqft: int | None,
    candidate_beds: int | None,
    candidate_baths: float | None,
    distance_miles: float,
    sold_date_delta_days: int,
) -> CompScore:
    """Score a candidate comparable and produce adjustment factors."""
    weights = {
        "distance": 0.25,
        "price": 0.25,
        "beds": 0.15,
        "baths": 0.15,
        "sqft": 0.1,
        "recency": 0.1,
    }
    adjustments: list[CompAdjustment] = []

    distance_score = max(0.0, 1.0 - (distance_miles / 10.0))
    price_ratio = float(candidate_price / subject_price) if subject_price > 0 else 1.0
    price_score = max(0.0, 1.0 - abs(price_ratio - 1.0))
    bed_score = 1.0 if subject_beds == candidate_beds else max(0.0, 1.0 - abs((subject_beds or 0) - (candidate_beds or 0)) * 0.1)
    bath_score = 1.0 if subject_baths == candidate_baths else max(0.0, 1.0 - abs((subject_baths or 0.0) - (candidate_baths or 0.0)) * 0.1)
    sqft_score = 1.0 if subject_sqft and candidate_sqft and subject_sqft == candidate_sqft else max(0.0, 1.0 - abs((subject_sqft or 0) - (candidate_sqft or 0)) / 1000.0)
    recency_score = max(0.0, 1.0 - (sold_date_delta_days / 365.0))

    raw_similarity = (
        distance_score * weights["distance"]
        + price_score * weights["price"]
        + bed_score * weights["beds"]
        + bath_score * weights["baths"]
        + sqft_score * weights["sqft"]
        + recency_score * weights["recency"]
    )

    if distance_miles > 2.0:
        adjustments.append({"factor": "distance", "delta": -5000, "reason": "distance greater than 2 miles"})
    if price_ratio > 1.05:
        adjustments.append({"factor": "price", "delta": -10000, "reason": "candidate priced above subject"})
    elif price_ratio < 0.95:
        adjustments.append({"factor": "price", "delta": 10000, "reason": "candidate priced below subject"})
    if subject_sqft and candidate_sqft and abs(subject_sqft - candidate_sqft) > 250:
        adjustments.append({"factor": "sqft", "delta": -5000, "reason": "significant sqft difference"})
    if subject_beds and candidate_beds and abs(subject_beds - candidate_beds) > 1:
        adjustments.append({"factor": "beds", "delta": -7500, "reason": "bedroom count differs"})

    adjustment_total = sum(item["delta"] for item in adjustments)
    adjusted_price = candidate_price + Decimal(str(adjustment_total))

    return CompScore(
        distance_miles=distance_miles,
        sold_date_delta_days=sold_date_delta_days,
        raw_similarity=round(raw_similarity, 4),
        adjustments=adjustments,
        adjusted_price=adjusted_price,
    )
