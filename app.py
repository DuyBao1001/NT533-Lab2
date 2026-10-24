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
    # ================================================================
    st.divider()
    st.subheader("6. Cấu hình Load Balancer")

    token = st.session_state["token"]

    # 1. TỰ ĐỘNG TẢI DANH SÁCH LOAD BALANCER KHI TRANG LOAD
    col_btn_lb, _ = st.columns([1, 4])
    with col_btn_lb:
        if st.button("Làm mới danh sách Load Balancer", key="lb_refresh", type="secondary"):
            st.session_state["lb_items"] = None

    if "lb_items" not in st.session_state or st.session_state["lb_items"] is None:
        lbs, err = list_load_balancers(token)
        if lbs is not None:
            st.session_state["lb_items"] = lbs
        else:
            st.error(err)

    lb_items = st.session_state.get("lb_items") or []

    if not lb_items:
        st.info("Chưa có Load Balancer nào hoặc không tìm thấy dữ liệu.")
    else:
        lb_options = {
            f"{lb.get('name')} | {lb.get('provisioning_status')} | {lb.get('id')}":
            lb["id"]
            for lb in lb_items
        }

        selected_lb_label = st.selectbox(
            "Chọn Load Balancer",
            list(lb_options.keys()),
            key="lb_selected",
        )
        selected_lb_id = lb_options[selected_lb_label]

        if st.button("Kiểm tra trạng thái Load Balancer", key="lb_check"):
            lb, err = get_load_balancer(token, selected_lb_id)
            if lb:
                st.json({
                    "name": lb.get("name"),
                    "id": lb.get("id"),
                    "vip_address": lb.get("vip_address"),
                    "vip_port_id": lb.get("vip_port_id"),
                    "provisioning_status": lb.get("provisioning_status"),
                    "operating_status": lb.get("operating_status"),
                })
                st.session_state["selected_lb_detail"] = lb
            else:
                st.error(err)

        # ------------------------------------------------------------
        # 6.1. LISTENER HTTP
        # ------------------------------------------------------------
        st.markdown("#### 6.1. Listener HTTP")

        listener_name = st.text_input(
            "Tên Listener",
            value="http-listener",
            key="lb_listener_name",
        )

        if st.button("Tạo Listener HTTP port 80", key="lb_create_listener"):
            lb, err = get_load_balancer(token, selected_lb_id)

            if not lb:
                st.error(err)
            elif lb.get("provisioning_status") != "ACTIVE":
                st.warning(
                    "Load Balancer chưa ACTIVE. Hãy đợi rồi thử lại."
                )
            else:
                listener, err = create_listener(
                    token, selected_lb_id, listener_name.strip()
                )
                if listener:
                    st.success("Đã gửi yêu cầu tạo Listener.")
                    st.json(listener)
                    st.session_state["lb_listener_items"] = None  # Reset để tự động nạp lại ở bước sau
                else:
                    st.error(err)

        # ------------------------------------------------------------
        # 6.2. POOL ROUND_ROBIN
        # ------------------------------------------------------------
        st.markdown("#### 6.2. Pool ROUND_ROBIN")

        # 2. TỰ ĐỘNG TẢI DANH SÁCH LISTENER KHI TRANG LOAD
        if "lb_listener_items" not in st.session_state or st.session_state["lb_listener_items"] is None:
            items, err = list_listeners(token)
            if items is not None:
                st.session_state["lb_listener_items"] = items
            else:
                st.session_state["lb_listener_items"] = []

        listener_items = st.session_state.get("lb_listener_items") or []

        # Chỉ cho chọn Listener thuộc Load Balancer đang chọn
        listener_items = [
            item for item in listener_items
            if selected_lb_id in [
                x.get("id") if isinstance(x, dict) else x
                for x in item.get("loadbalancers", [])
            ]
            or item.get("loadbalancer_id") == selected_lb_id
        ]

        if listener_items:
            listener_options = {
                f"{x.get('name')} | {x.get('protocol')}:{x.get('protocol_port')} | {x.get('id')}":
                x["id"]
                for x in listener_items
            }

            selected_listener_label = st.selectbox(
                "Chọn Listener",
                list(listener_options.keys()),
                key="lb_listener_selected",
            )
            selected_listener_id = listener_options[selected_listener_label]

            pool_name = st.text_input(
                "Tên Pool",
                value="web-pool",
                key="lb_pool_name",
            )

            if st.button("Tạo Pool ROUND_ROBIN", key="lb_create_pool"):
                pool, err = create_pool(
                    token, selected_listener_id, pool_name.strip()
                )
                if pool:
                    st.success("Đã gửi yêu cầu tạo Pool.")
                    st.json(pool)
                    st.session_state["lb_pool_items"] = None  # Reset để tự động nạp lại danh sách Pool
                else:
                    st.error(err)
        else:
            st.info("Chưa có Listener nào cho Load Balancer này. Hãy tạo Listener trước.")

        # ------------------------------------------------------------
        # 6.3. THÊM BACKEND VM
        # ------------------------------------------------------------
        st.markdown("#### 6.3. Thêm backend VM")

        # 3. TỰ ĐỘNG TẢI DANH SÁCH POOL KHI TRANG LOAD
        if "lb_pool_items" not in st.session_state or st.session_state["lb_pool_items"] is None:
            items, err = list_pools(token)
            if items is not None:
                st.session_state["lb_pool_items"] = items
            else:
                st.session_state["lb_pool_items"] = []

        pool_items = st.session_state.get("lb_pool_items") or []

        # Chỉ hiển thị Pool gắn với Listener của Load Balancer đang chọn
        current_listener_ids = {x["id"] for x in listener_items}
        pool_items = [
            p for p in pool_items
            if any(
                x.get("id") in current_listener_ids
                for x in p.get("listeners", [])
            )
            or any(
                x.get("id") == selected_lb_id
                for x in p.get("loadbalancers", [])
            )
        ]

        if pool_items:
            pool_options = {
                f"{p.get('name')} | {p.get('protocol')} | {p.get('id')}":
                p["id"]
                for p in pool_items
            }

            selected_pool_label = st.selectbox(
                "Chọn Pool",
                list(pool_options.keys()),
                key="lb_pool_selected",
            )
            selected_pool_id = pool_options[selected_pool_label]

            with st.form("lb_add_member_form"):
                member_ip = st.text_input(
                    "Fixed IP của VM backend",
                    placeholder="Ví dụ: 192.168.12.117",
                )
                member_subnet = st.text_input(
                    "Subnet ID của backend",
                    placeholder="UUID subnet chứa VM",
                )
                member_port = st.number_input(
                    "Port dịch vụ web",
                    min_value=1,
                    max_value=65535,
                    value=80,
                )

                add_member_submit = st.form_submit_button(
                    "Thêm backend vào Pool"
                )

            if add_member_submit:
                if not member_ip.strip() or not member_subnet.strip():
                    st.warning("Nhập Fixed IP và Subnet ID.")
                else:
                    member, err = add_pool_member(
                        token,
                        selected_pool_id,
                        member_ip.strip(),
                        member_subnet.strip(),
                        int(member_port),
                    )
                    if member:
                        st.success("Đã gửi yêu cầu thêm backend.")
                        st.json(member)
                    else:
                        st.error(err)

            if st.button("Xem Members của Pool", key="lb_show_members"):
                members, err = list_members(token, selected_pool_id)
                if members is not None:
                    if members:
                        st.dataframe([
                            {
                                "Tên": m.get("name"),
                                "IP": m.get("address"),
                                "Port": m.get("protocol_port"),
                                "Provisioning": m.get("provisioning_status"),
                                "Operating": m.get("operating_status"),
                            }
                            for m in members
                        ], use_container_width=True)
                    else:
                        st.info("Pool chưa có backend.")
                else:
                    st.error(err)
        else:
            st.info("Chưa có Pool nào cho Load Balancer này. Hãy tạo Pool trước.")

        # ------------------------------------------------------------
        # 6.4. HEALTH MONITOR HTTP
        # ------------------------------------------------------------
        st.markdown("#### 6.4. Health Monitor HTTP")

        if pool_items:
            hm_pool_options = {
                f"{p.get('name')} | {p.get('id')}": p["id"]
                for p in pool_items
            }
            hm_pool_label = st.selectbox(
                "Pool cần giám sát",
                list(hm_pool_options.keys()),
                key="lb_hm_pool",
            )
            hm_pool_id = hm_pool_options[hm_pool_label]

            if st.button("Tạo Health Monitor HTTP", key="lb_create_hm"):
                hm, err = create_health_monitor(token, hm_pool_id)
                if hm:
                    st.success("Đã gửi yêu cầu tạo Health Monitor.")
                    st.json(hm)
                else:
                    st.error(err)

            if st.button("Xem Health Monitors", key="lb_list_hm"):
                monitors, err = list_health_monitors(token)
                if monitors is not None:
                    st.dataframe([
                        {
                            "ID": h.get("id"),
                            "Pool ID": h.get("pool_id"),
                            "Loại": h.get("type"),
                            "Trạng thái": h.get("provisioning_status"),
                        }
                        for h in monitors
                    ], use_container_width=True)
                else:
                    st.error(err)
        
        # ------------------------------------------------------------
        # 6.5. GẮN FLOATING IP VÀO VIP
        # ------------------------------------------------------------
        st.markdown("#### 6.5. Gắn Floating IP vào VIP")

        external_network_id = st.text_input(
            "External Network ID",
            key="lb_external_network_id",
            placeholder="UUID mạng ngoài được cấp phép",
        )

        if st.button("Kiểm tra Floating IP của VIP", key="lb_check_vip_fip"):
            lb, err = get_load_balancer(token, selected_lb_id)

            if not lb:
                st.error(err)
            else:
                vip_port_id = lb.get("vip_port_id")
                st.write("VIP Address:", lb.get("vip_address"))
                st.write("VIP Port ID:", vip_port_id)

                if not vip_port_id:
                    st.error("Load Balancer chưa có VIP Port.")
                else:
                    fips, err = list_floating_ips(token)

                    if fips is None:
                        st.error(err)
                    else:
                        attached = [
                            f for f in fips
                            if f.get("port_id") == vip_port_id
                        ]

                        if attached:
                            for fip in attached:
                                st.success(
                                    "Floating IP hiện có: "
                                    + str(fip.get("floating_ip_address"))
                                )
                                st.code(
                                    "http://" + str(fip.get("floating_ip_address"))
                                )
                        else:
                            st.info("VIP chưa có Floating IP.")

        if st.button("Gắn Floating IP cho VIP", key="lb_attach_vip_fip"):
            if not external_network_id.strip():
                st.warning("Nhập External Network ID trước.")
            else:
                lb, err = get_load_balancer(token, selected_lb_id)

                if not lb:
                    st.error(err)
                elif lb.get("provisioning_status") != "ACTIVE":
                    st.warning("Load Balancer chưa ACTIVE.")
                else:
                    vip_port_id = lb.get("vip_port_id")

                    if not vip_port_id:
                        st.error("Không tìm thấy VIP Port ID.")
                    else:
                        fips, err = list_floating_ips(token)

                        if fips is None:
                            st.error(err)
                        else:
                            attached = [
                                f for f in fips
                                if f.get("port_id") == vip_port_id
                            ]

                            if attached:
                                st.info(
                                    "VIP đã có Floating IP: "
                                    + str(attached[0].get("floating_ip_address"))
                                )
                            else:
                                fip, err = create_floating_ip(
                                    token,
                                    external_network_id.strip(),
                                    vip_port_id,
                                )

                                if fip:
                                    st.success("Đã gửi yêu cầu gắn Floating IP.")
                                    st.code(
                                        "http://"
                                        + str(fip.get("floating_ip_address"))
                                    )
                                else:
                                    st.error(err)
