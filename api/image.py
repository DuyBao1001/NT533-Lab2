# api/image.py
import requests
from api.logger import logged_request
from config import IMAGE_URL, COMPUTE_URL


def get_images(token):
    """Lấy danh sách Image (thử Glance trước, fallback sang Compute API)"""
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    # 1. Thử gọi Glance Image API
    try:
        response = logged_request("GET", f"{IMAGE_URL}/images", headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("images", []), None
    except Exception:
        pass

    # 2. Fallback sang Compute Image API nếu Glance gặp sự cố (503)
    try:
        response = logged_request("GET", f"{COMPUTE_URL}/images/detail", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("images", []), None
        return None, f"Lỗi {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Lỗi kết nối: {str(e)}"

        return None, f"Lỗi kết nối: {str(e)}"