# ui/sidebar.py
"""Thanh bên: nhật ký HTTP request tới OpenStack."""
import json
import streamlit as st

import api.logger as api_logger

METHOD_COLORS = {
    "GET": "#2196F3",
    "POST": "#4CAF50",
    "PUT": "#FF9800",
    "DELETE": "#F44336",
    "PATCH": "#9C27B0",
}


def _status_color(code):
    if code is None:
        return "#9E9E9E"
    if 200 <= code < 300:
        return "#4CAF50"
    if 400 <= code < 500:
        return "#FF9800"
    return "#F44336" if code >= 500 else "#9E9E9E"


def _badge(text, color):
    return (
        f"<span style='background:{color};color:white;padding:2px 8px;"
        f"border-radius:4px;font-weight:bold;font-size:13px'>{text}</span>"
    )


def render_sidebar():
    with st.sidebar:
        st.markdown("## Nhật ký HTTP Request")

        col_clear, col_count = st.columns(2)
        if col_clear.button("Xóa log"):
            api_logger.clear_logs()
            st.rerun()
        col_count.caption(f"{len(api_logger.http_logs)} bản ghi")

        if not api_logger.http_logs:
            st.info("Chưa có request nào được ghi lại.")
            return

        for i, log in enumerate(api_logger.http_logs):
            status = str(log["response_status"]) if log["response_status"] else "ERR"
            duration = f'{log["duration_ms"]}ms' if log["duration_ms"] is not None else "?"

            with st.expander(f"{log['timestamp']}  {log['method']}  {status}  {duration}", expanded=(i == 0)):
                st.markdown(
                    _badge(log["method"], METHOD_COLORS.get(log["method"], "#607D8B"))
                    + "&nbsp;&nbsp;"
                    + _badge(status, _status_color(log["response_status"]))
                    + f"&nbsp;&nbsp;<span style='color:#666;font-size:12px'>{duration}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(log["url"])

                if log["request_body"]:
                    st.markdown("**Request Body:**")
                    st.code(json.dumps(log["request_body"], ensure_ascii=False, indent=2), language="json")
                if log["response_body"]:
                    st.markdown("**Response Body:**")
                    st.code(log["response_body"], language="json")
                if log["error"]:
                    st.error(f"Lỗi kết nối: {log['error']}")
