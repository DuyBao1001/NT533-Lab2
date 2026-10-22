# api/compute.py
import requests
from config import COMPUTE_URL

def get_flavors(token):
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }
    
    try:
        # Gọi GET request để lấy chi tiết Flavor
        response = requests.get(f"{COMPUTE_URL}/flavors/detail", headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("flavors", []), None
        else:
            return None, f"Lỗi {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Lỗi kết nối: {str(e)}"

def list_instances(token):
    url = f"{COMPUTE_URL.rstrip('/')}/servers"
    headers = {
        "X-Auth-Token": toekn,
        "Accept": "application/json"
        "Content-Type": "application/json"
    }
    try:
        response = request.get(
            url, 
            headers = headers,
            timeout = 5
        )
        
        if response.status_code == 200:
            return response.json().get("servers", []), None
        return None, (
            f"Lỗi hiển thị Instances: HTTP "
            f"{response.status_code} - {response.text}"
        )
        except resquets.RequestException as e:
            return None, f"Không thể kết nối Compute API: {e}"
def create_instance(token, name, image_id, flavor_id, network_id):
    url = f"{COMPUTE_URL.rstrip('/')}/servers"
    headers = {
        "X-Auth-Token": token, 
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "server":{
            "name": name,
            "imageRef": image_id,
            "flavorRef": flavor_id,
            "network": [
                {
                    "uuid": network_id
                }
            ]
        }
    }  
    try:
        response = request.post(
            url, 
            headers = headers,
            json = payload,
            timeout = 5
        )
        if response.status_code in (200, 201):
            return response.json().get("server", []), None
        return None, (
            f"Lỗi tạo Instance: HTTP "
            f"{response.status_code} - {response.text}"
        )
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Compute API: {e}"
