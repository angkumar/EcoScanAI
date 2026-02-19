"""EcoScan AI Streamlit application."""

from __future__ import annotations

import datetime as dt
from typing import Dict, Optional

import requests
import streamlit as st

from database import add_scan, get_scan_history, get_weekly_impact_points, init_db
from disposal import get_disposal_instruction
from scoring import score_product, suggest_alternative

APP_TITLE = "EcoScan AI"
APP_SUBTITLE = "Scan. Understand. Reduce."
CITY_OPTIONS = ["San Francisco", "Chicago"]


def inject_css(impact_score: Optional[str]) -> None:
    """Inject custom CSS theme with gradient and premium card styling."""
    gradient_map = {
        "Green": "linear-gradient(135deg, #0f2027 0%, #203a43 45%, #2e8b57 100%)",
        "Yellow": "linear-gradient(135deg, #3a2f0b 0%, #6a5d1f 45%, #8b7b2e 100%)",
        "Red": "linear-gradient(135deg, #2b0f14 0%, #5b1f2a 45%, #8b2e3b 100%)",
    }
    gradient = gradient_map.get(
        impact_score, "linear-gradient(135deg, #0b1722 0%, #1f2e45 45%, #2c5364 100%)"
    )

    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap');
            html, body, [class*="css"] {{
                font-family: 'Manrope', sans-serif;
            }}
            .stApp {{
                background: {gradient};
                color: #f8fbff;
            }}
            .block-container {{
                max-width: 1100px;
                padding-top: 2rem;
                padding-bottom: 3rem;
            }}
            .hero {{
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 24px;
                padding: 1.8rem;
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
                backdrop-filter: blur(6px);
                margin-bottom: 1.4rem;
            }}
            .hero h1 {{
                font-size: 3rem;
                margin: 0;
                line-height: 1.1;
                letter-spacing: -0.03em;
            }}
            .subtitle {{
                font-size: 1.1rem;
                margin-top: 0.4rem;
                opacity: 0.92;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.09);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 20px;
                padding: 1.2rem;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
                margin-bottom: 1rem;
            }}
            .stat {{
                font-size: 1.8rem;
                font-weight: 800;
                margin-bottom: 0.15rem;
            }}
            .stat-label {{
                font-size: 0.92rem;
                opacity: 0.85;
            }}
            .impact-badge {{
                display: inline-block;
                padding: 0.45rem 0.9rem;
                border-radius: 999px;
                font-weight: 800;
                font-size: 0.9rem;
                letter-spacing: 0.01em;
            }}
            .impact-green {{
                background: rgba(46, 139, 87, 0.2);
                color: #8cffc0;
                border: 1px solid rgba(140, 255, 192, 0.5);
            }}
            .impact-yellow {{
                background: rgba(224, 196, 84, 0.24);
                color: #ffe18e;
                border: 1px solid rgba(255, 225, 142, 0.45);
            }}
            .impact-red {{
                background: rgba(206, 72, 98, 0.24);
                color: #ff9ab0;
                border: 1px solid rgba(255, 154, 176, 0.45);
            }}
            .section-title {{
                margin-bottom: 0.7rem;
                font-size: 1.1rem;
                font-weight: 700;
            }}
            .history-row {{
                display: grid;
                grid-template-columns: 2fr 1fr 1fr 1.2fr;
                gap: 0.8rem;
                padding: 0.7rem 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.15);
                font-size: 0.92rem;
            }}
            .history-head {{
                font-weight: 700;
                opacity: 0.9;
            }}
            @media (max-width: 800px) {{
                .hero h1 {{
                    font-size: 2.2rem;
                }}
                .history-row {{
                    grid-template-columns: 1fr;
                    gap: 0.35rem;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def fetch_product(barcode: str) -> Optional[Dict]:
    """Fetch product data from Open Food Facts by barcode."""
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") == 1 and payload.get("product"):
            return payload["product"]
    except requests.RequestException:
        return None
    return None


def impact_badge_html(impact_score: str) -> str:
    """Return HTML for an impact badge."""
    labels = {
        "Green": ("impact-green", "Low Impact"),
        "Yellow": ("impact-yellow", "Medium Impact"),
        "Red": ("impact-red", "High Impact"),
    }
    class_name, text = labels.get(impact_score, ("impact-yellow", "Medium Impact"))
    return f"<span class='impact-badge {class_name}'>{impact_score} • {text}</span>"


def history_impact_label(score: str) -> str:
    """Convert score value into a compact visual label."""
    symbol = {"Green": "🟢", "Yellow": "🟡", "Red": "🔴"}.get(score, "🟡")
    return f"{symbol} {score}"


def parse_packaging(product: Dict) -> str:
    """Extract packaging text for disposal matching."""
    tags = product.get("packaging_tags") or []
    packaging_text = product.get("packaging") or ""
    return " ".join(tags) + " " + packaging_text


def render_header(total_scans: int, weekly_points: int) -> None:
    st.markdown(
        f"""
        <section class="hero">
            <h1>{APP_TITLE}</h1>
            <div class="subtitle">{APP_SUBTITLE}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="card">
                <div class="stat">{total_scans}</div>
                <div class="stat-label">Environmental Score Summary (Total Scans)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="card">
                <div class="stat">{weekly_points} pts</div>
                <div class="stat-label">Weekly Impact Summary (last 7 days)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_history(history: list[Dict]) -> None:
    st.markdown("<div class='section-title'>Scan History</div>", unsafe_allow_html=True)
    if not history:
        st.info("No scans yet. Start by scanning your first product.")
        return
    st.markdown(
        """
        <div class="card">
            <div class="history-row history-head">
                <div>Product</div>
                <div>City</div>
                <div>Impact</div>
                <div>Timestamp</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    for row in history:
        ts = row["timestamp"]
        try:
            formatted_ts = dt.datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            formatted_ts = ts
        st.markdown(
            f"""
            <div class="history-row">
                <div>{row["product_name"]}</div>
                <div>{row["city"]}</div>
                <div>{history_impact_label(row["impact_score"])}</div>
                <div>{formatted_ts}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="EcoScan AI",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_db()
    history = get_scan_history(limit=100)
    weekly_points = get_weekly_impact_points()

    if "current_impact" not in st.session_state:
        st.session_state.current_impact = None

    inject_css(st.session_state.current_impact)
    render_header(total_scans=len(history), weekly_points=weekly_points)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>City Selector</div>", unsafe_allow_html=True)
    city = st.selectbox("Choose city", CITY_OPTIONS, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Barcode Input</div>", unsafe_allow_html=True)
    barcode = st.text_input("Enter barcode", placeholder="e.g. 737628064502")
    scan_clicked = st.button("Scan Product", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if scan_clicked:
        if not barcode.strip():
            st.warning("Enter a barcode to scan.")
        else:
            with st.spinner("Scanning product..."):
                product = fetch_product(barcode.strip())

            if not product:
                st.error("Product not found in Open Food Facts. Try another barcode.")
            else:
                product_name = (
                    product.get("product_name")
                    or product.get("product_name_en")
                    or "Unknown Product"
                )
                image_url = product.get("image_url")
                impact_score, rationale = score_product(product)
                st.session_state.current_impact = impact_score
                packaging_text = parse_packaging(product)
                disposal = get_disposal_instruction(city, packaging_text)
                alternative = suggest_alternative(impact_score, product_name)

                add_scan(
                    product_name=product_name,
                    barcode=barcode.strip(),
                    city=city,
                    impact_score=impact_score,
                    disposal_type=disposal["type"],
                )

                st.markdown("<div class='section-title'>Results</div>", unsafe_allow_html=True)
                left, right = st.columns([1.1, 1.4])

                with left:
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown(f"### {product_name}")
                    if image_url:
                        st.image(image_url, use_container_width=True)
                    else:
                        st.info("No product image available.")
                    st.markdown(impact_badge_html(impact_score), unsafe_allow_html=True)
                    st.caption(rationale)
                    st.markdown("</div>", unsafe_allow_html=True)

                with right:
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown("#### Disposal Instruction")
                    st.markdown(
                        f"### {disposal['icon']} {disposal['type']}\n\n{disposal['detail']}"
                    )
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown("#### Suggested Lower-Impact Alternative")
                    st.write(alternative)
                    st.markdown("</div>", unsafe_allow_html=True)

                st.rerun()

    refreshed_history = get_scan_history(limit=100)
    refreshed_weekly = get_weekly_impact_points()
    st.markdown(
        f"""
        <div class="card">
            <div class="section-title">Weekly Environmental Tracking</div>
            Total weekly environmental score: <strong>{refreshed_weekly} pts</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_history(refreshed_history)


if __name__ == "__main__":
    main()
