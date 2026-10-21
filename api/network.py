
import requests
from config import NETWORK_URL


def _get_headers(token):
    return {
        "X-Auth-Token": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


def list_routers(token):
    url = f"{NETWORK_URL.rstrip('/')}/routers"

    try:
        response = requests.get(
            url,
            headers=_get_headers(token),
            timeout=5
        )

        if response.status_code == 200:
            return response.json().get("routers", []), None

        return None, (
            f"Lỗi hiển thị Routers: HTTP "
            f"{response.status_code} - {response.text}"
        )

    except requests.RequestException as e:
        return None, f"Không thể kết nối Network API: {e}"


def create_router(token, name):
    url = f"{NETWORK_URL.rstrip('/')}/routers"

    payload = {
        "router": {
            "name": name,
            "admin_state_up": True
        }
    }

    try:
        response = requests.post(
            url,
            headers=_get_headers(token),
            json=payload,
            timeout=5
        )

        if response.status_code in (200, 201):
            return response.json().get("router"), None

        return None, (
            f"Lỗi tạo Router: HTTP "
            f"{response.status_code} - {response.text}"
        )

    except requests.RequestException as e:
        return None, f"Không thể kết nối Network API: {e}"


def delete_router(token, router_id):
    url = f"{NETWORK_URL.rstrip('/')}/routers/{router_id}"

    try:
        response = requests.delete(
            url,
            headers=_get_headers(token),
            timeout=5
        )

        if response.status_code in (200, 202, 204):
            return True, None

        return False, (
            f"Lỗi xóa Router: HTTP "
            f"{response.status_code} - {response.text}"
        )

    except requests.RequestException as e:
        return False, f"Không thể kết nối Network API: {e}"


def get_networks(token):
    url = f"{NETWORK_URL.rstrip('/')}/networks"

    try:
        response = requests.get(
            url,
            headers=_get_headers(token),
            timeout=10
        )

        if response.status_code == 200:
            return response.json().get("networks", []), None

        return None, (
            f"Lỗi lấy Networks: HTTP "
            f"{response.status_code} - {response.text}"
        )

    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def create_network(token, name):
    url = f"{NETWORK_URL.rstrip('/')}/networks"

    payload = {
        "network": {
            "name": name,
            "admin_state_up": True
        }
    }

    try:
        response = requests.post(
            url,
            headers=_get_headers(token),
            json=payload,
            timeout=10
        )

        if response.status_code == 201:
            return response.json().get("network"), None

        return None, (
            f"Lỗi tạo Network: HTTP "
            f"{response.status_code} - {response.text}"
        )

    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def delete_network(token, network_id):
    url = f"{NETWORK_URL.rstrip('/')}/networks/{network_id}"

    try:
        response = requests.delete(
            url,
            headers=_get_headers(token),
            timeout=10
        )

        if response.status_code in (200, 204):
            return True, None

        return False, (
            f"Lỗi xóa Network: HTTP "
            f"{response.status_code} - {response.text}"
        )

    except requests.RequestException as e:
        return False, f"Lỗi kết nối Network API: {e}"


def get_subnets(token):
    url = f"{NETWORK_URL.rstrip('/')}/subnets"

    try:
        response = requests.get(
            url,
            headers=_get_headers(token),
            timeout=10
        )

        if response.status_code == 200:
            return response.json().get("subnets", []), None

        return None, (
            f"Lỗi lấy Subnets: HTTP "
            f"{response.status_code} - {response.text}"
        )

    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def create_subnet(token, network_id, name, cidr, gateway_ip=None):
    url = f"{NETWORK_URL.rstrip('/')}/subnets"

    subnet_data = {
        "network_id": network_id,
        "ip_version": 4,
        "cidr": cidr,
        "name": name
    }

    if gateway_ip and gateway_ip.strip():
        subnet_data["gateway_ip"] = gateway_ip.strip()

    payload = {"subnet": subnet_data}

    try:
        response = requests.post(
            url,
            headers=_get_headers(token),
            json=payload,
            timeout=10
        )

        if response.status_code == 201:
            return response.json().get("subnet"), None

        return None, (
            f"Lỗi tạo Subnet: HTTP "
            f"{response.status_code} - {response.text}"
        )

    except requests.RequestException as e:
        return None, f"Lỗi kết nối Network API: {e}"


def delete_subnet(token, subnet_id):
    url = f"{NETWORK_URL.rstrip('/')}/subnets/{subnet_id}"

    try:
        response = requests.delete(
            url,
            headers=_get_headers(token),
            timeout=10
        )

        if response.status_code in (200, 204):
            return True, None

        return False, (
            f"Lỗi xóa Subnet: HTTP "
            f"{response.status_code} - {response.text}"
        )

    except requests.RequestException as e:
        return False, f"Lỗi kết nối Network API: {e}"
