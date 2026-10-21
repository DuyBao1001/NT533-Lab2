import streamlit as st
import requests
from config import IDENTITY_URL
from api.auth import get_token
from api.compute import get_flavors 
from api.image import get_images
from api.network import (
    get_networks, create_network, delete_network,
    get_subnets, create_subnet, delete_subnet
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
        password = st.text_input("Password", type="password")
        project = st.text_input("Project Name", value="NT533.R12.G12")
        
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
    
    # Hiển thị 20 ký tự đầu của token để xác nhận
    st.write(f"**Token hiện tại:** `{st.session_state['token'][:20]}...`")
    
    if st.button("Đăng xuất"):
        st.session_state['token'] = None
        st.rerun()

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
    
    st.subheader("1. Danh sách Flavor & Image")
    tab_flavor, tab_image = st.tabs(["Flavor", "Image"])
    # ==================== TAB FLAVOR ====================
    with tab_flavor:
        col_btn_flavor, _ = st.columns([1, 4])
        with col_btn_flavor:
            if st.button("Làm mới Flavor"):
                st.session_state['flavors'] = None
        # Tự động tải nếu chưa có dữ liệu trong session
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
                    "Ephemeral Disk (GB)": f.get("OS-FLV-EXT-DATA:ephemeral", 0)
                } for f in st.session_state['flavors']
            ]
            st.dataframe(flavor_data, use_container_width=True)
    # ==================== TAB IMAGE ====================
    with tab_image:
        col_btn_image, _ = st.columns([1, 4])
        with col_btn_image:
            if st.button("Làm mới Image"):
                st.session_state['images'] = None
        # Tự động tải nếu chưa có dữ liệu trong session
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
                    "Định dạng (Format)": img.get("disk_format", "N/A"),
                    "Min Disk (GB)": img.get("min_disk", img.get("minDisk", 0)),
                    "Min RAM (MB)": img.get("min_ram", img.get("minRam", 0))
                } for img in st.session_state['images']
            ]
            st.dataframe(image_data, use_container_width=True)

    st.divider()

    st.subheader("2. Quản lý Network & Subnet")

    tab_net, tab_sub = st.tabs(["Network", "Subnet"])

    with tab_net:
        col_list_net, col_action_net = st.columns([3, 2])

        with col_list_net:
            st.markdown("##### Danh sách Network")
            if st.button("Làm mới Network"):
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
                submit_create_net = st.form_submit_button("Tạo Network")

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
                net_options = {f"{n.get('name')} ({n['id'][:8]}...)": n['id'] for n in st.session_state['networks']}
                selected_net_to_delete = st.selectbox("Chọn Network cần xóa", list(net_options.keys()), key="del_net_sel")
                if st.button("Xóa Network đã chọn"):
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
            if st.button("Làm mới Subnet"):
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
                    net_choices = {f"{n.get('name')} ({n['id'][:8]}...)": n['id'] for n in st.session_state['networks']}
                    selected_parent_net = st.selectbox("Thuộc Network", list(net_choices.keys()))
                    parent_net_id = net_choices[selected_parent_net]
                else:
                    parent_net_id = st.text_input("Network ID", placeholder="Nhập ID của Network")

                new_sub_name = st.text_input("Tên Subnet", placeholder="Ví dụ: nhom12_subnet")
                new_cidr = st.text_input("Dải mạng (CIDR)", placeholder="Ví dụ: 192.168.12.0/24")
                new_gateway = st.text_input("Gateway IP (Không bắt buộc)", placeholder="Ví dụ: 192.168.12.1")
                submit_create_sub = st.form_submit_button("Tạo Subnet")

                if submit_create_sub:
                    if not new_sub_name or not new_cidr or not parent_net_id:
                        st.warning("Vui lòng nhập đủ Tên Subnet, CIDR và Network cha.")
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
                sub_options = {f"{s.get('name')} ({s.get('cidr')})": s['id'] for s in st.session_state['subnets']}
                selected_sub_to_delete = st.selectbox("Chọn Subnet cần xóa", list(sub_options.keys()), key="del_sub_sel")
                if st.button("Xóa Subnet đã chọn"):
                    sub_id = sub_options[selected_sub_to_delete]
                    success, err = delete_subnet(st.session_state['token'], sub_id)
                    if success:
                        st.success("Xóa Subnet thành công!")
                        st.session_state['subnets'] = None
                        st.session_state['networks'] = None
                        st.rerun()
                    else:
                        st.error(err)
