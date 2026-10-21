import requests
from config import NETWORK_URL

def list_routers(token):
    url = f"{NETWORK_URL.rstrip('/')}/routers"
    headers = {
        "X-Auth-Token": token,
        "Accept": "application/json"
    }
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("routers", []), None
        
        return None, f"Lỗi hiển thị Routers: HTTP {response.status_code} - {response.text}"
        
    except requests.RequestException as e:
        return None, f"Không thể kết nối Network API: {e}"


def create_router(token, name):
    url = f"{NETWORK_URL.rstrip('/')}/routers"
    headers = {
        "X-Auth-Token": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "router": {
            "name": name,
            "admin_state_up": True
        }
    }

    try:
        response = requests.post(
            url, 
            headers=headers,
            json=payload,
            timeout=5
        )
        if response.status_code in (200, 201):
            return response.json().get("router"), None
            
        return None, f"Lỗi tạo Router: HTTP {response.status_code} - {response.text}"
        
    except requests.RequestException as e:
        return None, f"Không thể kết nối Network API: {e}"


def delete_router(token, router_id):
    url = f"{NETWORK_URL.rstrip('/')}/routers/{router_id}"
    headers = {
        "X-Auth-Token": token,
        "Accept": "application/json"
    }

    try:
        response = requests.delete(
            url,
            headers=headers,
            timeout=5
        )
        if response.status_code in (200, 202, 204):
            return True, None
            
        return False, f"Lỗi xóa Router: HTTP {response.status_code} - {response.text}"
        
    except requests.RequestException as e:
        return False, f"Không thể kết nối Network API: {e}"