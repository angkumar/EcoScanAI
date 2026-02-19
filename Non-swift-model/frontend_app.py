"""Streamlit frontend for EcoScan AI."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

import cv2
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components

from camera import find_first_readable_camera, scan_barcode_from_webcam, test_camera_access

API_BASE_DEFAULT = "http://192.168.1.118:8000"
STREAMLIT_PHONE_URL = "http://192.168.1.118:8501"


def setup_pwa() -> None:
    """Inject PWA head tags, register service worker, and install prompt UI."""
    components.html(
        """
        <script>
          const candidates = {
            manifest: ["/app/static/manifest.json", "/static/manifest.json"],
            css: ["/app/static/mobile.css", "/static/mobile.css"],
            sw: ["/app/static/service-worker.js", "/static/service-worker.js"]
          };

          const pickFirstReachable = async (urls) => {
            for (const url of urls) {
              try {
                const res = await fetch(url, { method: "HEAD", cache: "no-cache" });
                if (res.ok) return url;
              } catch (e) {}
            }
            return urls[0];
          };

          (async () => {
            const head = window.parent.document.head;
            const body = window.parent.document.body;

            const manifestUrl = await pickFirstReachable(candidates.manifest);
            const cssUrl = await pickFirstReachable(candidates.css);
            const swUrl = await pickFirstReachable(candidates.sw);

            const setMeta = (name, content, attr = "name") => {
              let tag = head.querySelector(`meta[${attr}="${name}"]`);
              if (!tag) {
                tag = window.parent.document.createElement("meta");
                tag.setAttribute(attr, name);
                head.appendChild(tag);
              }
              tag.setAttribute("content", content);
            };

            const setLink = (rel, href) => {
              let tag = head.querySelector(`link[rel="${rel}"]`);
              if (!tag) {
                tag = window.parent.document.createElement("link");
                tag.setAttribute("rel", rel);
                head.appendChild(tag);
              }
              tag.setAttribute("href", href);
            };

            setMeta("theme-color", "#00ff7f");
            setMeta("apple-mobile-web-app-capable", "yes");
            setMeta("apple-mobile-web-app-status-bar-style", "black-translucent");
            setMeta("apple-mobile-web-app-title", "EcoScan");
            setMeta("mobile-web-app-capable", "yes");
            setMeta("viewport", "width=device-width, initial-scale=1, viewport-fit=cover", "name");

            setLink("manifest", manifestUrl);
            setLink("apple-touch-icon", manifestUrl.replace("manifest.json", "icons/icon-192.png"));
            setLink("stylesheet", cssUrl);

            if ("serviceWorker" in navigator) {
              try {
                await navigator.serviceWorker.register(swUrl);
              } catch (e) {
                console.warn("SW registration failed", e);
              }
            }

            if (!body.querySelector("#ecoscan-install-btn")) {
              const installBtn = window.parent.document.createElement("button");
              installBtn.id = "ecoscan-install-btn";
              installBtn.innerText = "Install EcoScan";
              installBtn.style.cssText = `
                position: fixed; right: 16px; bottom: 16px; z-index: 99999;
                border: 1px solid rgba(0,255,127,.6); border-radius: 999px;
                background: rgba(0,255,127,.16); color: #d8ffe9;
                font-weight: 700; padding: 10px 14px; cursor: pointer; display:none;
                box-shadow: 0 0 16px rgba(0,255,127,.24);
              `;
              body.appendChild(installBtn);

              let deferredPrompt = null;
              window.parent.addEventListener("beforeinstallprompt", (e) => {
                e.preventDefault();
                deferredPrompt = e;
                installBtn.style.display = "block";
              });

              installBtn.addEventListener("click", async () => {
                if (!deferredPrompt) return;
                deferredPrompt.prompt();
                await deferredPrompt.userChoice;
                deferredPrompt = null;
                installBtn.style.display = "none";
              });
            }
          })();
        </script>
        """,
        height=0,
    )


def trigger_haptic(ms: int = 35) -> None:
    components.html(
        f"""
        <script>
          if (window.parent.navigator && window.parent.navigator.vibrate) {{
            window.parent.navigator.vibrate({ms});
          }}
        </script>
        """,
        height=0,
    )


def impact_color(impact_score: Optional[str]) -> str:
    mapping = {"Green": "#3dffb6", "Yellow": "#ffe066", "Red": "#ff5d73"}
    return mapping.get(impact_score or "", "#4cf2a0")


def inject_css(current_impact: Optional[str]) -> None:
    glow = impact_color(current_impact)
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Manrope:wght@400;600;700;800&display=swap');
            :root {{
                --bg: #0e1117;
                --panel: rgba(255, 255, 255, 0.06);
                --stroke: rgba(255, 255, 255, 0.16);
                --text: #e9edf5;
                --muted: #9ba6bd;
                --accent: #4cf2a0;
                --impact: {glow};
            }}
            .stApp {{
                background:
                    radial-gradient(circle at 15% 20%, color-mix(in srgb, var(--impact) 28%, transparent), transparent 40%),
                    radial-gradient(circle at 80% 10%, rgba(76, 242, 160, 0.15), transparent 38%),
                    linear-gradient(160deg, #0b0f15 0%, #0e1117 58%, #0a1018 100%);
                color: var(--text);
            }}
            .block-container {{
                max-width: 1200px;
                padding-top: 1.6rem;
                padding-bottom: 2.5rem;
            }}
            .title-wrap {{
                border: 1px solid var(--stroke);
                border-radius: 26px;
                padding: 1.5rem 1.6rem;
                background: linear-gradient(140deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
                box-shadow: 0 0 30px rgba(0,0,0,0.45), inset 0 0 26px rgba(76,242,160,0.08);
                backdrop-filter: blur(14px);
                animation: fadeIn 0.6s ease;
            }}
            .title-wrap h1 {{
                margin: 0;
                font-family: "Orbitron", sans-serif;
                font-weight: 900;
                letter-spacing: 0.08em;
                font-size: clamp(2rem, 4vw, 3rem);
            }}
            .subtitle {{
                margin-top: 0.3rem;
                color: var(--muted);
                font-size: 1.03rem;
            }}
            .glass-card {{
                border: 1px solid var(--stroke);
                border-radius: 20px;
                padding: 1rem 1.1rem;
                margin-bottom: 1rem;
                background: var(--panel);
                backdrop-filter: blur(12px);
                box-shadow: 0 8px 28px rgba(0,0,0,0.35);
                animation: fadeIn 0.5s ease;
            }}
            .metric-value {{
                font-family: "Orbitron", sans-serif;
                font-size: 1.8rem;
                font-weight: 700;
                line-height: 1.2;
            }}
            .metric-label {{
                color: var(--muted);
                font-size: 0.86rem;
                letter-spacing: 0.03em;
                text-transform: uppercase;
            }}
            .impact-badge {{
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 0.5rem 1rem;
                border: 1px solid color-mix(in srgb, var(--impact) 70%, white);
                background: color-mix(in srgb, var(--impact) 20%, transparent);
                box-shadow: 0 0 16px color-mix(in srgb, var(--impact) 35%, transparent);
                font-weight: 800;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                animation: pulse 2s infinite;
            }}
            .scan-cta .stButton > button {{
                width: 100%;
                border-radius: 14px;
                border: 1px solid rgba(76, 242, 160, 0.45);
                color: #d9ffef;
                background: linear-gradient(135deg, rgba(76,242,160,0.32), rgba(76,242,160,0.12));
                box-shadow: 0 0 18px rgba(76,242,160,0.28);
                font-weight: 700;
                transition: all 0.25s ease;
            }}
            .scan-cta .stButton > button:hover {{
                transform: translateY(-1px);
                box-shadow: 0 0 26px rgba(76,242,160,0.4);
            }}
            .history-row {{
                display: grid;
                grid-template-columns: 2fr 1fr 1fr 1fr 1.3fr;
                gap: 0.5rem;
                font-size: 0.9rem;
                padding: 0.45rem 0;
                border-bottom: 1px solid rgba(255,255,255,0.09);
            }}
            .history-head {{
                color: var(--muted);
                font-weight: 700;
                text-transform: uppercase;
                font-size: 0.78rem;
                letter-spacing: 0.04em;
            }}
            .stTextInput > div > div > input,
            .stSelectbox > div > div {{
                border-radius: 12px !important;
                background: rgba(255,255,255,0.07) !important;
                color: var(--text) !important;
                border: 1px solid var(--stroke) !important;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(6px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            @keyframes pulse {{
                0% {{ box-shadow: 0 0 12px color-mix(in srgb, var(--impact) 45%, transparent); }}
                50% {{ box-shadow: 0 0 24px color-mix(in srgb, var(--impact) 60%, transparent); }}
                100% {{ box-shadow: 0 0 12px color-mix(in srgb, var(--impact) 45%, transparent); }}
            }}
            @media (max-width: 880px) {{
                .title-wrap {{
                    border-radius: 18px;
                    padding: 1rem;
                }}
                .scan-cta .stButton > button {{
                    min-height: 52px;
                    font-size: 1rem;
                }}
                .glass-card {{
                    border-radius: 16px;
                    padding: 0.9rem;
                }}
                .history-row {{
                    grid-template-columns: 1fr;
                    gap: 0.2rem;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def api_call(
    method: str, endpoint: str, base_url: str, payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=15)
        elif method == "POST":
            response = requests.post(url, json=payload or {}, timeout=25)
        else:
            raise ValueError(f"Unsupported method: {method}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc


def fetch_csv_report(base_url: str, year: int, month: int) -> bytes:
    url = f"{base_url.rstrip('/')}/export/monthly?year={year}&month={month}"
    response = requests.get(url, timeout=25)
    response.raise_for_status()
    return response.content


def render_metrics(analytics: Dict[str, Any]) -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="glass-card">
                <div class="metric-value">{analytics.get("environmental_score", 0)}</div>
                <div class="metric-label">Live Environmental Score (7d)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="glass-card">
                <div class="metric-value">{analytics.get("streak", 0)} 🔥</div>
                <div class="metric-label">Daily Scan Streak</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="glass-card">
                <div class="metric-value">{analytics.get("total_co2", 0):.2f} kg</div>
                <div class="metric-label">Cumulative CO2 Footprint</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_result(result: Dict[str, Any]) -> None:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    center_left, center_right = st.columns([1.0, 1.2])

    with center_left:
        st.markdown(f"### {result['product_name']}")
        if result.get("product_image"):
            st.image(result["product_image"], use_container_width=True)
        else:
            st.info("No product image available.")

    with center_right:
        st.markdown(
            f"<div class='impact-badge'>{result['impact_score']} • {result['impact_label']}</div>",
            unsafe_allow_html=True,
        )
        st.write(result["impact_reason"])
        st.markdown("#### Disposal")
        st.write(
            f"{result['disposal_icon']} **{result['disposal_type']}**  \n"
            f"{result['disposal_detail']}"
        )
        st.markdown("#### CO2 Estimate")
        st.write(f"**{result['co2_estimate']:.2f} kg CO2e**")
        st.markdown("#### Suggested Lower-Impact Alternative")
        st.write(result["suggested_alternative"])

    st.markdown("</div>", unsafe_allow_html=True)


def render_history(items: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### Recent Scans")
    if not items:
        st.info("No scans yet.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown(
        """
        <div class="history-row history-head">
            <div>Product</div>
            <div>City</div>
            <div>Impact</div>
            <div>Disposal</div>
            <div>Time</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for row in items:
        st.markdown(
            f"""
            <div class="history-row">
                <div>{row['product_name']}</div>
                <div>{row['city']}</div>
                <div>{row['impact_score']}</div>
                <div>{row['disposal_type']}</div>
                <div>{row['timestamp']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_analytics_charts(analytics: Dict[str, Any]) -> None:
    weekly = analytics.get("weekly_co2", [])
    pie_data = analytics.get("impact_distribution", [])
    trend = analytics.get("trend_line", [])

    col1, col2 = st.columns(2)

    with col1:
        fig_weekly = go.Figure()
        fig_weekly.add_trace(
            go.Bar(
                x=[item["day"] for item in weekly],
                y=[item["co2"] for item in weekly],
                marker=dict(color="#4cf2a0"),
                name="CO2 (kg)",
            )
        )
        fig_weekly.update_layout(
            title="Weekly CO2 Impact",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_weekly, use_container_width=True)

    with col2:
        fig_pie = go.Figure(
            data=[
                go.Pie(
                    labels=[item["impact_score"] for item in pie_data],
                    values=[item["count"] for item in pie_data],
                    hole=0.48,
                    marker=dict(colors=["#ff5d73", "#ffe066", "#3dffb6"]),
                )
            ]
        )
        fig_pie.update_layout(
            title="Impact Distribution",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    fig_trend = go.Figure()
    fig_trend.add_trace(
        go.Scatter(
            x=[item["day"] for item in trend],
            y=[item["co2"] for item in trend],
            mode="lines+markers",
            line=dict(color="#76f7c4", width=3),
            marker=dict(size=7),
            name="CO2 Trend",
        )
    )
    fig_trend.update_layout(
        title="30-Day CO2 Trend Line",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_trend, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="EcoScan AI", page_icon="🌱", layout="wide")
    setup_pwa()

    if "current_impact" not in st.session_state:
        st.session_state.current_impact = None
    if "manual_barcode" not in st.session_state:
        st.session_state.manual_barcode = ""
    if "latest_analysis" not in st.session_state:
        st.session_state.latest_analysis = None
    if "camera_index" not in st.session_state:
        st.session_state.camera_index = 1
    if "force_mac_builtin" not in st.session_state:
        st.session_state.force_mac_builtin = True

    inject_css(st.session_state.current_impact)
    st.markdown(
        """
        <section class="title-wrap">
            <h1>EcoScan AI</h1>
            <div class="subtitle">Scan. Understand. Reduce.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Backend")
        base_url = st.text_input("FastAPI URL", value=API_BASE_DEFAULT)
        st.caption("Run backend with: uvicorn main:app --host 0.0.0.0 --port 8000")
        st.caption(f"Open on iPhone Safari: {STREAMLIT_PHONE_URL}")

    try:
        analytics = api_call("GET", "/analytics", base_url)
    except RuntimeError as error:
        st.error(
            "Could not reach FastAPI backend. Start it with `uvicorn main:app --reload` "
            f"and verify URL.\n\n{error}"
        )
        st.stop()

    render_metrics(analytics)

    page = st.radio("Navigate", ["Scanner", "Analytics"], horizontal=True)

    if page == "Scanner":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        c1, c2 = st.columns([1.2, 1])
        with c1:
            city = st.selectbox("City", ["San Francisco", "Chicago"])
            barcode_input = st.text_input(
                "Manual Barcode Entry",
                value=st.session_state.manual_barcode,
                key="barcode_input_field",
                placeholder="Fallback manual barcode entry",
            )
            st.session_state.manual_barcode = barcode_input.strip()
            st.session_state.force_mac_builtin = st.toggle(
                "Use only Mac built-in camera",
                value=st.session_state.force_mac_builtin,
                help="Skips typical Continuity Camera index (0) and auto-selects a local Mac camera.",
            )
            st.session_state.camera_index = int(
                st.number_input(
                    "Camera Index (manual override)",
                    min_value=0,
                    max_value=5,
                    value=st.session_state.camera_index,
                    step=1,
                    disabled=st.session_state.force_mac_builtin,
                )
            )

        with c2:
            st.markdown('<div class="scan-cta">', unsafe_allow_html=True)
            camera_test = st.button("Test Camera")
            scan_camera = st.button("Activate Camera Scan")
            analyze_click = st.button("Analyze Product")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if camera_test:
            if st.session_state.force_mac_builtin:
                preferred = [1, 2, 3, 4, 5]
                detected_index = find_first_readable_camera(preferred)
                if detected_index is None:
                    st.error(
                        "No readable built-in/local Mac camera found on indices 1-5. "
                        "Disable built-in-only mode to test index 0."
                    )
                else:
                    st.session_state.camera_index = detected_index
                    ok, message = test_camera_access(detected_index)
                    if ok:
                        st.success(f"{message} Using index {detected_index}.")
                    else:
                        st.error(message)
            else:
                ok, message = test_camera_access(st.session_state.camera_index)
                if ok:
                    st.success(message)
                else:
                    st.error(message)

        if scan_camera:
            scan_index = st.session_state.camera_index
            if st.session_state.force_mac_builtin:
                detected_index = find_first_readable_camera([1, 2, 3, 4, 5])
                if detected_index is None:
                    st.error(
                        "Built-in-only mode could not find a usable Mac camera. "
                        "Disable built-in-only mode and try manual index selection."
                    )
                    st.stop()
                scan_index = detected_index
                st.session_state.camera_index = detected_index

            preview = st.empty()
            with st.spinner("Opening webcam and scanning barcode..."):
                scan_result = scan_barcode_from_webcam(
                    timeout_seconds=15,
                    camera_index=scan_index,
                    on_frame=lambda frame: preview.image(
                        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                        channels="RGB",
                        caption="Scanning... hold barcode steady",
                        use_container_width=True,
                    ),
                )
            preview.empty()
            if scan_result.barcode:
                st.session_state.manual_barcode = scan_result.barcode
                trigger_haptic(45)
                st.success(
                    f"Barcode detected: {scan_result.barcode} "
                    f"(frames processed: {scan_result.frames_seen})"
                )
            else:
                st.error(scan_result.error or "No barcode detected from camera.")
                st.info("If this is macOS: allow camera access for your terminal app in System Settings.")

        if analyze_click:
            barcode = st.session_state.manual_barcode.strip()
            if not barcode:
                st.warning("Enter a barcode or use camera scan first.")
            else:
                try:
                    analysis = api_call(
                        "POST",
                        "/analyze",
                        base_url,
                        {"barcode": barcode, "city": city},
                    )
                    trigger_haptic(30)
                    st.session_state.latest_analysis = analysis
                    st.session_state.current_impact = analysis["impact_score"]
                except RuntimeError as error:
                    st.error(str(error))

        result = st.session_state.latest_analysis
        if result:
            render_result(result)

            save_click = st.button("Save Scan", use_container_width=True)
            if save_click:
                try:
                    saved = api_call(
                        "POST",
                        "/scan",
                        base_url,
                        {"barcode": result["barcode"], "city": result["city"]},
                    )
                    trigger_haptic(65)
                    st.success(
                        "Scan saved. Disposal: "
                        f"{saved['scan']['disposal_type']} | CO2: {saved['scan']['co2_estimate']:.2f} kg"
                    )
                    st.rerun()
                except RuntimeError as error:
                    st.error(str(error))

        history = api_call("GET", "/history?limit=25", base_url).get("items", [])
        render_history(history)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### Export Monthly Environmental Report")
        today = dt.date.today()
        col_y, col_m = st.columns(2)
        with col_y:
            year = st.number_input("Year", min_value=2000, max_value=2100, value=today.year)
        with col_m:
            month = st.number_input("Month", min_value=1, max_value=12, value=today.month)

        if st.button("Generate CSV Report"):
            try:
                csv_bytes = fetch_csv_report(base_url, int(year), int(month))
                st.download_button(
                    label="Download Report CSV",
                    data=csv_bytes,
                    file_name=f"ecoscan_report_{int(year):04d}_{int(month):02d}.csv",
                    mime="text/csv",
                )
            except requests.RequestException as error:
                st.error(f"CSV export failed: {error}")
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Install On iPhone / Android"):
        st.markdown(
            """
            - **Android (Chrome):** Tap the browser menu, then **Install app** or **Add to Home screen**.
            - **iPhone (Safari):** Tap **Share** -> **Add to Home Screen**.
            - After install, launch EcoScan AI from your home screen for full-screen app mode.
            """
        )

    if page == "Analytics":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### Environmental Intelligence Dashboard")
        st.write(
            f"Total scans: **{analytics.get('total_scans', 0)}**  |  "
            f"Total CO2 footprint: **{analytics.get('total_co2', 0):.2f} kg**"
        )
        st.markdown("</div>", unsafe_allow_html=True)
        render_analytics_charts(analytics)


if __name__ == "__main__":
    main()
