# ui/instances.py
"""Mục 4-5: Instance và Floating IP."""
import streamlit as st

from api.compute import (
    get_flavors, list_instances, create_instance, delete_instance,
    server_action, list_keypairs,
)
from api.image import get_images
from api.network import (
    get_networks, get_instance_ports, list_floating_ips, create_floating_ip,
)
from ui.common import (
    DEFAULT_USER_DATA, load, invalidate, refresh_button, flash, table,
    short_id, choices, external_networks, server_ips,
)

NO_KEYPAIR = "Không dùng Key Pair"


def instance_spec_fields(token, key):
    """Các trường cấu hình máy ảo, dùng cho cả tạo Instance và tăng số lượng.

    Trả về dict khớp tham số của create_instance (không gồm tên máy ảo).
    """
    images = load("images", get_images, token)
    flavors = load("flavors", get_flavors, token)
    networks = load("networks", get_networks, token)

    if images:
        options = choices(images, lambda i: f"{i.get('name', 'N/A')} ({short_id(i['id'])})")
        image_id = options[st.selectbox("Image", list(options), key=f"{key}_image")]
    else:
        image_id = st.text_input("Image ID", key=f"{key}_image")

    if flavors:
        options = choices(
            flavors,
            lambda f: f"{f.get('name')} (vCPU: {f['vcpus']}, RAM: {f['ram']}MB, Disk: {f['disk']}GB)",
        )
        flavor_id = options[st.selectbox("Flavor", list(options), key=f"{key}_flavor")]
    else:
        flavor_id = st.text_input("Flavor ID", key=f"{key}_flavor")

    if networks:
        options = choices(networks)
        network_id = options[st.selectbox("Network", list(options), key=f"{key}_network")]
    else:
        network_id = st.text_input("Network ID", key=f"{key}_network")

    keypairs = load("keypairs", list_keypairs, token)
    key_options = [NO_KEYPAIR] + [kp.get("name", "") for kp in keypairs]
    key_name = st.selectbox("Key Pair (Không bắt buộc)", key_options, key=f"{key}_keypair")

    security_group = st.text_input("Security Group", value="default", key=f"{key}_sg").strip()

    with st.expander("User Data Script (chạy khi máy ảo khởi động)"):
        user_data = st.text_area("Bash Script", value=DEFAULT_USER_DATA, height=150, key=f"{key}_user_data")

    return {
        "image_id": image_id,
        "flavor_id": flavor_id,
        "network_id": network_id,
        "key_name": None if key_name == NO_KEYPAIR else key_name,
        "security_groups": [security_group] if security_group else None,
        "user_data": user_data,
    }


def _render_instance_list(token):
    refresh_button("Làm mới danh sách Instance", "instances")
    instances = load("instances", list_instances, token)
    if not instances:
        st.info("Chưa có Instance nào. Hãy tạo mới ở tab bên cạnh.")
        return

    st.caption(f"Tổng số: {len(instances)} Instance")
    table([
        {
            "ID": short_id(s["id"]),
            "Tên": s.get("name", "N/A"),
            "Trạng thái": s.get("status", "N/A"),
            "Địa chỉ IP": ", ".join(server_ips(s)) or "N/A",
            "Flavor": s.get("flavor", {}).get("original_name", s.get("flavor", {}).get("id", "N/A")),
            "Image": short_id(s["image"]["id"]) if s.get("image") else "Volume",
        }
        for s in instances
    ])

    st.markdown("##### Thao tác nhanh")
    options = choices(instances, lambda s: f"{s.get('name')} [{s.get('status')}]")
    server_id = options[st.selectbox("Chọn Instance", list(options), key="inst_action")]

    actions = [
        ("Bật", "start", "Đã gửi lệnh Bật."),
        ("Tắt", "stop", "Đã gửi lệnh Tắt."),
        ("Khởi động lại", "reboot", "Đã gửi lệnh Khởi động lại."),
    ]
    columns = st.columns(len(actions) + 1)
    for col, (label, action, message) in zip(columns, actions):
        if col.button(label, width="stretch", key=f"inst_{action}"):
            ok, err = server_action(token, server_id, action)
            if ok:
                flash("success", message)
                invalidate("instances")
                st.rerun()
            else:
                st.error(err)

    if columns[-1].button("Xóa", width="stretch", type="primary", key="inst_delete"):
        ok, err = delete_instance(token, server_id)
        if ok:
            flash("success", "Đã xóa Instance.")
            invalidate("instances")
            st.rerun()
        else:
            st.error(err)


def _render_instance_create(token):
    with st.form("create_instance_form"):
        name = st.text_input("Tên Instance", placeholder="Ví dụ: nhom12_vm1")
        spec = instance_spec_fields(token, "create")
        submitted = st.form_submit_button("Khởi tạo Instance")

    if not submitted:
        return
    if not name.strip() or not all(spec[k] for k in ("image_id", "flavor_id", "network_id")):
        st.warning("Vui lòng nhập đủ Tên, Image, Flavor và Network.")
        return

    server, err = create_instance(token, name=name.strip(), **spec)
    if server:
        st.success(f"Đang khởi tạo Instance {server.get('name')} (ID: {server.get('id')}).")
        st.info("Trạng thái ban đầu là BUILD, làm mới danh sách sau vài giây để xem ACTIVE.")
        invalidate("instances")
    else:
        st.error(err)


def render_instances(token):
    st.subheader("4. Quản lý Instance (Máy ảo)")
    tab_list, tab_create = st.tabs(["Danh sách Instance", "Tạo Instance mới"])
    with tab_list:
        _render_instance_list(token)
    with tab_create:
        _render_instance_create(token)


def render_floating_ip(token):
    st.subheader("5. Gắn Floating IP")
    instances = load("instances", list_instances, token)
    networks = load("networks", get_networks, token)

    refresh_button("Làm mới danh sách Floating IP", "floating_ips")
    fips = load("floating_ips", list_floating_ips, token)
    if fips:
        table([
            {
                "Floating IP": f.get("floating_ip_address"),
                "Port ID": f.get("port_id"),
                "Trạng thái": f.get("status"),
            }
            for f in fips
        ])

    if not instances:
        st.info("Cần có Instance trước khi gắn Floating IP.")
        return

    externals = external_networks(networks)
    if not externals:
        st.warning("Không tìm thấy External Network. Hãy kiểm tra quyền truy cập hoặc cấu hình mạng.")
        return

    vm_options = choices(instances, lambda s: f"{s.get('name')} [{s.get('status')}]")
    ext_options = choices(externals)
    col_vm, col_ext = st.columns(2)
    vm_id = vm_options[col_vm.selectbox("Máy ảo cần gắn Floating IP", list(vm_options), key="fip_vm")]
    ext_id = ext_options[col_ext.selectbox("External Network", list(ext_options), key="fip_ext")]

    if not st.button("Gắn Floating IP mới", key="attach_fip"):
        return

    ports, err = get_instance_ports(token, vm_id)
    if ports is None:
        st.error(err)
        return
    port = next((p for p in ports if p.get("fixed_ips")), None)
    if not port:
        st.error("Máy ảo chưa có port mạng với Fixed IP. Hãy kiểm tra Network và trạng thái Instance.")
        return

    fip, err = create_floating_ip(token, ext_id, port["id"])
    if fip:
        invalidate("floating_ips")
        st.success("Đã gắn Floating IP.")
        st.code(f"http://{fip.get('floating_ip_address')}")
        st.caption("Nếu chưa truy cập được, kiểm tra Security Group, routing và trạng thái Nginx.")
    else:
        st.error(err)
