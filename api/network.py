import requests
from config import NETWORK_URL

def _get_headers(token):
    return {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

def get_networks(token):
    try:
        url = f"{NETWORK_URL}/networks"
        response = requests.get(url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return response.json().get("networks", []), None
        else:
            return None, f"Lỗi: {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Lỗi kết nối: {str(e)}"

def create_network(token, name):
    try:
        url = f"{NETWORK_URL}/networks"
        payload = {
            "network": {
                "name": name,
                "admin_state_up": True
            }
        }
        response = requests.post(url, headers=_get_headers(token), json=payload, timeout=10)
        if response.status_code == 201:
            return response.json().get("network"), None
        else:
            return None, f"Lỗi {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Lỗi kết nối: {str(e)}"

def delete_network(token, network_id):
    try:
        url = f"{NETWORK_URL}/networks/{network_id}"
        response = requests.delete(url, headers=_get_headers(token), timeout=10)
        if response.status_code in [200, 204]:
            return True, None
        else:
            return False, f"Lỗi {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Lỗi kết nối: {str(e)}"

def get_subnets(token):
    try:
        url = f"{NETWORK_URL}/subnets"
        response = requests.get(url, headers=_get_headers(token), timeout=10)
        if response.status_code == 200:
            return response.json().get("subnets", []), None
        else:
            return None, f"Lỗi {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Lỗi kết nối: {str(e)}"
    
def create_subnet(token, network_id, name, cidr, gateway_ip=None):
    try:
        url = f"{NETWORK_URL}/subnets"
        subnet_data = {
            "network_id": network_id,
            "ip_version": 4,
            "cidr": cidr,
            "name": name
        }
        if gateway_ip and gateway_ip.strip():
            subnet_data["gateway_ip"] = gateway_ip.strip()
        payload = {"subnet": subnet_data}
        response = requests.post(url, headers=_get_headers(token), json=payload, timeout=10)
        if response.status_code == 201:
            return response.json().get("subnet"), None
        else:
            return None, f"Lỗi {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Lỗi kết nối: {str(e)}"
    
def delete_subnet(token, subnet_id):
    try:
        url = f"{NETWORK_URL}/subnets/{subnet_id}"
        response = requests.delete(url, headers=_get_headers(token), timeout=10)
        if response.status_code in [200, 204]:
            return True, None
        else:
            return False, f"Lỗi {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Lỗi kết nối: {str(e)}"