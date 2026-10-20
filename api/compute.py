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