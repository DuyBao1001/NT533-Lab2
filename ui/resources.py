# ui/resources.py
"""Mục 1-3: Flavor, Image, Network, Subnet, Router."""
import streamlit as st

from api.compute import get_flavors
from api.image import get_images
from api.network import (
    get_networks, create_network, delete_network,
    get_subnets, create_subnet, delete_subnet,
    list_routers, create_router, delete_router,
    add_router_interface, remove_router_interface,
)
from ui.common import (
    load, invalidate, refresh_button, flash, table, short_id, name_id,
    choices, external_networks, delete_box,
)

LIST_COLS, ACTION_COLS = 3, 2


def render_flavor_image(token):
    st.subheader("1. Danh sách Flavor & Image")
    tab_flavor, tab_image = st.tabs(["Flavor", "Image"])

    with tab_flavor:
        refresh_button("Làm mới Flavor", "flavors")
        flavors = load("flavors", get_flavors, token)
        if flavors:
            st.caption(f"Tổng số: {len(flavors)} Flavor")
            table([
                {
                    "ID": f["id"],
                    "Tên Flavor": f.get("name", "N/A"),
                    "vCPU": f.get("vcpus", 0),
                    "RAM (MB)": f.get("ram", 0),
                    "Disk (GB)": f.get("disk", 0),
                    "Ephemeral (GB)": f.get("OS-FLV-EXT-DATA:ephemeral", 0),
                }
                for f in flavors
            ])

    with tab_image:
        refresh_button("Làm mới Image", "images")
        images = load("images", get_images, token)
        if images:
            st.caption(f"Tổng số: {len(images)} Image")
            table([
                {
                    "ID": img["id"],
                    "Tên Image": img.get("name", "N/A"),
                    "Trạng thái": img.get("status", "N/A"),
                    "Định dạng": img.get("disk_format", "N/A"),
                    "Min Disk (GB)": img.get("min_disk", img.get("minDisk", 0)),
                    "Min RAM (MB)": img.get("min_ram", img.get("minRam", 0)),
                }
                for img in images
            ])


def render_network_subnet(token):
    st.subheader("2. Quản lý Network & Subnet")
    tab_net, tab_sub = st.tabs(["Network", "Subnet"])

    with tab_net:
        col_list, col_action = st.columns([LIST_COLS, ACTION_COLS])
        with col_list:
            st.markdown("##### Danh sách Network")
            refresh_button("Làm mới Network", "networks")
            networks = load("networks", get_networks, token)
            if networks:
                table([
                    {
                        "ID": n["id"],
                        "Tên Network": n.get("name", "N/A"),
                        "Trạng thái": n.get("status", "N/A"),
                        "Số Subnet": len(n.get("subnets", [])),
                    }
                    for n in networks
                ])

        with col_action:
            st.markdown("##### Tạo Network mới")
            with st.form("create_net_form"):
                name = st.text_input("Tên Network", placeholder="Ví dụ: nhom12_net")
                submitted = st.form_submit_button("Tạo Network")
            if submitted:
                if not name.strip():
                    st.warning("Vui lòng nhập tên Network.")
                else:
                    net, err = create_network(token, name.strip())
                    if net:
                        flash("success", f"Tạo thành công Network: {net.get('name')}")
                        invalidate("networks")
                        st.rerun()
                    else:
                        st.error(err)

            delete_box("Network", "net", networks, name_id, delete_network, token, "networks")

    with tab_sub:
        col_list, col_action = st.columns([LIST_COLS, ACTION_COLS])
        with col_list:
            st.markdown("##### Danh sách Subnet")
            refresh_button("Làm mới Subnet", "subnets")
            subnets = load("subnets", get_subnets, token)
            if subnets:
                table([
                    {
                        "ID": s["id"],
                        "Tên Subnet": s.get("name", "N/A"),
                        "Network ID": short_id(s.get("network_id")),
                        "CIDR": s.get("cidr", "N/A"),
                        "Gateway": s.get("gateway_ip", "N/A"),
                    }
                    for s in subnets
                ])

        with col_action:
            st.markdown("##### Tạo Subnet mới")
            with st.form("create_sub_form"):
                if networks:
                    net_options = choices(networks)
                    parent_net_id = net_options[st.selectbox("Thuộc Network", list(net_options))]
                else:
                    parent_net_id = st.text_input("Network ID", placeholder="Nhập ID của Network")
                name = st.text_input("Tên Subnet", placeholder="Ví dụ: nhom12_subnet")
                cidr = st.text_input("Dải mạng (CIDR)", placeholder="Ví dụ: 192.168.12.0/24")
                gateway = st.text_input("Gateway IP (Không bắt buộc)", placeholder="Ví dụ: 192.168.12.1")
                dns = st.text_input("DNS Nameservers (cách nhau bằng dấu phẩy)", value="8.8.8.8")
                submitted = st.form_submit_button("Tạo Subnet")
            if submitted:
                if not name.strip() or not cidr.strip() or not parent_net_id:
                    st.warning("Vui lòng nhập đủ Tên Subnet, CIDR và Network.")
                else:
                    sub, err = create_subnet(
                        token, parent_net_id, name.strip(), cidr.strip(), gateway,
                        [d.strip() for d in dns.split(",") if d.strip()],
                    )
                    if sub:
                        flash("success", f"Tạo thành công Subnet: {sub.get('name')}")
                        invalidate("subnets", "networks")
                        st.rerun()
                    else:
                        st.error(err)

            delete_box(
                "Subnet", "sub", subnets,
                lambda s: f"{s.get('name')} ({s.get('cidr')})",
                delete_subnet, token, "subnets", "networks",
            )


def _gateway_ip(router):
    info = router.get("external_gateway_info")
    if info and info.get("external_fixed_ips"):
        return info["external_fixed_ips"][0].get("ip_address", "Có gateway")
    return "Chưa gắn"


def render_router(token):
    st.subheader("3. Quản lý Router")
    tab_main, tab_interface = st.tabs(["Danh sách & Quản lý Router", "Cấu hình Interface (Nối Subnet)"])

    networks = load("networks", get_networks, token)
    subnets = load("subnets", get_subnets, token)

    with tab_main:
        col_list, col_action = st.columns([LIST_COLS, ACTION_COLS])
        with col_list:
            st.markdown("##### Danh sách Router")
            refresh_button("Làm mới Router", "routers")
            routers = load("routers", list_routers, token)
            if routers:
                table([
                    {
                        "ID": short_id(r["id"]),
                        "Tên Router": r.get("name", "N/A"),
                        "Trạng thái": r.get("status", "N/A"),
                        "Gateway IP": _gateway_ip(r),
                        "Admin State": "UP" if r.get("admin_state_up") else "DOWN",
                    }
                    for r in routers
                ])

        with col_action:
            st.markdown("##### Tạo Router mới")
            with st.form("create_router_form"):
                name = st.text_input("Tên Router", placeholder="Ví dụ: nhom12_router")
                externals = external_networks(networks)
                if externals:
                    ext_options = {"Không gắn Gateway ngoài": None}
                    ext_options.update(choices(externals))
                    ext_net_id = ext_options[st.selectbox("External Gateway Network", list(ext_options))]
                else:
                    ext_net_id = st.text_input("External Network ID (Không bắt buộc)") or None
                submitted = st.form_submit_button("Tạo Router")
            if submitted:
                if not name.strip():
                    st.warning("Vui lòng nhập tên Router.")
                else:
                    router, err = create_router(token, name.strip(), ext_net_id)
                    if router:
                        flash("success", f"Tạo thành công Router: {router.get('name')}")
                        invalidate("routers")
                        st.rerun()
                    else:
                        st.error(err)

            delete_box("Router", "router", routers, name_id, delete_router, token, "routers")

    with tab_interface:
        st.info("Gắn Subnet vào Router để các máy ảo trong Subnet đó truy cập được mạng ngoài qua Gateway.")
        routers = st.session_state.get("routers")
        if not routers or not subnets:
            st.warning("Cần có ít nhất 1 Router và 1 Subnet.")
            return

        router_options = choices(routers)
        subnet_options = choices(subnets, lambda s: f"{s.get('name')} - {s.get('cidr')}")
        col_router, col_subnet = st.columns(2)
        router_id = router_options[col_router.selectbox("Chọn Router", list(router_options), key="if_router")]
        subnet_id = subnet_options[col_subnet.selectbox("Chọn Subnet", list(subnet_options), key="if_subnet")]

        col_add, col_remove = st.columns(2)
        if col_add.button("Nối Subnet vào Router", width="stretch", type="primary"):
            res, err = add_router_interface(token, router_id, subnet_id)
            if res:
                st.success("Đã nối Subnet vào Router.")
            else:
                st.error(err)
        if col_remove.button("Gỡ Subnet khỏi Router", width="stretch"):
            res, err = remove_router_interface(token, router_id, subnet_id)
            if res:
                st.success("Đã gỡ Subnet khỏi Router.")
            else:
                st.error(err)
