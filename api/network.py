# api/network.py
import requests
from api.logger import logged_request
from config import NETWORK_URL


def _get_headers(token):
    return {
        "X-Auth-Token": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


# ==================== ROUTER APIS ====================

def list_routers(token):
    """Liệt kê danh sách Routers"""
    url = f"{NETWORK_URL.rstrip('/')}/routers"
    try:
        response = logged_request("GET", url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return response.json().get("routers", []), None
        return None, f"Lỗi hiển thị Routers: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Không thể kết nối Network API: {e}"


def create_router(token, name, external_network_id=None):
    """Tạo mới Router, hỗ trợ gắn External Gateway"""
    url = f"{NETWORK_URL.rstrip('/')}/routers"
    router_data = {"name": name, "admin_state_up": True}
    if external_network_id and external_network_id.strip():
        router_data["external_gateway_info"] = {"network_id": external_network_id.strip()}

    payload = {"router": router_data}
    try:
        response = logged_request("POST", url, headers=_get_headers(token), json_body=payload, timeout=10)
        if response.status_code in (200, 201):
            return response.json().get("router"), None
        return None, f"Lỗi tạo Router: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Không thể kết nối Network API: {e}"


def delete_router(token, router_id):
    """Xóa Router theo ID"""
    url = f"{NETWORK_URL.rstrip('/')}/routers/{router_id}"
    try:
        response = logged_request("DELETE", url, headers=_get_headers(token), timeout=10)
        if response.status_code in (200, 202, 204):
            return True, None
        return False, f"Lỗi xóa Router: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return False, f"Không thể kết nối Network API: {e}"


def add_router_interface(token, router_id, subnet_id):
    """Nối một Subnet vào Router"""
    url = f"{NETWORK_URL.rstrip('/')}/routers/{router_id}/add_router_interface"
    payload = {"subnet_id": subnet_id}
    try:
        response = logged_request("PUT", url, headers=_get_headers(token), json_body=payload, timeout=10)
        if response.status_code == 200:
            return response.json(), None
        return None, f"Lỗi nối Subnet vào Router: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def remove_router_interface(token, router_id, subnet_id):
    """Gỡ một Subnet ra khỏi Router"""
    url = f"{NETWORK_URL.rstrip('/')}/routers/{router_id}/remove_router_interface"
    payload = {"subnet_id": subnet_id}
    try:
        response = logged_request("PUT", url, headers=_get_headers(token), json_body=payload, timeout=10)
        if response.status_code == 200:
            return response.json(), None
        return None, f"Lỗi gỡ Subnet khỏi Router: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


# ==================== NETWORK APIS ====================

def get_external_networks(token):
    """Lấy danh sách các External Network (router:external=True) để dùng làm Gateway"""
    url = f"{NETWORK_URL.rstrip('/')}/networks?router:external=True"
    try:
        response = logged_request("GET", url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return response.json().get("networks", []), None
        return None, f"Lỗi lấy External Networks: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def get_networks(token):
    """Liệt kê danh sách Networks"""
    url = f"{NETWORK_URL.rstrip('/')}/networks"
    try:
        response = logged_request("GET", url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return response.json().get("networks", []), None
        return None, f"Lỗi lấy Networks: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def create_network(token, name):
    """Tạo mới Network"""
    url = f"{NETWORK_URL.rstrip('/')}/networks"
    payload = {"network": {"name": name, "admin_state_up": True}}
    try:
        response = logged_request("POST", url, headers=_get_headers(token), json_body=payload, timeout=10)
        if response.status_code == 201:
            return response.json().get("network"), None
        return None, f"Lỗi tạo Network: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def delete_network(token, network_id):
    """Xóa Network theo ID"""
    url = f"{NETWORK_URL.rstrip('/')}/networks/{network_id}"
    try:
        response = logged_request("DELETE", url, headers=_get_headers(token), timeout=10)
        if response.status_code in (200, 204):
            return True, None
        return False, f"Lỗi xóa Network: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return False, f"Lỗi kết nối Network API: {e}"


# ==================== SUBNET APIS ====================

def get_subnets(token):
    """Liệt kê danh sách Subnets"""
    url = f"{NETWORK_URL.rstrip('/')}/subnets"
    try:
        response = logged_request("GET", url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return response.json().get("subnets", []), None
        return None, f"Lỗi lấy Subnets: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def create_subnet(token, network_id, name, cidr, gateway_ip=None, dns_nameservers=None):
    """Tạo mới Subnet gắn vào một Network"""
    url = f"{NETWORK_URL.rstrip('/')}/subnets"
    subnet_data = {"network_id": network_id, "ip_version": 4, "cidr": cidr, "name": name}
    if gateway_ip and gateway_ip.strip():
        subnet_data["gateway_ip"] = gateway_ip.strip()
    if dns_nameservers:
        subnet_data["dns_nameservers"] = dns_nameservers

    payload = {"subnet": subnet_data}
    try:
        response = logged_request("POST", url, headers=_get_headers(token), json_body=payload, timeout=10)
        if response.status_code == 201:
            return response.json().get("subnet"), None
        return None, f"Lỗi tạo Subnet: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def delete_subnet(token, subnet_id):
    """Xóa Subnet theo ID"""
    url = f"{NETWORK_URL.rstrip('/')}/subnets/{subnet_id}"
    try:
        response = logged_request("DELETE", url, headers=_get_headers(token), timeout=10)
        if response.status_code in (200, 204):
            return True, None
        return False, f"Lỗi xóa Subnet: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return False, f"Lỗi kết nối Network API: {e}"


# ==================== FLOATING IP ====================

def get_instance_ports(token, instance_id):
    """Tìm các port mạng gắn với một VM"""
    url = f"{NETWORK_URL.rstrip('/')}/ports"
    try:
        response = logged_request(
            "GET", url, headers=_get_headers(token),
            params={"device_id": instance_id}, timeout=10
        )
        if response.status_code == 200:
            return response.json().get("ports", []), None

        return None, (
            f"HTTP {response.status_code}: {response.text}"
        )

    except requests.RequestException as e:
        return None, str(e)

def list_floating_ips(token):
    """Liệt kê Floating IP trong phạm vi quyền truy cập."""
    url = f"{NETWORK_URL.rstrip('/')}/floatingips"

    try:
        response = logged_request("GET", url, headers=_get_headers(token), timeout=10)

        if response.status_code == 200:
            return response.json().get("floatingips", []), None

        return None, (
            f"HTTP {response.status_code}: {response.text}"
        )

    except requests.RequestException as e:
        return None, str(e)

def create_floating_ip(token, external_network_id, port_id):
    """Cấp Floating IP và gắn trực tiếp vào port của VM."""
    url = f"{NETWORK_URL.rstrip('/')}/floatingips"

    payload = {
        "floatingip": {
            "floating_network_id": external_network_id,
            "port_id": port_id
        }
    }

    try:
        response = logged_request("POST", url, headers=_get_headers(token), json_body=payload, timeout=10)

        if response.status_code in (200, 201):
            return response.json().get("floatingip"), None

        return None, (
            f"HTTP {response.status_code}: {response.text}"
        )

    except requests.RequestException as e:
        return None, str(e)

