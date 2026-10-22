# api/compute.py
import base64
import requests
from api.logger import logged_request
from config import COMPUTE_URL


def _get_headers(token):
    return {
        "X-Auth-Token": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


def get_flavors(token):
    """Lấy danh sách chi tiết các Flavor"""
    url = f"{COMPUTE_URL.rstrip('/')}/flavors/detail"
    try:
        response = logged_request("GET", url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return response.json().get("flavors", []), None
        return None, f"Lỗi lấy Flavor: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Compute API: {e}"


def list_instances(token):
    """Liệt kê danh sách máy ảo chi tiết"""
    url = f"{COMPUTE_URL.rstrip('/')}/servers/detail"
    try:
        response = logged_request("GET", url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return response.json().get("servers", []), None
        return None, f"Lỗi hiển thị Instances: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Không thể kết nối Compute API: {e}"


def get_instance(token, server_id):
    """Lấy thông tin chi tiết của 1 máy ảo theo ID"""
    url = f"{COMPUTE_URL.rstrip('/')}/servers/{server_id}"
    try:
        response = logged_request("GET", url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return response.json().get("server"), None
        return None, f"Lỗi lấy thông tin Instance: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Không thể kết nối Compute API: {e}"


def create_instance(token, name, image_id, flavor_id, network_id,
                    user_data=None, key_name=None, security_groups=None):
    """Khởi tạo máy ảo mới"""
    url = f"{COMPUTE_URL.rstrip('/')}/servers"
    server_data = {
        "name": name,
        "imageRef": image_id,
        "flavorRef": flavor_id,
        "networks": [{"uuid": network_id}]
    }
    if user_data and user_data.strip():
        server_data["user_data"] = base64.b64encode(user_data.strip().encode("utf-8")).decode("utf-8")
    if key_name and key_name.strip():
        server_data["key_name"] = key_name.strip()
    if security_groups:
        server_data["security_groups"] = [{"name": sg} for sg in security_groups]

    payload = {"server": server_data}
    try:
        response = logged_request("POST", url, headers=_get_headers(token), json_body=payload, timeout=15)
        if response.status_code in (200, 201, 202):
            return response.json().get("server"), None
        return None, f"Lỗi tạo Instance: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Compute API: {e}"


def delete_instance(token, server_id):
    """Xóa máy ảo theo ID"""
    url = f"{COMPUTE_URL.rstrip('/')}/servers/{server_id}"
    try:
        response = logged_request("DELETE", url, headers=_get_headers(token), timeout=10)
        if response.status_code in (200, 202, 204):
            return True, None
        return False, f"Lỗi xóa Instance: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return False, f"Không thể kết nối Compute API: {e}"


def server_action(token, server_id, action):
    """Thực hiện thao tác: 'start', 'stop', 'reboot'"""
    url = f"{COMPUTE_URL.rstrip('/')}/servers/{server_id}/action"
    if action == "reboot":
        payload = {"reboot": {"type": "SOFT"}}
    elif action == "start":
        payload = {"os-start": None}
    elif action == "stop":
        payload = {"os-stop": None}
    else:
        return False, f"Hành động '{action}' không hợp lệ."
    try:
        response = logged_request("POST", url, headers=_get_headers(token), json_body=payload, timeout=10)
        if response.status_code in (200, 202):
            return True, None
        return False, f"Lỗi thao tác {action}: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return False, f"Lỗi kết nối Compute API: {e}"


def list_keypairs(token):
    """Lấy danh sách SSH Keypair đã tạo"""
    url = f"{COMPUTE_URL.rstrip('/')}/os-keypairs"
    try:
        response = logged_request("GET", url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return [item.get("keypair", {}) for item in response.json().get("keypairs", [])], None
        return [], None
    except Exception:
        return [], None
