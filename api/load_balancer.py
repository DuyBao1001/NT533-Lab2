
import requests
from config import LOADBALANCER_URL


def _headers(token):
    return {
        "X-Auth-Token": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _url(path):
    return f"{LOADBALANCER_URL.rstrip('/')}/lbaas/{path.lstrip('/')}"


def list_load_balancers(token):
    try:
        response = requests.get(
            _url("loadbalancers"),
            headers=_headers(token),
            timeout=5,
        )

        if response.status_code == 200:
            return response.json().get("loadbalancers", []), None

        return None, (
            f"HTTP {response.status_code}: {response.text}"
        )

    except requests.RequestException as e:
        return None, f"Lỗi kết nối Octavia API: {e}"


def create_load_balancer(token, name, subnet_id):
    payload = {
        "loadbalancer": {
            "name": name,
            "vip_subnet_id": subnet_id,
            "description": "NT533 Web Load Balancing",
        }
    }

    try:
        response = requests.post(
            _url("loadbalancers"),
            headers=_headers(token),
            json=payload,
            timeout=60,
        )

        if response.status_code in (200, 201, 202):
            return response.json().get("loadbalancer"), None

        return None, (
            f"HTTP {response.status_code}: {response.text}"
        )

    except requests.RequestException as e:
        return None, f"Lỗi kết nối Octavia API: {e}"

def get_load_balancer(token, lb_id):
    try:
        r = requests.get(
            _url(f"loadbalancers/{lb_id}"),
            headers=_headers(token),
            timeout=5,
        )
        if r.status_code == 200:
            return r.json().get("loadbalancer"), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except requests.RequestException as e:
        return None, str(e)


def list_listeners(token):
    try:
        r = requests.get(
            _url("listeners"),
            headers=_headers(token),
            timeout=30,
        )
        if r.status_code == 200:
            return r.json().get("listeners", []), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except requests.RequestException as e:
        return None, str(e)


def create_listener(token, lb_id, name="http-listener"):
    payload = {
        "listener": {
            "name": name,
            "loadbalancer_id": lb_id,
            "protocol": "HTTP",
            "protocol_port": 80,
        }
    }
    try:
        r = requests.post(
            _url("listeners"),
            headers=_headers(token),
            json=payload,
            timeout=60,
        )
        if r.status_code in (200, 201, 202):
            return r.json().get("listener"), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except requests.RequestException as e:
        return None, str(e)


def list_pools(token):
    try:
        r = requests.get(
            _url("pools"),
            headers=_headers(token),
            timeout=30,
        )
        if r.status_code == 200:
            return r.json().get("pools", []), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except requests.RequestException as e:
        return None, str(e)


def create_pool(token, listener_id, name="web-pool"):
    payload = {
        "pool": {
            "name": name,
            "listener_id": listener_id,
            "protocol": "HTTP",
            "lb_algorithm": "ROUND_ROBIN",
        }
    }
    try:
        r = requests.post(
            _url("pools"),
            headers=_headers(token),
            json=payload,
            timeout=60,
        )
        if r.status_code in (200, 201, 202):
            return r.json().get("pool"), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except requests.RequestException as e:
        return None, str(e)


def list_members(token, pool_id):
    try:
        r = requests.get(
            _url(f"pools/{pool_id}/members"),
            headers=_headers(token),
            timeout=30,
        )
        if r.status_code == 200:
            return r.json().get("members", []), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except requests.RequestException as e:
        return None, str(e)


def add_pool_member(token, pool_id, address, subnet_id, port=80):
    payload = {
        "member": {
            "name": address,
            "address": address,
            "protocol_port": int(port),
            "subnet_id": subnet_id,
        }
    }
    try:
        r = requests.post(
            _url(f"pools/{pool_id}/members"),
            headers=_headers(token),
            json=payload,
            timeout=60,
        )
        if r.status_code in (200, 201, 202):
            return r.json().get("member"), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except requests.RequestException as e:
        return None, str(e)


def list_health_monitors(token):
    try:
        r = requests.get(
            _url("healthmonitors"),
            headers=_headers(token),
            timeout=30,
        )
        if r.status_code == 200:
            return r.json().get("healthmonitors", []), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except requests.RequestException as e:
        return None, str(e)


def create_health_monitor(token, pool_id):
    payload = {
        "healthmonitor": {
            "name": "web-health-monitor",
            "pool_id": pool_id,
            "type": "HTTP",
            "delay": 5,
            "timeout": 2,
            "max_retries": 3,
            "http_method": "GET",
            "url_path": "/",
            "expected_codes": "200",
        }
    }
    try:
        r = requests.post(
            _url("healthmonitors"),
            headers=_headers(token),
            json=payload,
            timeout=60,
        )
        if r.status_code in (200, 201, 202):
            return r.json().get("healthmonitor"), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except requests.RequestException as e:
        return None, str(e)
