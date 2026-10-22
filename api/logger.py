# api/logger.py
"""
Module ghi lại (log) toàn bộ các HTTP request gửi đến OpenStack API.
Các module api/* dùng logged_request() thay cho requests.get/post/put/delete.
"""
import time
import json
import requests
from datetime import datetime

# Bộ đệm log toàn cục — lưu tối đa 100 bản ghi gần nhất
http_logs = []
MAX_LOGS = 100


def _sanitize_headers(headers: dict) -> dict:
    """Ẩn bớt giá trị Token để tránh lộ thông tin nhạy cảm khi hiển thị."""
    if not headers:
        return {}
    result = {}
    for k, v in headers.items():
        if k.lower() == "x-auth-token" and v:
            result[k] = v[:12] + "..." + v[-4:]
        else:
            result[k] = v
    return result


def logged_request(method: str, url: str, headers: dict = None,
                   json_body=None, **kwargs) -> requests.Response:
    """
    Gửi HTTP request, ghi log chi tiết rồi trả về Response như bình thường.
    Dùng thay cho requests.get / post / put / delete trong mọi module API.
    """
    start = time.time()

    log_entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "method": method.upper(),
        "url": url,
        "request_headers": _sanitize_headers(headers),
        "request_body": json_body,
        "response_status": None,
        "response_body": None,
        "duration_ms": None,
        "error": None,
    }

    try:
        response = requests.request(
            method, url, headers=headers, json=json_body, **kwargs
        )
        log_entry["duration_ms"] = int((time.time() - start) * 1000)
        log_entry["response_status"] = response.status_code

        # Cố parse JSON, nếu không thì lấy text ngắn
        try:
            body = response.json()
            # Rút gọn nếu response quá dài
            body_str = json.dumps(body, ensure_ascii=False, indent=2)
            if len(body_str) > 2000:
                body_str = body_str[:2000] + "\n... (rút gọn)"
            log_entry["response_body"] = body_str
        except Exception:
            log_entry["response_body"] = response.text[:500]

        _append_log(log_entry)
        return response

    except Exception as exc:
        log_entry["duration_ms"] = int((time.time() - start) * 1000)
        log_entry["error"] = str(exc)
        _append_log(log_entry)
        raise


def _append_log(entry: dict):
    """Chèn log vào đầu danh sách (mới nhất ở trên cùng)."""
    http_logs.insert(0, entry)
    if len(http_logs) > MAX_LOGS:
        http_logs.pop()


def clear_logs():
    """Xóa toàn bộ log."""
    http_logs.clear()

