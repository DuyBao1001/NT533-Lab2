import streamlit as st
import requests
from config import IDENTITY_URL
from api.auth import get_token
from api.compute import get_flavors 
from api.image import get_images    

st.set_page_config(page_title="OpenStack Lab 2", layout="centered")
st.title("Quản lý OpenStack API")

# Khởi tạo session lưu trữ token
if 'token' not in st.session_state:
    st.session_state['token'] = None

# Nếu chưa có token thì hiển thị form đăng nhập
if st.session_state['token'] is None:
    st.subheader("Đăng nhập hệ thống")
    
    with st.form("login_form"):
        username = st.text_input("Username (MSSV)", value="24520190")
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

# Nếu đã có token thì hiển thị giao diện thành công
else:
    st.success("Đã kết nối thành công với hạ tầng OpenStack!")
    
    # Hiển thị 20 ký tự đầu của token để xác nhận
    st.write(f"**Token hiện tại:** `{st.session_state['token'][:20]}...`")
    
    if st.button("Đăng xuất"):
        st.session_state['token'] = None
        st.rerun()

    # --- Debug Service Catalog ---
    with st.expander("🔍 Kiểm tra Service Endpoints (Catalog)"):
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
    
    # --- HIỂN THỊ FLAVOR VÀ IMAGE ---
    st.subheader("1. Danh sách Flavor & Image")

    # Khởi tạo state lưu dữ liệu nếu chưa có
    if 'flavors' not in st.session_state:
        st.session_state['flavors'] = None
    if 'images' not in st.session_state:
        st.session_state['images'] = None
    
    col1, col2 = st.columns(2)
    
    # --- CỘT 1: FLAVOR ---
    with col1:
        if st.button("🔄 Tải lại Flavor"):
            flavors, err = get_flavors(st.session_state['token'])
            if flavors is not None:
                st.session_state['flavors'] = flavors
            else:
                st.error(err)
                
        if st.session_state['flavors']:
            flavor_data = [
                {
                    "ID": f["id"], 
                    "Tên": f["name"], 
                    "vCPU": f["vcpus"], 
                    "RAM (MB)": f["ram"], 
                    "Disk (GB)": f["disk"]
                } for f in st.session_state['flavors']
            ]
            st.dataframe(flavor_data, use_container_width=True)

    # --- CỘT 2: IMAGE ---
    with col2:
        if st.button("🔄 Tải lại Image"):
            images, err = get_images(st.session_state['token'])
            if images is not None:
                st.session_state['images'] = images
            else:
                st.error(err)
                
        if st.session_state['images']:
            image_data = [
                {
                    "ID": img["id"], 
                    "Tên": img.get("name", "N/A"), 
                    "Status": img.get("status", "N/A"),
                    "Format": img.get("disk_format", "N/A")
                } for img in st.session_state['images']
            ]
            st.dataframe(image_data, use_container_width=True)
