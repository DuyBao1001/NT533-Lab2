# -*- coding: utf-8 -*-
import requests
import streamlit as st

from api.auth import get_token
from config import IDENTITY_URL
from ui.common import show_flash
from ui.instances import render_instances, render_floating_ip
from ui.loadbalancer import render_load_balancer
from ui.resources import render_flavor_image, render_network_subnet, render_router
from ui.scaling import render_scaling
from ui.sidebar import render_sidebar

st.set_page_config(page_title="OpenStack Lab 2", layout="centered")
st.title("Quản lý OpenStack API")

st.session_state.setdefault("token", None)


def render_login():
    st.subheader("Đăng nhập hệ thống")
    with st.form("login_form"):
        username = st.text_input("Username (MSSV)")
        password = st.text_input("Mật khẩu", type="password")
        project = st.text_input("Tên Project", value="NT533.R12.G12")
        submitted = st.form_submit_button("Kết nối")

    if not submitted:
        return
    if not username or not password or not project:
        st.warning("Vui lòng nhập đầy đủ thông tin.")
        return

    token, error = get_token(username, password, project)
    if token:
        st.session_state["token"] = token
        st.rerun()
    else:
        st.error(error)


def render_endpoints(token):
    with st.expander("Kiểm tra Service Endpoints (Catalog)"):
        if not st.button("Lấy Endpoints từ OpenStack"):
            return
        res = requests.get(f"{IDENTITY_URL}/auth/catalog", headers={"X-Auth-Token": token}, timeout=10)
        if res.status_code != 200:
            st.error(f"Lỗi: {res.status_code} - {res.text}")
            return
        for svc in res.json().get("catalog", []):
            st.markdown(f"**{svc.get('name')}** (`{svc.get('type')}`)")
            for ep in svc.get("endpoints", []):
                st.write(f"- `{ep.get('interface')}`: {ep.get('url')}")


def render_dashboard(token):
    st.success("Đã kết nối thành công với hạ tầng OpenStack!")
    st.write(f"**Token hiện tại:** `{token[:20]}...`")
    if st.button("Đăng xuất"):
        st.session_state.clear()
        st.rerun()

    render_sidebar()
    show_flash()
    render_endpoints(token)

    for render in (
        render_flavor_image,
        render_network_subnet,
        render_router,
        render_instances,
        render_floating_ip,
        render_load_balancer,
        render_scaling,
    ):
        st.divider()
        render(token)


token = st.session_state["token"]
if token:
    render_dashboard(token)
else:
    render_login()
