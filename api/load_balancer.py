# api/load_balancer.py
import requests
from api.logger import logged_request
from config import LOADBALANCER_URL


def _headers(token):
    return {
        "X-Auth-Token": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _call(method, path, token, body=None, key=None, timeout=30):
    """Gọi Octavia API. Trả về (dữ liệu, lỗi); DELETE (key=None) trả về (True, None)."""
    url = f"{LOADBALANCER_URL.rstrip('/')}/lbaas/{path.lstrip('/')}"
    try:
        r = logged_request(method, url, headers=_headers(token), json_body=body, timeout=timeout)
    except requests.RequestException as e:
        return None, f"Lỗi kết nối Octavia API: {e}"

    if r.status_code in (200, 201, 202, 204):
        return (r.json().get(key) if key else True), None
    return None, f"HTTP {r.status_code}: {r.text}"


# ==================== LOAD BALANCER ====================

def list_load_balancers(token):
    return _call("GET", "loadbalancers", token, key="loadbalancers")


def get_load_balancer(token, lb_id):
    return _call("GET", f"loadbalancers/{lb_id}", token, key="loadbalancer")


def create_load_balancer(token, name, subnet_id):
    body = {"loadbalancer": {
        "name": name,
        "vip_subnet_id": subnet_id,
        "description": "NT533 Web Load Balancing",
    }}
    return _call("POST", "loadbalancers", token, body, "loadbalancer", timeout=60)


# ==================== LISTENER ====================

def list_listeners(token):
    return _call("GET", "listeners", token, key="listeners")


def create_listener(token, lb_id, name="http-listener"):
    body = {"listener": {
        "name": name,
        "loadbalancer_id": lb_id,
        "protocol": "TCP",
        "protocol_port": 80,
    }}
    return _call("POST", "listeners", token, body, "listener", timeout=60)


# ==================== POOL & MEMBER ====================

def list_pools(token):
    return _call("GET", "pools", token, key="pools")


def create_pool(token, listener_id, name="web-pool", algorithm="SOURCE_IP_PORT"):
    body = {"pool": {
        "name": name,
        "listener_id": listener_id,
        "protocol": "TCP",
        "lb_algorithm": algorithm,
    }}
    return _call("POST", "pools", token, body, "pool", timeout=60)


def update_pool_algorithm(token, pool_id, algorithm):
    body = {"pool": {"lb_algorithm": algorithm}}
    return _call("PUT", f"pools/{pool_id}", token, body, "pool", timeout=60)


def list_members(token, pool_id):
    return _call("GET", f"pools/{pool_id}/members", token, key="members")


def add_pool_member(token, pool_id, address, subnet_id, port=80):
    body = {"member": {
        "name": address,
        "address": address,
        "protocol_port": int(port),
        "subnet_id": subnet_id,
    }}
    return _call("POST", f"pools/{pool_id}/members", token, body, "member", timeout=60)


def delete_pool_member(token, pool_id, member_id):
    return _call("DELETE", f"pools/{pool_id}/members/{member_id}", token, timeout=60)


# ==================== HEALTH MONITOR ====================

def list_health_monitors(token):
    return _call("GET", "healthmonitors", token, key="healthmonitors")


def create_health_monitor(token, pool_id):
    body = {"healthmonitor": {
        "name": "tcp-health-monitor",
        "pool_id": pool_id,
        "type": "TCP",
        "delay": 5,
        "timeout": 2,
        "max_retries": 3,
    }}
    return _call("POST", "healthmonitors", token, body, "healthmonitor", timeout=60)
