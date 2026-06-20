"""Streamlit UI: chat + grafik + jadval + "SQL ko'rsatish". API'ga requests orqali ulanadi.

Butun render `main()` ichida — shu sabab modulni import qilish st chaqiruvlarini ishga
tushirmaydi (import smoke testi xatosiz). `streamlit run` da __name__ == "__main__" -> main().
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests
import streamlit as st

# `streamlit run` sys.path[0] ni src/ui/ ga qo'yadi (root emas) -> `src` topilmaydi.
# Shu sabab loyiha root'ini path'ga qo'shamiz (seed_demo_biz.py bilan bir xil yondashuv).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agent.prompts import SAMPLE_PROMPTS  # noqa: E402
from src.config import get_settings  # noqa: E402

REQUEST_TIMEOUT = 120


def call_api(message: str, conversation_id: int | None) -> dict[str, Any]:
    """API /chat ni chaqiradi. Ulanish xatosi muloyim xabar bo'lib qaytadi."""
    api_url = get_settings().api_url
    payload: dict[str, Any] = {"message": message}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    try:
        resp = requests.post(f"{api_url}/chat", json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as exc:
        return {
            "conversation_id": conversation_id or 0,
            "text": (
                "API'ga ulanib bo'lmadi. Backend ishga tushganmi tekshiring "
                "(`uv run uvicorn src.api.main:app --reload`)."
            ),
            "sql": None,
            "rows": [],
            "vega_spec": None,
            "chart_title": "",
            "error_detail": str(exc),
        }


def save_chart_api(msg: dict[str, Any]) -> bool:
    """Joriy javob grafigini API /charts ga saqlaydi. Muvaffaqiyatda True."""
    spec = msg.get("vega_spec")
    if not spec:
        return False
    payload = {
        "conversation_id": msg.get("conversation_id"),
        "title": msg.get("chart_title") or "Grafik",
        "vega_spec": spec,
        "sql": msg.get("sql"),
    }
    try:
        resp = requests.post(
            f"{get_settings().api_url}/charts", json=payload, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


def list_saved_charts_api() -> list[dict[str, Any]]:
    """Saqlangan grafiklar ro'yxati (xatoda bo'sh)."""
    try:
        resp = requests.get(f"{get_settings().api_url}/charts", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return []


def delete_saved_chart_api(chart_id: int) -> bool:
    try:
        resp = requests.delete(
            f"{get_settings().api_url}/charts/{chart_id}", timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


def _render_assistant(msg: dict[str, Any], key: str = "") -> None:
    st.markdown(msg.get("text", ""))
    metrics = msg.get("metrics") or []
    if metrics:
        cols = st.columns(len(metrics))
        for col, m in zip(cols, metrics, strict=False):
            col.metric(m.get("label", ""), m.get("value", ""), m.get("delta"))
    spec = msg.get("vega_spec")
    if spec:
        st.vega_lite_chart(spec, use_container_width=True)
        if key and st.button("💾 Saqlash", key=f"save_{key}"):
            if save_chart_api(msg):
                st.success("Grafik saqlandi ✅ ('📌 Saqlangan' tabida ko'ring)")
            else:
                st.warning("Saqlab bo'lmadi (API ishlayaptimi?)")
    rows = msg.get("rows") or []
    sql = msg.get("sql")
    if sql:
        with st.expander("SQL ko'rsatish"):
            st.code(sql, language="sql")
    if rows:
        with st.expander(f"Natija jadvali ({len(rows)} qator)"):
            st.dataframe(rows, use_container_width=True)
    detail = msg.get("error_detail")
    if detail:
        with st.expander("Tafsilot (texnik)"):
            st.caption(detail)


def _render_saved_tab() -> None:
    """Saqlangan grafiklar gallereyasi (ko'rish + o'chirish)."""
    charts = list_saved_charts_api()
    if not charts:
        st.info("Hali grafik saqlanmagan. Suhbatda grafik ostidagi '💾 Saqlash' tugmasini bos.")
        return
    for c in charts:
        st.subheader(c.get("title") or "Grafik")
        created = (c.get("created_at") or "")[:19].replace("T", " ")
        if created:
            st.caption(created)
        spec = c.get("vega_spec")
        if spec:
            st.vega_lite_chart(spec, use_container_width=True)
        csql = c.get("sql")
        if csql:
            with st.expander("SQL"):
                st.code(csql, language="sql")
        if st.button("🗑 O'chirish", key=f"del_{c['id']}"):
            delete_saved_chart_api(c["id"])
            st.rerun()
        st.divider()


def _process_prompt(prompt: str) -> None:
    """Savolni yuboradi, tarixga yozadi. Render replay loop'da bo'ladi (rerun'dan keyin)."""
    st.session_state.history.append({"role": "user", "text": prompt})
    with st.spinner("Tahlil qilinmoqda…"):
        result = call_api(prompt, st.session_state.conversation_id)
    st.session_state.conversation_id = result.get("conversation_id")
    result["role"] = "assistant"
    st.session_state.history.append(result)


def main() -> None:
    st.set_page_config(page_title="Datachi — AI Analytics", page_icon="📊", layout="wide")
    st.title("📊 Datachi — AI Analytics")
    st.caption(
        "Savolingizni o'zbek, rus yoki ingliz tilida yozing — agent xavfsiz SQL yozadi, "
        "grafik va qisqa izoh qaytaradi. (Demo sintetik savdo bazasida.)"
    )

    if "history" not in st.session_state:
        st.session_state.history = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None

    with st.sidebar:
        st.header("Namuna savollar")
        for i, sample in enumerate(SAMPLE_PROMPTS):
            if st.button(sample, key=f"sample_{i}", use_container_width=True):
                st.session_state.pending = sample
        st.divider()
        if st.button("Yangi suhbat", use_container_width=True):
            st.session_state.history = []
            st.session_state.conversation_id = None
            st.rerun()

    tab_chat, tab_saved = st.tabs(["💬 Suhbat", "📌 Saqlangan grafiklar"])

    with tab_chat:
        # Mavjud tarixni qayta chizish (yangi javob ham shu yerda — _process_prompt + rerun).
        for i, msg in enumerate(st.session_state.history):
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant":
                    _render_assistant(msg, key=f"h{i}")
                else:
                    st.markdown(msg.get("text", ""))

    with tab_saved:
        _render_saved_tab()

    # chat_input tab'lardan tashqarida -> pastga mahkamlanadi, har ikki tab'da ko'rinadi.
    prompt = st.chat_input("Savolingiz…") or st.session_state.pop("pending", None)
    if prompt:
        _process_prompt(prompt)
        st.rerun()


if __name__ == "__main__":
    main()
