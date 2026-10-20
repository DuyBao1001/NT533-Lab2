# api/image.py
import requests
from config import IMAGE_URL, COMPUTE_URL

def get_images(token):
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }
    
    # 1. Thử gọi Glance Image API
    try:
        response = requests.get(f"{IMAGE_URL}/images", headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("images", []), None
    except Exception:
        pass

    # 2. Fallback sang Compute Image API nếu Glance gặp sự cố (503)
    try:
        response = requests.get(f"{COMPUTE_URL}/images/detail", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("images", []), None
        else:
            return None, f"Lỗi {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Lỗi kết nối: {str(e)}"