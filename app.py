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
    add_router_interface, remove_router_interface,
    get_instance_ports,
    list_floating_ips,
    create_floating_ip
)

from api.load_balancer import (
    list_load_balancers,
    create_load_balancer,
    get_load_balancer,
    list_listeners,
    create_listener,
    list_pools,
    create_pool,
    list_members,
    add_pool_member,
    list_health_monitors,
    create_health_monitor,
)


st.set_page_config(page_title="OpenStack Lab 2", layout="centered")
st.title("Quản lý OpenStack API")

if 'token' not in st.session_state:
    st.session_state['token'] = None

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
                submit_create_net = st.form_submit_button("Tạo Network", type="secondary")
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
                submit_create_sub = st.form_submit_button("Tạo Subnet", type="secondary")

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

                submit_create_router = st.form_submit_button("Tạo Router", type="secondary")
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
                if st.button("Bật", use_container_width=True, type="secondary"):
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
                if st.button("Xóa", use_container_width=True, type="primary"):
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
set -eux
exec > /var/log/nt533-user-data.log 2>&1
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nginx curl
VM_IP=$(curl -fsS --max-time 5 \
  http://169.254.169.254/openstack/latest/meta_data.json \
  | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(",".join(
    a["addr"]
    for values in d.get("meta", {}).get("network", {}).values()
    for a in values
    if a.get("version") == 4
))
' 2>/dev/null || true)
if [ -z "$VM_IP" ]; then
    VM_IP=$(hostname -I | awk '{print $1}')
fi

cat > /var/www/html/index.html <<EOF
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NT533 OpenStack Lab 2</title>
</head>
<body>
  <h1>NT533 - OpenStack Lab 2</h1>
  <h2>Nhóm: NT533.R12.G12</h2>
  <p>Máy ảo đã được khởi tạo thành công.</p>
  <p>Địa chỉ IP nội bộ: ${VM_IP}</p>
</body>
</html>
EOF

systemctl enable nginx
systemctl restart nginx"""
                user_data_script = st.text_area("Bash Script", value=default_script, height=150)

            submit_create_inst = st.form_submit_button("Khởi tạo Instance", type="secondary")

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


    # --- GAN FLOATING IP ---
    st.divider()
    st.subheader("5. Gắn Floating IP")
    token = st.session_state["token"]
    current_instances = st.session_state.get("instances") or []

    if current_instances:
        vm_options = {
            f"{vm.get('name', 'VM')} [{vm.get('status', '')}]": vm["id"]
            for vm in current_instances
        }

        selected_vm_label = st.selectbox(
            "Chọn máy ảo cần gắn Floating IP",
            list(vm_options.keys()),
            key="floating_vm"
        )

        external_network_id = st.text_input(
            "External Network ID",
            placeholder="Nhập ID của mạng ngoài"
        )

        if st.button("Lấy danh sách Floating IP", key="load_fips"):
            fips, err = list_floating_ips(st.session_state["token"])

            if fips is not None:
                st.session_state["floating_ips"] = fips
                st.dataframe([
                    {
                        "Floating IP": fip.get("floating_ip_address"),
                        "Port ID": fip.get("port_id"),
                        "Trạng thái": fip.get("status")
                    }
                    for fip in fips
                ], use_container_width=True)
            else:
                st.error(err)

        if st.button("Gắn Floating IP mới", key="attach_fip"):
            if not external_network_id.strip():
                st.warning("Vui lòng nhập External Network ID.")
            else:
                vm_id = vm_options[selected_vm_label]

                ports, err = get_instance_ports(
                    st.session_state["token"], vm_id
                )

                if ports is None:
                    st.error(err)
                elif not ports:
                    st.error(
                        "VM chưa có port mạng. Hãy kiểm tra Network "
                        "và trạng thái Instance."
                    )
                else:
                    # Chon port co dia chi IP noi bo
                    port = next(
                        (
                            p for p in ports
                            if p.get("fixed_ips")
                        ),
                        None
                    )

                    if not port:
                        st.error("Không tìm thấy port có Fixed IP.")
                    else:
                        fip, err = create_floating_ip(
                            st.session_state["token"],
                            external_network_id.strip(),
                            port["id"]
                        )

                        if fip:
                            st.success("Đã gắn Floating IP!")
                            st.code(
                                f"http://{fip.get('floating_ip_address')}"
                            )
                            st.caption(
                                "Nếu chưa truy cập được, kiểm tra "
                                "Security Group, routing và trạng thái Nginx."
                            )
                        else:
                            st.error(err)
    else:
        st.info(
            "Hãy tải danh sách Instance trước khi gắn Floating IP."
        )
    
    # ================================================================
    # PHẦN 6: LOAD BALANCER
    # Lưu ý: Toàn bộ phần này nằm bên trong else đăng nhập thành công
    # ================================================================

    st.divider()
    st.subheader("6. Cấu hình Load Balancer")

    token = st.session_state["token"]

    # ------------------------------------------------
    # 6.1. Tạo và chọn Load Balancer
    # ------------------------------------------------

    st.markdown("#### 6.1. Tạo và chọn Load Balancer")

    with st.expander("Tạo Load Balancer mới", expanded=False):
        subnets, subnet_err = get_subnets(token)

        if subnets is None or subnet_err:
            st.error(subnet_err or "Không tải được danh sách Subnet.")
        else:
            subnet_options = {
                f"{s.get('name') or '(Không tên)'} | {s.get('cidr', '')} | {s.get('id')}": s["id"]
                for s in subnets
                if s.get("id")
            }

            if not subnet_options:
                st.warning("Chưa có Subnet để tạo Load Balancer.")
            else:
                with st.form("lb_create_form"):
                    new_lb_name = st.text_input(
                        "Tên Load Balancer",
                        value="lb-demo",
                    )
                    selected_subnet_label = st.selectbox(
                        "Subnet chứa VIP",
                        list(subnet_options.keys()),
                    )
                    create_lb_submit = st.form_submit_button(
                        "Tạo Load Balancer",
                        use_container_width=True,
                    )

                if create_lb_submit:
                    if not new_lb_name.strip():
                        st.warning("Vui lòng nhập tên Load Balancer.")
                    else:
                        with st.spinner("Đang tạo Load Balancer..."):
                            new_lb, err = create_load_balancer(
                                token,
                                new_lb_name.strip(),
                                subnet_options[selected_subnet_label],
                            )

                        if new_lb:
                            st.success("Đã gửi yêu cầu tạo Load Balancer.")
                            st.json(new_lb)
                            lbs, refresh_err = list_load_balancers(token)

                            if lbs is not None and not refresh_err:
                                st.session_state["lb_items"] = lbs

                            if new_lb.get("id"):
                                st.session_state["lb_selected_id"] = new_lb["id"]
                        else:
                            st.error(err or "Không tạo được Load Balancer.")

    lb_refresh_col, lb_status_col = st.columns(2)

    with lb_refresh_col:
        if st.button(
            "🔄 Làm mới danh sách Load Balancer",
            key="lb_refresh",
            use_container_width=True,
        ):
            lbs, err = list_load_balancers(token)
            if lbs is not None and not err:
                st.session_state["lb_items"] = lbs
                st.success("Đã tải danh sách Load Balancer.")
            else:
                st.error(err or "Không tải được danh sách Load Balancer.")

    lb_items = st.session_state.get("lb_items") or []

    if not lb_items:
        st.info("Nhấn 'Làm mới danh sách Load Balancer' để tải dữ liệu.")
        selected_lb_id = None
    else:
        lb_options = {
            (
                f"{lb.get('name') or '(Không tên)'} | "
                f"{lb.get('provisioning_status') or 'Unknown'} | "
                f"{lb.get('id')}"
            ): lb["id"]
            for lb in lb_items
            if lb.get("id")
        }

        if not lb_options:
            st.warning("Không tìm thấy Load Balancer có ID hợp lệ.")
            selected_lb_id = None
        else:
            lb_ids = list(lb_options.values())
            saved_lb_id = st.session_state.get("lb_selected_id")

            default_index = (
                lb_ids.index(saved_lb_id)
                if saved_lb_id in lb_ids
                else 0
            )

            selected_lb_label = st.selectbox(
                "Chọn Load Balancer",
                list(lb_options.keys()),
                index=default_index,
                key="lb_selected",
            )
            selected_lb_id = lb_options[selected_lb_label]
            st.session_state["lb_selected_id"] = selected_lb_id

            with lb_status_col:
                if st.button(
                    "🔎 Kiểm tra trạng thái",
                    key="lb_check",
                    use_container_width=True,
                ):
                    lb, err = get_load_balancer(token, selected_lb_id)
                    if lb:
                        st.json(lb)
                    else:
                        st.error(err or "Không lấy được thông tin Load Balancer.")

    # ------------------------------------------------
    # 6.2–6.6. Chỉ hiển thị khi đã chọn Load Balancer
    # ------------------------------------------------

    if selected_lb_id is None:
        st.info("Chọn một Load Balancer để cấu hình các mục tiếp theo.")

    else:
        # ============================================
        # 6.2. Listener TCP
        # ============================================

        st.divider()
        st.markdown("#### 6.2. Listener TCP")

        with st.expander("Tạo Listener TCP", expanded=False):
            with st.form("lb_create_listener_form"):
                listener_name = st.text_input(
                    "Tên Listener",
                    value="tcp-listener-demo",
                )
                listener_submit = st.form_submit_button(
                    "Tạo Listener TCP",
                    use_container_width=True,
                )

            if listener_submit:
                if not listener_name.strip():
                    st.warning("Vui lòng nhập tên Listener.")
                else:
                    with st.spinner("Đang tạo Listener..."):
                        listener, err = create_listener(
                            token,
                            selected_lb_id,
                            listener_name.strip(),
                        )

                    if listener:
                        st.success("Đã gửi yêu cầu tạo Listener.")
                        st.json(listener)
                        st.session_state.pop("lb_listener_items", None)
                        st.session_state.pop("lb_pool_items", None)
                    else:
                        st.error(err or "Không tạo được Listener.")

        listener_refresh_col, _ = st.columns([1, 3])

        with listener_refresh_col:
            if st.button(
                "🔄 Tải lại Listener",
                key="lb_refresh_listeners",
                use_container_width=True,
            ):
                items, err = list_listeners(token)
                if items is not None and not err:
                    st.session_state["lb_listener_items"] = items
                else:
                    st.error(err or "Không tải được danh sách Listener.")

        if "lb_listener_items" not in st.session_state:
            items, err = list_listeners(token)
            if items is not None and not err:
                st.session_state["lb_listener_items"] = items
            elif err:
                st.error(err)

        all_listeners = st.session_state.get("lb_listener_items", [])

        def listener_belongs_to_lb(listener, lb_id):
            if listener.get("loadbalancer_id") == lb_id:
                return True

            linked_lbs = listener.get("loadbalancers") or []
            return any(
                (x.get("id") if isinstance(x, dict) else x) == lb_id
                for x in linked_lbs
            )

        selected_listeners = [
            listener
            for listener in all_listeners
            if listener_belongs_to_lb(listener, selected_lb_id)
        ]

        if selected_listeners:
            st.dataframe(
                [
                    {
                        "Tên": x.get("name", ""),
                        "ID": x.get("id", ""),
                        "Protocol": x.get("protocol", ""),
                        "Port": x.get("protocol_port", ""),
                        "Trạng thái cấu hình": x.get("provisioning_status", ""),
                        "Trạng thái hoạt động": x.get("operating_status", ""),
                    }
                    for x in selected_listeners
                ],
                use_container_width=True,
                hide_index=True,
            )
        elif all_listeners:
            st.info(
                "API có trả về Listener nhưng chưa xác định được Listener "
                "thuộc Load Balancer này. Hãy kiểm tra dữ liệu Listener bên dưới."
            )
            st.json(all_listeners)
        else:
            st.info("Chưa có Listener hoặc chưa tải được dữ liệu Listener.")

        # ============================================
        # 6.3. Pool
        # ============================================

        st.divider()
        st.markdown("#### 6.3. Pool")

        if selected_listeners:
            listener_options = {
                (
                    f"{x.get('name') or '(Không tên)'} | "
                    f"{x.get('protocol', '')}:{x.get('protocol_port', '')} | "
                    f"{x.get('id')}"
                ): x["id"]
                for x in selected_listeners
                if x.get("id")
            }

            if listener_options:
                with st.expander("Tạo Pool mới", expanded=False):
                    with st.form("lb_create_pool_form"):
                        pool_name = st.text_input(
                            "Tên Pool",
                            value="tcp-pool",
                        )
                        selected_listener_label = st.selectbox(
                            "Listener gắn với Pool",
                            list(listener_options.keys()),
                        )
                        pool_submit = st.form_submit_button(
                            "Tạo Pool",
                            use_container_width=True,
                        )

                    if pool_submit:
                        if not pool_name.strip():
                            st.warning("Vui lòng nhập tên Pool.")
                        else:
                            with st.spinner("Đang tạo Pool..."):
                                pool, err = create_pool(
                                    token,
                                    listener_options[selected_listener_label],
                                    pool_name.strip(),
                                )

                            if pool:
                                st.success("Đã gửi yêu cầu tạo Pool.")
                                st.json(pool)
                                st.session_state.pop("lb_pool_items", None)
                            else:
                                st.error(err or "Không tạo được Pool.")
        else:
            st.info("Cần có Listener thuộc Load Balancer này trước khi tạo Pool.")

        pool_refresh_col, _ = st.columns([1, 3])

        with pool_refresh_col:
            if st.button(
                "🔄 Tải lại Pool",
                key="lb_refresh_pools",
                use_container_width=True,
            ):
                items, err = list_pools(token)
                if items is not None and not err:
                    st.session_state["lb_pool_items"] = items
                else:
                    st.error(err or "Không tải được danh sách Pool.")

        if "lb_pool_items" not in st.session_state:
            items, err = list_pools(token)
            if items is not None and not err:
                st.session_state["lb_pool_items"] = items
            elif err:
                st.error(err)

        all_pools = st.session_state.get("lb_pool_items", [])
        selected_listener_ids = {
            x.get("id") for x in selected_listeners if x.get("id")
        }

        def pool_belongs_to_selected_lb(pool):
            linked_listeners = pool.get("listeners") or []

            if pool.get("listener_id") in selected_listener_ids:
                return True

            return any(
                (
                    x.get("id") if isinstance(x, dict) else x
                ) in selected_listener_ids
                for x in linked_listeners
            )

        selected_pools = [
            pool for pool in all_pools
            if pool_belongs_to_selected_lb(pool)
        ]

        if selected_pools:
            st.dataframe(
                [
                    {
                        "Tên": p.get("name", ""),
                        "ID": p.get("id", ""),
                        "Protocol": p.get("protocol", ""),
                        "Thuật toán": p.get("lb_algorithm", ""),
                        "Trạng thái cấu hình": p.get("provisioning_status", ""),
                    }
                    for p in selected_pools
                ],
                use_container_width=True,
                hide_index=True,
            )
        elif all_pools:
            st.warning(
                "API có trả về Pool nhưng chưa xác định được Pool thuộc "
                "Listener đã chọn. Dữ liệu Pool API trả về:"
            )
            st.json(all_pools)
        else:
            st.info("Chưa có Pool. Hãy tạo Pool từ Listener ở mục 6.3.")

        
        # ============================================
        # 6.4. Backend VM
        # ============================================

        st.divider()
        st.markdown("#### 6.4. Backend VM")
        st.caption("Chọn Pool, Subnet và Fixed IP để thêm Backend VM.")

        if selected_pools:
            # Cho phép chọn Pool cần thêm Backend
            backend_pool_options = {
                f"{p.get('name') or '(Không tên)'} | {p.get('id')}": p["id"]
                for p in selected_pools
                if p.get("id")
            }

            if backend_pool_options:
                backend_pool_label = st.selectbox(
                    "Pool nhận Backend",
                    options=list(backend_pool_options.keys()),
                    key="backend_pool_select",
                )

                backend_pool_id = backend_pool_options[backend_pool_label]

                # Load danh sách Subnet và Port
                
                try:
                    subnet_result = get_subnets(token)

                    # Xử lý trường hợp hàm trả về (data, error)
                    if isinstance(subnet_result, tuple):
                        subnet_items, subnet_err = subnet_result
                        if subnet_err:
                            st.error(f"Lỗi tải Subnet: {subnet_err}")
                    else:
                        subnet_items = subnet_result

                    subnet_items = subnet_items or []

                    # Lấy danh sách Instance
                    instance_result = list_instances(token)

                    if isinstance(instance_result, tuple):
                        instance_items, instance_err = instance_result
                        if instance_err:
                            st.error(f"Lỗi tải Instance: {instance_err}")
                    else:
                        instance_items = instance_result

                    instance_items = instance_items or []

                except Exception as e:
                    subnet_items = []
                    instance_items = []
                    st.error(f"Không tải được dữ liệu: {e}")
                
                # Chuẩn hóa dữ liệu Instance nếu API trả về dict
                if isinstance(instance_items, dict):
                    instance_items = instance_items.get("servers", [])

                instance_options = {
                    f"{vm.get('name') or '(Không tên)'} | {vm.get('id')}": vm["id"]
                    for vm in instance_items
                    if isinstance(vm, dict) and vm.get("id")
                }

                port_items = []

                if instance_options:
                    selected_instance_label = st.selectbox(
                        "Backend VM",
                        options=list(instance_options.keys()),
                        key="backend_instance_select",
                    )

                    selected_instance_id = instance_options[selected_instance_label]

                    port_result = get_instance_ports(
                        token,
                        selected_instance_id,
                    )

                    if isinstance(port_result, tuple):
                        port_items, port_err = port_result
                        if port_err:
                            st.error(f"Lỗi tải Port: {port_err}")
                    else:
                        port_items = port_result

                    if isinstance(port_items, dict):
                        port_items = port_items.get("ports", [])

                    port_items = port_items or []
                else:
                    st.warning("Không tìm thấy Instance hợp lệ để chọn.")


                # Chọn Subnet
                subnet_options = {
                    f"{s.get('name') or '(Không tên)'} | {s.get('id')}": s["id"]
                    for s in subnet_items
                    if s.get("id")
                }

                if subnet_options:
                    selected_subnet_label = st.selectbox(
                        "Subnet của Backend VM",
                        options=list(subnet_options.keys()),
                        key="backend_subnet_select",
                    )
                    selected_subnet_id = subnet_options[selected_subnet_label]
                else:
                    selected_subnet_id = None
                    st.warning("Chưa có Subnet để chọn.")

                # Lọc Fixed IP theo Subnet đã chọn
                fixed_ip_options = {}

                if selected_subnet_id:
                    for port in port_items:
                        for fixed_ip in port.get("fixed_ips", []):
                            if fixed_ip.get("subnet_id") != selected_subnet_id:
                                continue

                            ip_address = fixed_ip.get("ip_address")
                            port_id = port.get("id")

                            if not ip_address or not port_id:
                                continue

                            device_name = (
                                port.get("device_owner")
                                or port.get("name")
                                or port.get("device_id")
                                or "VM/Port"
                            )

                            label = (
                                f"{ip_address} | {device_name} "
                                f"| Port: {port_id[:8]}"
                            )

                            fixed_ip_options[label] = ip_address

                if fixed_ip_options:
                    selected_ip_label = st.selectbox(
                        "Fixed IP của Backend VM",
                        options=list(fixed_ip_options.keys()),
                        key="backend_fixed_ip_select",
                    )
                    selected_backend_ip = fixed_ip_options[selected_ip_label]
                else:
                    selected_backend_ip = None
                    if selected_subnet_id:
                        st.warning(
                            "Không tìm thấy Fixed IP thuộc Subnet này. "
                            "Kiểm tra VM đã có Port và Fixed IP chưa."
                        )

                backend_port = st.number_input(
                    "Port ứng dụng",
                    min_value=1,
                    max_value=65535,
                    value=80,
                    step=1,
                    key="backend_port_number",
                )

                if st.button(
                    "Thêm Backend",
                    key="add_backend_button",
                    disabled=(
                        not selected_subnet_id
                        or not selected_backend_ip
                    ),
                    use_container_width=True,
                ):
                    with st.spinner("Đang thêm Backend..."):
                        result = add_pool_member(
                            token,
                            backend_pool_id,
                            selected_backend_ip,
                            selected_subnet_id,
                            int(backend_port),
                        )

                    if isinstance(result, tuple):
                        # Hỗ trợ trường hợp hàm trả về (data, error)
                        member, err = result
                        if member and not err:
                            st.success("Đã gửi yêu cầu thêm Backend.")
                            st.json(member)
                        else:
                            st.error(err or "Không thêm được Backend.")
                    elif result:
                        st.success("Đã gửi yêu cầu thêm Backend.")
                        st.json(result)
                    else:
                        st.error("Không thêm được Backend.")

                st.markdown("**Danh sách Backend trong Pool**")

                if st.button(
                    "🔄 Tải lại Backend",
                    key="refresh_backend_button",
                ):
                    st.session_state["refresh_backend_list"] = True

                try:
                    backend_items = list_members(token, backend_pool_id)

                    # Hỗ trợ hàm trả về (data, error)
                    if isinstance(backend_items, tuple):
                        members, err = backend_items
                        if err:
                            st.error(err)
                            members = []
                    else:
                        members = backend_items or []

                    if members:
                        st.dataframe(
                            members,
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.info("Pool hiện chưa có Backend.")

                except Exception as e:
                    st.error(f"Không tải được danh sách Backend: {e}")
            else:
                st.warning("Không tìm thấy Pool hợp lệ để chọn.")
        else:
            st.info("Chưa có Pool thuộc Load Balancer đang chọn. Hãy tạo Pool ở mục 6.3.")

        # ============================================
        # 6.5. Health Monitor
        # ============================================

        st.divider()
        st.markdown("#### 6.5. Health Monitor")
        st.caption("Health Monitor kiểm tra trạng thái hoạt động của backend.")

        if selected_pools:
            hm_pool_options = {
                f"{p.get('name') or '(Không tên)'} | {p.get('id')}": p["id"]
                for p in selected_pools
                if p.get("id")
            }

            hm_pool_label = st.selectbox(
                "Pool cần giám sát",
                list(hm_pool_options.keys()),
                key="lb_hm_pool",
            )
            hm_pool_id = hm_pool_options[hm_pool_label]

            if st.button(
                "Tạo Health Monitor TCP",
                key="lb_create_hm",
                use_container_width=True,
            ):
                with st.spinner("Đang tạo Health Monitor..."):
                    hm, err = create_health_monitor(token, hm_pool_id)

                if hm:
                    st.success("Đã gửi yêu cầu tạo Health Monitor.")
                    st.json(hm)
                else:
                    st.error(err or "Không tạo được Health Monitor.")
        else:
            st.info("Chưa có Pool thuộc Load Balancer đang chọn.")

        
        if st.button(
            "Xem danh sách Health Monitor",
            key="lb_list_hm",
            use_container_width=True,
        ):
            result = list_health_monitors(token)

            # Xử lý kết quả API
            if isinstance(result, tuple):
                monitors, err = result
            else:
                monitors, err = result, None

            if err:
                st.error(f"Lỗi tải Health Monitor: {err}")
            else:
                # Chuẩn hóa dữ liệu trả về
                if isinstance(monitors, dict):
                    monitors = monitors.get("healthmonitors", [])

                monitors = monitors or []

                st.write(f"Tổng số Health Monitor từ API: {len(monitors)}")

                # Hiển thị dữ liệu gốc để kiểm tra
                with st.expander("🔍 Xem dữ liệu Health Monitor từ API"):
                    st.json(monitors)

                selected_pool_ids = {
                    p.get("id")
                    for p in selected_pools
                    if p.get("id")
                }

                
                relevant_monitors = []

                for hm in monitors:
                    if not isinstance(hm, dict):
                        continue

                    # Một số API trả về pool_id trực tiếp
                    if hm.get("pool_id") in selected_pool_ids:
                        relevant_monitors.append(hm)
                        continue

                    # API của bạn trả về danh sách pools
                    hm_pool_ids = {
                        p.get("id")
                        for p in (hm.get("pools") or [])
                        if isinstance(p, dict) and p.get("id")
                    }

                    if hm_pool_ids & selected_pool_ids:
                        relevant_monitors.append(hm)


                if relevant_monitors:
                    st.success(
                        f"Tìm thấy {len(relevant_monitors)} Health Monitor "
                        "thuộc Pool đang chọn."
                    )

                    st.dataframe(
                        [
                            {
                                "Tên": hm.get("name", ""),
                                "ID": hm.get("id", ""),
                                "Pool ID": hm.get("pool_id", ""),
                                "Loại": hm.get("type", ""),
                                "Delay": hm.get("delay", ""),
                                "Timeout": hm.get("timeout", ""),
                                "Trạng thái": hm.get(
                                    "provisioning_status", ""
                                ),
                                "Hoạt động": hm.get(
                                    "operating_status", ""
                                ),
                            }
                            for hm in relevant_monitors
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                elif monitors:
                    st.warning(
                        "API có trả về Health Monitor nhưng không tìm thấy "
                        "HM thuộc Pool đang chọn. Mở phần dữ liệu gốc ở trên "
                        "để kiểm tra pool_id."
                    )
                    st.write("Pool ID đang chọn:")
                    st.code("\n".join(selected_pool_ids))
                else:
                    st.info(
                        "API không trả về Health Monitor nào. "
                        "Hãy kiểm tra kết quả tạo HM và thử tải lại."
                    )


       
        # ============================================
        # 6.6. Floating IP cho VIP
        # ============================================

        st.divider()
        st.markdown("#### 6.6. Floating IP cho VIP")
        st.caption(
            "Chọn External Network, sau đó kiểm tra hoặc gắn "
            "Floating IP vào VIP của Load Balancer."
        )

        vip_lb, vip_err = get_load_balancer(token, selected_lb_id)

        if not vip_lb:
            st.error(vip_err or "Không lấy được thông tin Load Balancer.")
        else:
            vip_port_id = vip_lb.get("vip_port_id")
            vip_address = vip_lb.get("vip_address")

            vip_col1, vip_col2 = st.columns(2)
            vip_col1.metric(
                "VIP Address",
                str(vip_address or "Chưa có"),
            )
            vip_col2.metric(
                "Provisioning",
                str(vip_lb.get("provisioning_status") or "Unknown"),
            )

            st.caption(f"VIP Port ID: {vip_port_id or 'Chưa có'}")

            # Tải danh sách Network từ OpenStack
            networks, network_err = get_networks(token)

            external_networks = []

            if networks is None or network_err:
                st.error(
                    network_err or "Không tải được danh sách Network."
                )
            else:
                external_networks = [
                    net for net in networks
                    if isinstance(net, dict)
                    and net.get("id")
                    and net.get("router:external") is True
                ]

            if not external_networks:
                st.warning(
                    "Không tìm thấy External Network trong danh sách API. "
                    "Hãy kiểm tra quyền truy cập hoặc cấu hình mạng "
                    "trên NC-Cloud."
                )
            else:
                # Tạo lựa chọn hiển thị tên mạng và UUID
                external_network_options = {
                    (
                        f"{net.get('name') or '(Không tên)'}"
                        f" | {net['id']}"
                    ): net["id"]
                    for net in external_networks
                }

                selected_external_label = st.selectbox(
                    "External Network",
                    options=list(external_network_options.keys()),
                    key="lb_external_network_select",
                )

                external_network_id = external_network_options[
                    selected_external_label
                ]

                st.caption(
                    f"External Network ID: {external_network_id}"
                )

                fip_col1, fip_col2 = st.columns(2)

                with fip_col1:
                    check_fip_clicked = st.button(
                        "🔎 Kiểm tra Floating IP",
                        key="lb_check_vip_fip",
                        use_container_width=True,
                    )

                with fip_col2:
                    attach_fip_clicked = st.button(
                        "🔗 Gắn Floating IP vào VIP",
                        key="lb_attach_vip_fip",
                        use_container_width=True,
                    )

                if check_fip_clicked:
                    if not vip_port_id:
                        st.error("Load Balancer chưa có VIP Port.")
                    else:
                        fips, err = list_floating_ips(token)

                        if fips is None or err:
                            st.error(
                                err or "Không tải được danh sách Floating IP."
                            )
                        else:
                            attached_fips = [
                                f for f in fips
                                if isinstance(f, dict)
                                and f.get("port_id") == vip_port_id
                            ]

                            if attached_fips:
                                for fip in attached_fips:
                                    address = fip.get("floating_ip_address")
                                    st.success(
                                        "Floating IP: "
                                        f"{address or 'Không rõ địa chỉ'}"
                                    )
                                    if address:
                                        st.code(f"http://{address}")
                            else:
                                st.info(
                                    "VIP hiện chưa được gắn Floating IP."
                                )

                if attach_fip_clicked:
                    if not vip_port_id:
                        st.error("Load Balancer chưa có VIP Port.")

                    elif vip_lb.get("provisioning_status") != "ACTIVE":
                        st.warning(
                            "Load Balancer chưa ACTIVE. Hãy chờ trạng thái "
                            "ACTIVE rồi thử lại."
                        )

                    else:
                        fips, err = list_floating_ips(token)

                        if fips is None or err:
                            st.error(
                                err or "Không tải được danh sách Floating IP."
                            )
                        else:
                            attached_fips = [
                                f for f in fips
                                if isinstance(f, dict)
                                and f.get("port_id") == vip_port_id
                            ]

                            if attached_fips:
                                address = attached_fips[0].get(
                                    "floating_ip_address"
                                )
                                st.info(
                                    "VIP đã có Floating IP: "
                                    f"{address or 'Không rõ địa chỉ'}"
                                )
                                if address:
                                    st.code(f"http://{address}")
                            else:
                                with st.spinner(
                                    "Đang gắn Floating IP vào VIP..."
                                ):
                                    fip, err = create_floating_ip(
                                        token,
                                        external_network_id,
                                        vip_port_id,
                                    )

                                if fip:
                                    address = fip.get("floating_ip_address")
                                    st.success(
                                        "Đã gửi yêu cầu tạo Floating IP "
                                        "và gắn vào VIP."
                                    )
                                    if address:
                                        st.code(f"http://{address}")
                                else:
                                    st.error(
                                        err or "Không gắn được Floating IP."
                                    )
