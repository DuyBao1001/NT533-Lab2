# -*- coding: utf-8 -*-
import json
import streamlit as st
import requests
from config import IDENTITY_URL
from api.auth import get_token
import api.logger as api_logger
from api.compute import get_flavors, list_instances, create_instance, delete_instance, server_action, list_keypairs
from api.image import get_images
from api.network import (
    get_networks, create_network, delete_network,
    get_subnets, create_subnet, delete_subnet,
    list_routers, create_router, delete_router,
    add_router_interface, remove_router_interface
)

st.set_page_config(page_title="OpenStack Lab 2", layout="centered")
st.title("Quản lý OpenStack API")

# Khởi tạo session lưu trữ token
if 'token' not in st.session_state:
    st.session_state['token'] = None

# Nếu chưa có token thì hiển thị form đăng nhập
if st.session_state['token'] is None:
    st.subheader("Đăng nhập hệ thống")

    with st.form("login_form"):
        username = st.text_input("Username (MSSV)")
        password = st.text_input("Mật khẩu", type="password")
        project = st.text_input("Tên Project", value="NT533.R12.G12")
        submit = st.form_submit_button("Kết nối")

        if submit:
            if not username or not password or not project:
                st.warning("Vui lòng nhập đầy đủ thông tin.")
            else:
                token, error = get_token(username, password, project)
                if token:
                    st.session_state['token'] = token
                    st.success("Lấy Token thành công!")
                    st.rerun()
                else:
                    st.error(error)

else:
    st.success("Đã kết nối thành công với hạ tầng OpenStack!")
    st.write(f"**Token hiện tại:** `{st.session_state['token'][:20]}...`")

    if st.button("Đăng xuất"):
        st.session_state['token'] = None
        st.rerun()

    # ================================================================
    # SIDEBAR: HTTP REQUEST LOG
    # ================================================================
    with st.sidebar:
        st.markdown("## Nhật ký HTTP Request")

        col_clear, col_count = st.sidebar.columns([1, 1])
        with col_clear:
            if st.button("Xóa log", type="secondary"):
                api_logger.clear_logs()
                st.rerun()
        with col_count:
            st.caption(f"{len(api_logger.http_logs)} bản ghi")

        # Màu sắc theo method
        METHOD_COLOR = {
            "GET":    "#2196F3",   # xanh dương
            "POST":   "#4CAF50",   # xanh lá
            "PUT":    "#FF9800",   # cam
            "DELETE": "#F44336",   # đỏ
            "PATCH":  "#9C27B0",   # tím
        }

        def status_color(code):
            if code is None:
                return "#9E9E9E"
            if 200 <= code < 300:
                return "#4CAF50"   # xanh lá
            if 400 <= code < 500:
                return "#FF9800"   # cam
            if code >= 500:
                return "#F44336"   # đỏ
            return "#9E9E9E"

        if not api_logger.http_logs:
            st.info("Chưa có request nào được ghi lại.")
        else:
            for i, log in enumerate(api_logger.http_logs):
                m_color = METHOD_COLOR.get(log["method"], "#607D8B")
                s_color = status_color(log["response_status"])
                status_text = str(log["response_status"]) if log["response_status"] else "ERR"
                duration = f'{log["duration_ms"]}ms' if log["duration_ms"] is not None else "?"

                # Dòng tiêu đề của mỗi request
                label = (
                    f":{log['method'].lower()}[**{log['method']}**] "
                    f"`{status_text}` · {duration} · `{log['url'].split('/')[-1] or log['url'].split('/')[-2]}`"
                )

                with st.expander(f"{log['timestamp']}  {log['method']}  {status_text}  {duration}", expanded=(i == 0)):
                    # Badge method
                    st.markdown(
                        f"<span style='background:{m_color};color:white;padding:2px 8px;"
                        f"border-radius:4px;font-weight:bold;font-size:13px'>{log['method']}</span>"
                        f"&nbsp;&nbsp;"
                        f"<span style='background:{s_color};color:white;padding:2px 8px;"
                        f"border-radius:4px;font-weight:bold;font-size:13px'>{status_text}</span>"
                        f"&nbsp;&nbsp;<span style='color:#666;font-size:12px'>{duration}</span>",
                        unsafe_allow_html=True
                    )
                    st.caption(log["url"])

                    # Request body
                    if log["request_body"]:
                        st.markdown("**Request Body:**")
                        st.code(
                            json.dumps(log["request_body"], ensure_ascii=False, indent=2),
                            language="json"
                        )

                    # Response body
                    if log["response_body"]:
                        st.markdown("**Response Body:**")
                        st.code(log["response_body"], language="json")

                    # Lỗi kết nối
                    if log["error"]:
                        st.error(f"Lỗi kết nối: {log['error']}")

    # ================================================================
    # NỘI DUNG CHÍNH
    # ================================================================
    with st.expander("Kiểm tra Service Endpoints (Catalog)"):
        if st.button("Lấy Endpoints từ OpenStack"):
            res = requests.get(f"{IDENTITY_URL}/auth/catalog", headers={"X-Auth-Token": st.session_state['token']})
            if res.status_code == 200:
                catalog = res.json().get("catalog", [])
                for svc in catalog:
                    st.markdown(f"**{svc.get('name')}** (`{svc.get('type')}`)")
                    for ep in svc.get("endpoints", []):
                        st.write(f"- `{ep.get('interface')}`: {ep.get('url')}")
            else:
                st.error(f"Lỗi: {res.status_code} - {res.text}")

    st.divider()

    # ================================================================
    # PHẦN 1: FLAVOR & IMAGE
    # ================================================================
    st.subheader("1. Danh sách Flavor & Image")
    tab_flavor, tab_image = st.tabs(["Flavor", "Image"])

    with tab_flavor:
        col_btn_f, _ = st.columns([1, 4])
        with col_btn_f:
            if st.button("Làm mới Flavor", type="secondary"):
                st.session_state['flavors'] = None

        if 'flavors' not in st.session_state or st.session_state['flavors'] is None:
            flavors, err = get_flavors(st.session_state['token'])
            if flavors is not None:
                st.session_state['flavors'] = flavors
            else:
                st.error(err)

        if st.session_state.get('flavors'):
            st.caption(f"Tổng số: {len(st.session_state['flavors'])} Flavor")
            flavor_data = [
                {
                    "ID": f["id"],
                    "Tên Flavor": f.get("name", "N/A"),
                    "vCPU": f.get("vcpus", 0),
                    "RAM (MB)": f.get("ram", 0),
                    "Disk (GB)": f.get("disk", 0),
                    "Ephemeral (GB)": f.get("OS-FLV-EXT-DATA:ephemeral", 0)
                } for f in st.session_state['flavors']
            ]
            st.dataframe(flavor_data, use_container_width=True)

    with tab_image:
        col_btn_i, _ = st.columns([1, 4])
        with col_btn_i:
            if st.button("Làm mới Image", type="secondary"):
                st.session_state['images'] = None

        if 'images' not in st.session_state or st.session_state['images'] is None:
            images, err = get_images(st.session_state['token'])
            if images is not None:
                st.session_state['images'] = images
            else:
                st.error(err)

        if st.session_state.get('images'):
            st.caption(f"Tổng số: {len(st.session_state['images'])} Image")
            image_data = [
                {
                    "ID": img["id"],
                    "Tên Image": img.get("name", "N/A"),
                    "Trạng thái": img.get("status", "N/A"),
                    "Định dạng": img.get("disk_format", "N/A"),
                    "Min Disk (GB)": img.get("min_disk", img.get("minDisk", 0)),
                    "Min RAM (MB)": img.get("min_ram", img.get("minRam", 0))
                } for img in st.session_state['images']
            ]
            st.dataframe(image_data, use_container_width=True)

    st.divider()

    # ================================================================
    # PHẦN 2: NETWORK & SUBNET
    # ================================================================
    st.subheader("2. Quản lý Network & Subnet")
    tab_net, tab_sub = st.tabs(["Network", "Subnet"])

    with tab_net:
        col_list_net, col_action_net = st.columns([3, 2])

        with col_list_net:
            st.markdown("##### Danh sách Network")
            if st.button("Làm mới Network", type="secondary"):
                st.session_state['networks'] = None

            if 'networks' not in st.session_state or st.session_state['networks'] is None:
                nets, err = get_networks(st.session_state['token'])
                if nets is not None:
                    st.session_state['networks'] = nets
                else:
                    st.error(err)

            if st.session_state.get('networks'):
                net_data = [
                    {
                        "ID": n["id"],
                        "Tên Network": n.get("name", "N/A"),
                        "Trạng thái": n.get("status", "N/A"),
                        "Số Subnet": len(n.get("subnets", []))
                    } for n in st.session_state['networks']
                ]
                st.dataframe(net_data, use_container_width=True)

        with col_action_net:
            st.markdown("##### Tạo Network mới")
            with st.form("create_net_form"):
                new_net_name = st.text_input("Tên Network", placeholder="Ví dụ: nhom12_net")
                submit_create_net = st.form_submit_button("Tạo Network", type="primary")
                if submit_create_net:
                    if not new_net_name:
                        st.warning("Vui lòng nhập tên Network.")
                    else:
                        net, err = create_network(st.session_state['token'], new_net_name)
                        if net:
                            st.success(f"Tạo thành công: {net.get('name')}")
                            st.session_state['networks'] = None
                            st.rerun()
                        else:
                            st.error(err)

            st.markdown("##### Xóa Network")
            if st.session_state.get('networks'):
                net_options = {
                    f"{n.get('name')} ({n['id'][:8]}...)": n['id']
                    for n in st.session_state['networks']
                }
                selected_net_to_delete = st.selectbox("Chọn Network cần xóa", list(net_options.keys()), key="del_net_sel")
                if st.button("Xóa Network đã chọn", type="primary"):
                    net_id = net_options[selected_net_to_delete]
                    success, err = delete_network(st.session_state['token'], net_id)
                    if success:
                        st.success("Xóa Network thành công!")
                        st.session_state['networks'] = None
                        st.rerun()
                    else:
                        st.error(err)

    with tab_sub:
        col_list_sub, col_action_sub = st.columns([3, 2])

        with col_list_sub:
            st.markdown("##### Danh sách Subnet")
            if st.button("Làm mới Subnet", type="secondary"):
                st.session_state['subnets'] = None

            if 'subnets' not in st.session_state or st.session_state['subnets'] is None:
                subs, err = get_subnets(st.session_state['token'])
                if subs is not None:
                    st.session_state['subnets'] = subs
                else:
                    st.error(err)

            if st.session_state.get('subnets'):
                sub_data = [
                    {
                        "ID": s["id"],
                        "Tên Subnet": s.get("name", "N/A"),
                        "Network ID": s.get("network_id", "N/A")[:8] + "...",
                        "CIDR": s.get("cidr", "N/A"),
                        "Gateway": s.get("gateway_ip", "N/A")
                    } for s in st.session_state['subnets']
                ]
                st.dataframe(sub_data, use_container_width=True)

        with col_action_sub:
            st.markdown("##### Tạo Subnet mới")
            with st.form("create_sub_form"):
                if st.session_state.get('networks'):
                    net_choices = {
                        f"{n.get('name')} ({n['id'][:8]}...)": n['id']
                        for n in st.session_state['networks']
                    }
                    selected_parent_net = st.selectbox("Thuộc Network", list(net_choices.keys()))
                    parent_net_id = net_choices[selected_parent_net]
                else:
                    parent_net_id = st.text_input("Network ID", placeholder="Nhập ID của Network")

                new_sub_name = st.text_input("Tên Subnet", placeholder="Ví dụ: nhom12_subnet")
                new_cidr = st.text_input("Dải mạng (CIDR)", placeholder="Ví dụ: 192.168.12.0/24")
                new_gateway = st.text_input("Gateway IP (Không bắt buộc)", placeholder="Ví dụ: 192.168.12.1")
                submit_create_sub = st.form_submit_button("Tạo Subnet", type="primary")

                if submit_create_sub:
                    if not new_sub_name or not new_cidr or not parent_net_id:
                        st.warning("Vui lòng nhập đủ Tên Subnet, CIDR và Network.")
                    else:
                        sub, err = create_subnet(
                            st.session_state['token'],
                            network_id=parent_net_id,
                            name=new_sub_name,
                            cidr=new_cidr,
                            gateway_ip=new_gateway
                        )
                        if sub:
                            st.success(f"Tạo thành công Subnet: {sub.get('name')}")
                            st.session_state['subnets'] = None
                            st.session_state['networks'] = None
                            st.rerun()
                        else:
                            st.error(err)

            st.markdown("##### Xóa Subnet")
            if st.session_state.get('subnets'):
                sub_options = {
                    f"{s.get('name')} ({s.get('cidr')})": s['id']
                    for s in st.session_state['subnets']
                }
                selected_sub_to_delete = st.selectbox("Chọn Subnet cần xóa", list(sub_options.keys()), key="del_sub_sel")
                if st.button("Xóa Subnet đã chọn", type="primary"):
                    sub_id = sub_options[selected_sub_to_delete]
                    success, err = delete_subnet(st.session_state['token'], sub_id)
                    if success:
                        st.success("Xóa Subnet thành công!")
                        st.session_state['subnets'] = None
                        st.session_state['networks'] = None
                        st.rerun()
                    else:
                        st.error(err)

    st.divider()

    # ================================================================
    # PHẦN 3: ROUTER
    # ================================================================
    st.subheader("3. Quản lý Router")
    tab_router_main, tab_router_interface = st.tabs([
        "Danh sách & Quản lý Router",
        "Cấu hình Interface (Nối Subnet)"
    ])

    with tab_router_main:
        col_list_router, col_action_router = st.columns([3, 2])

        with col_list_router:
            st.markdown("##### Danh sách Router")
            if st.button("Làm mới Router", type="secondary"):
                st.session_state['routers'] = None

            if 'routers' not in st.session_state or st.session_state['routers'] is None:
                routers, err = list_routers(st.session_state['token'])
                if routers is not None:
                    st.session_state['routers'] = routers
                else:
                    st.error(err)

            if st.session_state.get('routers'):
                router_data = []
                for r in st.session_state['routers']:
                    ext_info = r.get("external_gateway_info")
                    ext_ip = "Chưa gắn"
                    if ext_info and ext_info.get("external_fixed_ips"):
                        ext_ip = ext_info["external_fixed_ips"][0].get("ip_address", "Có gateway")
                    router_data.append({
                        "ID": r["id"][:8] + "...",
                        "Tên Router": r.get("name", "N/A"),
                        "Trạng thái": r.get("status", "N/A"),
                        "Gateway IP": ext_ip,
                        "Admin State": "UP" if r.get("admin_state_up") else "DOWN"
                    })
                st.dataframe(router_data, use_container_width=True)

        with col_action_router:
            st.markdown("##### Tạo Router mới")
            with st.form("create_router_form"):
                new_router_name = st.text_input("Tên Router", placeholder="Ví dụ: nhom12_router")

                ext_net_id = None
                if st.session_state.get('networks'):
                    ext_options = {"-- Không gắn Gateway ngoài --": None}
                    for n in st.session_state['networks']:
                        ext_options[f"{n.get('name')} ({n['id'][:8]}...)"] = n['id']
                    selected_ext = st.selectbox("External Gateway Network", list(ext_options.keys()))
                    ext_net_id = ext_options[selected_ext]
                else:
                    ext_net_id_input = st.text_input("External Network ID (Không bắt buộc)", placeholder="ID của Public_Net")
                    ext_net_id = ext_net_id_input if ext_net_id_input.strip() else None

                submit_create_router = st.form_submit_button("Tạo Router", type="primary")
                if submit_create_router:
                    if not new_router_name:
                        st.warning("Vui lòng nhập tên Router.")
                    else:
                        router, err = create_router(
                            st.session_state['token'],
                            name=new_router_name,
                            external_network_id=ext_net_id
                        )
                        if router:
                            st.success(f"Tạo thành công Router: {router.get('name')}")
                            st.session_state['routers'] = None
                            st.rerun()
                        else:
                            st.error(err)

            st.markdown("##### Xóa Router")
            if st.session_state.get('routers'):
                router_options = {
                    f"{r.get('name')} ({r['id'][:8]}...)": r['id']
                    for r in st.session_state['routers']
                }
                selected_router_to_delete = st.selectbox(
                    "Chọn Router cần xóa",
                    list(router_options.keys()),
                    key="del_router_sel"
                )
                if st.button("Xóa Router đã chọn", type="primary"):
                    router_id = router_options[selected_router_to_delete]
                    success, err = delete_router(st.session_state['token'], router_id)
                    if success:
                        st.success("Xóa Router thành công!")
                        st.session_state['routers'] = None
                        st.rerun()
                    else:
                        st.error(err)

    with tab_router_interface:
        st.info("Gắn Subnet vào Router để các máy ảo trong Subnet đó có thể truy cập mạng ngoài qua Gateway.")

        if st.session_state.get('routers') and st.session_state.get('subnets'):
            r_choices = {
                f"{r.get('name')} ({r['id'][:8]}...)": r['id']
                for r in st.session_state['routers']
            }
            s_choices = {
                f"{s.get('name')} — {s.get('cidr')}": s['id']
                for s in st.session_state['subnets']
            }

            col_if1, col_if2 = st.columns(2)
            with col_if1:
                target_router = st.selectbox("Chọn Router", list(r_choices.keys()), key="if_r_sel")
                target_router_id = r_choices[target_router]
            with col_if2:
                target_subnet = st.selectbox("Chọn Subnet", list(s_choices.keys()), key="if_s_sel")
                target_subnet_id = s_choices[target_subnet]

            col_btn_add, col_btn_rem = st.columns(2)
            with col_btn_add:
                if st.button("Nối Subnet vào Router", use_container_width=True, type="primary"):
                    res, err = add_router_interface(st.session_state['token'], target_router_id, target_subnet_id)
                    if res:
                        st.success("Đã nối Subnet vào Router thành công!")
                    else:
                        st.error(err)
            with col_btn_rem:
                if st.button("Gỡ Subnet khỏi Router", use_container_width=True):
                    res, err = remove_router_interface(st.session_state['token'], target_router_id, target_subnet_id)
                    if res:
                        st.success("Đã gỡ Subnet khỏi Router thành công!")
                    else:
                        st.error(err)
        else:
            st.warning("Bạn cần có ít nhất 1 Router và 1 Subnet. Hãy tải lại dữ liệu ở các mục trên.")

    st.divider()

    # ================================================================
    # PHẦN 4: INSTANCE (MÁY ẢO)
    # ================================================================
    st.subheader("4. Quản lý Instance (Máy ảo)")
    tab_inst_list, tab_inst_create = st.tabs(["Danh sách Instance", "Tạo Instance mới"])

    with tab_inst_list:
        if st.button("Làm mới danh sách Instance", type="secondary"):
            st.session_state['instances'] = None

        if 'instances' not in st.session_state or st.session_state['instances'] is None:
            instances, err = list_instances(st.session_state['token'])
            if instances is not None:
                st.session_state['instances'] = instances
            else:
                st.error(err)

        if st.session_state.get('instances'):
            st.caption(f"Tổng số: {len(st.session_state['instances'])} Instance")
            inst_data = []
            for s in st.session_state['instances']:
                addrs = s.get("addresses", {})
                ip_list = []
                for net_addrs in addrs.values():
                    for addr in net_addrs:
                        ip_list.append(addr.get("addr", ""))
                ip_str = ", ".join(ip_list) if ip_list else "N/A"
                inst_data.append({
                    "ID": s["id"][:8] + "...",
                    "Tên": s.get("name", "N/A"),
                    "Trạng thái": s.get("status", "N/A"),
                    "Địa chỉ IP": ip_str,
                    "Flavor": s.get("flavor", {}).get("original_name", s.get("flavor", {}).get("id", "N/A")),
                    "Image": s.get("image", {}).get("id", "N/A")[:8] + "..." if s.get("image") else "Volume"
                })
            st.dataframe(inst_data, use_container_width=True)

            st.markdown("##### Thao tác nhanh")
            inst_options = {
                f"{s.get('name')} [{s.get('status')}]": s['id']
                for s in st.session_state['instances']
            }
            selected_inst = st.selectbox("Chọn Instance", list(inst_options.keys()), key="inst_action_sel")
            selected_inst_id = inst_options[selected_inst]

            col_start, col_stop, col_reboot, col_del = st.columns(4)
            with col_start:
                if st.button("Bật", use_container_width=True, type="primary"):
                    ok, err = server_action(st.session_state['token'], selected_inst_id, "start")
                    if ok:
                        st.success("Đã gửi lệnh Bật!")
                        st.session_state['instances'] = None
                        st.rerun()
                    else:
                        st.error(err)
            with col_stop:
                if st.button("Tắt", use_container_width=True):
                    ok, err = server_action(st.session_state['token'], selected_inst_id, "stop")
                    if ok:
                        st.success("Đã gửi lệnh Tắt!")
                        st.session_state['instances'] = None
                        st.rerun()
                    else:
                        st.error(err)
            with col_reboot:
                if st.button("Khởi động lại", use_container_width=True):
                    ok, err = server_action(st.session_state['token'], selected_inst_id, "reboot")
                    if ok:
                        st.success("Đã gửi lệnh Reboot!")
                    else:
                        st.error(err)
            with col_del:
                if st.button("Xóa", use_container_width=True):
                    ok, err = delete_instance(st.session_state['token'], selected_inst_id)
                    if ok:
                        st.success("Đã xóa Instance!")
                        st.session_state['instances'] = None
                        st.rerun()
                    else:
                        st.error(err)
        elif st.session_state.get('instances') is not None:
            st.info("Chưa có Instance nào. Hãy tạo mới ở tab bên cạnh.")

    with tab_inst_create:
        with st.form("create_instance_form"):
            inst_name = st.text_input("Tên Instance", placeholder="Ví dụ: nhom12_vm1")

            if st.session_state.get('images'):
                img_choices = {
                    f"{img.get('name', 'N/A')} (ID: {img['id'][:8]}...)": img['id']
                    for img in st.session_state['images']
                }
                selected_img = st.selectbox("Chọn Image", list(img_choices.keys()))
                image_id_input = img_choices[selected_img]
            else:
                image_id_input = st.text_input("Image ID", placeholder="Nhập ID của Image")

            if st.session_state.get('flavors'):
                flav_choices = {
                    f"{f.get('name')} (vCPU: {f['vcpus']}, RAM: {f['ram']}MB, Disk: {f['disk']}GB)": f['id']
                    for f in st.session_state['flavors']
                }
                selected_flav = st.selectbox("Chọn Flavor", list(flav_choices.keys()))
                flavor_id_input = flav_choices[selected_flav]
            else:
                flavor_id_input = st.text_input("Flavor ID", placeholder="Nhập ID của Flavor")

            if st.session_state.get('networks'):
                net_choices_inst = {
                    f"{n.get('name')} ({n['id'][:8]}...)": n['id']
                    for n in st.session_state['networks']
                }
                selected_net_inst = st.selectbox("Chọn Network", list(net_choices_inst.keys()))
                network_id_input = net_choices_inst[selected_net_inst]
            else:
                network_id_input = st.text_input("Network ID", placeholder="Nhập ID của Network")

            keypairs, _ = list_keypairs(st.session_state['token'])
            kp_options = ["-- Không dùng Key Pair --"] + [kp.get("name", "") for kp in keypairs]
            selected_kp = st.selectbox("Key Pair (Không bắt buộc)", kp_options)
            key_name = selected_kp if selected_kp != "-- Không dùng Key Pair --" else None

            sg_input = st.text_input("Security Group", value="default", placeholder="Ví dụ: default")
            security_groups = [sg_input.strip()] if sg_input.strip() else None

            with st.expander("User Data Script (Tùy chọn — chạy khi máy ảo khởi động)"):
                default_script = """#!/bin/bash
apt-get update -y
apt-get install -y nginx
echo "<h1>Hello from NT533.R12.G12 - OpenStack Lab 2</h1>" > /var/www/html/index.html
systemctl restart nginx"""
                user_data_script = st.text_area("Bash Script", value=default_script, height=150)

            submit_create_inst = st.form_submit_button("Khởi tạo Instance", type="primary")

            if submit_create_inst:
                if not inst_name or not image_id_input or not flavor_id_input or not network_id_input:
                    st.warning("Vui lòng nhập đủ Tên, Image, Flavor và Network.")
                else:
                    server, err = create_instance(
                        token=st.session_state['token'],
                        name=inst_name,
                        image_id=image_id_input,
                        flavor_id=flavor_id_input,
                        network_id=network_id_input,
                        user_data=user_data_script,
                        key_name=key_name,
                        security_groups=security_groups
                    )
                    if server:
                        st.success(f"Đang khởi tạo Instance: **{server.get('name')}** (ID: `{server.get('id')}`)")
                        st.info("Trạng thái ban đầu là BUILD, vui lòng đợi vài giây rồi làm mới danh sách để xem ACTIVE.")
                        st.session_state['instances'] = None
                    else:
                        st.error(err)
