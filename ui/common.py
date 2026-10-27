# ui/common.py
"""Các hàm giao diện dùng chung cho mọi mục."""
import streamlit as st

DEFAULT_USER_DATA = """#!/bin/bash
set -eux
exec > /var/log/nt533-user-data.log 2>&1
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nginx curl
VM_IP=$(curl -fsS --max-time 5 \\
  http://169.254.169.254/openstack/latest/meta_data.json \\
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


def load(key, fetcher, *args):
    """Tải dữ liệu vào session_state nếu chưa có. Trả về danh sách (rỗng nếu lỗi)."""
    if st.session_state.get(key) is None:
        data, err = fetcher(*args)
        if data is None:
            st.error(err)
            return []
        st.session_state[key] = data
    return st.session_state[key]


def invalidate(*keys):
    """Đánh dấu dữ liệu đã cũ để lần chạy sau tự tải lại."""
    for key in keys:
        st.session_state[key] = None


def refresh_button(label, *keys, key=None):
    if st.button(label, key=key or "refresh_" + "_".join(keys)):
        invalidate(*keys)


def flash(kind, message):
    """Lưu thông báo để hiển thị sau khi st.rerun()."""
    st.session_state["_flash"] = (kind, message)


def show_flash():
    kind, message = st.session_state.pop("_flash", (None, None))
    if kind:
        getattr(st, kind)(message)


def table(rows):
    st.dataframe(rows, width="stretch", hide_index=True)


def short_id(value):
    return f"{value[:8]}..." if value else "N/A"


def name_id(item):
    return f"{item.get('name') or '(Không tên)'} ({short_id(item.get('id'))})"


def choices(items, label=name_id):
    """Ánh xạ nhãn hiển thị -> ID cho selectbox."""
    return {label(i): i["id"] for i in items if i.get("id")}


def external_networks(networks):
    return [n for n in networks if n.get("router:external") is True]


def server_ips(server):
    return [a.get("addr", "") for addrs in server.get("addresses", {}).values() for a in addrs]


def delete_box(noun, key, items, label, deleter, token, *stale_keys):
    """Selectbox + nút xóa dùng chung cho Network, Subnet, Router."""
    st.markdown(f"##### Xóa {noun}")
    if not items:
        return
    options = choices(items, label)
    selected = st.selectbox(f"Chọn {noun} cần xóa", list(options), key=f"del_{key}")
    if st.button(f"Xóa {noun} đã chọn", type="primary", key=f"del_btn_{key}"):
        ok, err = deleter(token, options[selected])
        if ok:
            flash("success", f"Xóa {noun} thành công.")
            invalidate(*stale_keys)
            st.rerun()
        else:
            st.error(err)
