"""FastAPI backend for EcoScan AI."""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from database import (
    get_current_streak,
    get_impact_distribution,
    get_live_environmental_score,
    get_monthly_scans,
    get_scan_by_id,
    get_scan_history,
    get_total_co2,
    get_total_scans,
    get_trend_line,
    get_weekly_co2_series,
    init_db,
    insert_scan,
)
from disposal import SUPPORTED_CITIES, get_disposal_instruction
from scoring import IMPACT_TO_LABEL, estimate_co2, score_product, suggest_alternative

app = FastAPI(title="EcoScan AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"


class ScanRequest(BaseModel):
    barcode: str = Field(min_length=5, max_length=32)
    city: str


class ProductResult(BaseModel):
    barcode: str
    city: str
    product_name: str
    product_image: Optional[str]
    impact_score: str
    impact_label: str
    impact_reason: str
    co2_estimate: float
    disposal_type: str
    disposal_detail: str
    disposal_icon: str
    suggested_alternative: str
    packaging_text: str


def fetch_product_from_open_food_facts(barcode: str) -> Dict[str, Any]:
    """Fetch product details by barcode."""
    try:
        response = requests.get(OPEN_FOOD_FACTS_URL.format(barcode=barcode), timeout=12)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Open Food Facts request failed: {exc}") from exc

    if payload.get("status") != 1 or not payload.get("product"):
        raise HTTPException(status_code=404, detail="Product not found.")

    return payload["product"]


def _build_packaging_text(product: Dict[str, Any]) -> str:
    tags = product.get("packaging_tags") or []
    packaging_raw = product.get("packaging") or ""
    return " ".join(tags + [packaging_raw]).strip()


def build_product_result(barcode: str, city: str) -> ProductResult:
    if city not in SUPPORTED_CITIES:
        raise HTTPException(status_code=400, detail=f"Unsupported city. Use one of: {SUPPORTED_CITIES}")

    product = fetch_product_from_open_food_facts(barcode)
    product_name = (
        product.get("product_name")
        or product.get("product_name_en")
        or "Unknown Product"
    )
    product_image = product.get("image_url")
    impact_score, impact_reason = score_product(product)
    co2 = estimate_co2(impact_score)
    packaging_text = _build_packaging_text(product)
    disposal = get_disposal_instruction(city, packaging_text)
    alternative = suggest_alternative(impact_score, product_name)

    return ProductResult(
        barcode=barcode,
        city=city,
        product_name=product_name,
        product_image=product_image,
        impact_score=impact_score,
        impact_label=IMPACT_TO_LABEL.get(impact_score, "Medium Impact"),
        impact_reason=impact_reason,
        co2_estimate=co2,
        disposal_type=disposal["disposal_type"],
        disposal_detail=disposal["detail"],
        disposal_icon=disposal["icon"],
        suggested_alternative=alternative,
        packaging_text=packaging_text,
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/cities")
def get_cities() -> Dict[str, List[str]]:
    return {"cities": list(SUPPORTED_CITIES)}


@app.post("/analyze", response_model=ProductResult)
def analyze_product(request: ScanRequest) -> ProductResult:
    return build_product_result(request.barcode.strip(), request.city)


@app.post("/scan")
def save_scan(request: ScanRequest) -> Dict[str, Any]:
    result = build_product_result(request.barcode.strip(), request.city)
    scan_id = insert_scan(
        product_name=result.product_name,
        barcode=result.barcode,
        city=result.city,
        impact_score=result.impact_score,
        disposal_type=result.disposal_type,
        co2_estimate=result.co2_estimate,
    )
    scan_row = get_scan_by_id(scan_id)
    return {"saved": True, "scan": scan_row, "result": result.model_dump()}


@app.get("/history")
def history(limit: int = Query(default=100, ge=1, le=1000)) -> Dict[str, List[Dict[str, Any]]]:
    return {"items": get_scan_history(limit=limit)}


@app.get("/analytics")
def analytics() -> Dict[str, Any]:
    return {
        "total_scans": get_total_scans(),
        "total_co2": round(get_total_co2(), 2),
        "environmental_score": get_live_environmental_score(days=7),
        "weekly_co2": get_weekly_co2_series(),
        "impact_distribution": get_impact_distribution(),
        "trend_line": get_trend_line(days=30),
        "streak": get_current_streak(),
    }


@app.get("/streak")
def streak() -> Dict[str, int]:
    return {"days": get_current_streak()}


@app.get("/export/monthly")
def export_monthly_csv(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> StreamingResponse:
    rows = get_monthly_scans(year=year, month=month)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "product_name",
            "barcode",
            "city",
            "impact_score",
            "disposal_type",
            "co2_estimate",
            "timestamp",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["product_name"],
                row["barcode"],
                row["city"],
                row["impact_score"],
                row["disposal_type"],
                row["co2_estimate"],
                row["timestamp"],
            ]
        )

    output = io.BytesIO(buffer.getvalue().encode("utf-8"))
    filename = f"ecoscan_report_{year:04d}_{month:02d}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(output, media_type="text/csv", headers=headers)

