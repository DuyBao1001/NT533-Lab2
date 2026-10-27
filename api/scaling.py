# api/scaling.py
"""Tăng/giảm số lượng máy ảo backend và tự động cập nhật Pool của Load Balancer."""
import time

from api.compute import create_instance, delete_instance, get_instance
from api.load_balancer import add_pool_member, delete_pool_member, get_load_balancer
from api.network import get_instance_ports

POLL_INTERVAL = 5


def _wait(check, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = check()
        if result is not None:
            return result
        time.sleep(POLL_INTERVAL)
    return None


def wait_lb_active(token, lb_id, timeout=180):
    def check():
        lb, _ = get_load_balancer(token, lb_id)
        return True if lb and lb.get("provisioning_status") == "ACTIVE" else None
    return bool(_wait(check, timeout))


def _wait_instance_ip(token, server_id, timeout=300):
    def check():
        server, _ = get_instance(token, server_id)
        if not server:
            return None
        if server.get("status") == "ERROR":
            return ("error", "Máy ảo ở trạng thái ERROR")
        if server.get("status") != "ACTIVE":
            return None
        ports, _ = get_instance_ports(token, server_id)
        for port in ports or []:
            for fixed in port.get("fixed_ips", []):
                if fixed.get("ip_address"):
                    return ("ok", (fixed["ip_address"], fixed.get("subnet_id")))
        return None

    result = _wait(check, timeout)
    if result is None:
        return None, "Hết thời gian chờ máy ảo ACTIVE"
    kind, value = result
    return (value, None) if kind == "ok" else (None, value)


def next_names(prefix, existing, count):
    names, i = [], 1
    while len(names) < count:
        if f"{prefix}-{i}" not in existing:
            names.append(f"{prefix}-{i}")
        i += 1
    return names


def scale_out(token, lb_id, pool_id, names, spec, port, log):
    errors = []

    # Tạo tất cả máy ảo trước để chúng khởi động song song
    created = []
    for name in names:
        log(f"Tạo máy ảo {name}")
        server, err = create_instance(token, name=name, **spec)
        if server:
            created.append((name, server["id"]))
        else:
            errors.append(f"{name}: {err}")

    for name, server_id in created:
        log(f"Chờ {name} ACTIVE và có địa chỉ IP")
        found, err = _wait_instance_ip(token, server_id)
        if not found:
            errors.append(f"{name}: {err}")
            continue

        address, subnet_id = found
        log(f"Thêm {name} ({address}) vào Pool")
        if not wait_lb_active(token, lb_id):
            errors.append(f"{name}: Load Balancer không về trạng thái ACTIVE")
            continue
        member, err = add_pool_member(token, pool_id, address, subnet_id, port)
        if not member:
            errors.append(f"{name}: {err}")
    return errors


def scale_in(token, lb_id, pool_id, members, vm_by_address, delete_vms, log):
    errors = []
    for member in members:
        address = member.get("address")
        log(f"Gỡ {address} khỏi Pool")
        if not wait_lb_active(token, lb_id):
            errors.append(f"{address}: Load Balancer không về trạng thái ACTIVE")
            continue
        ok, err = delete_pool_member(token, pool_id, member["id"])
        if not ok:
            errors.append(f"{address}: {err}")
            continue

        server = vm_by_address.get(address)
        if delete_vms and server:
            log(f"Xóa máy ảo {server.get('name')}")
            ok, err = delete_instance(token, server["id"])
            if not ok:
                errors.append(f"{server.get('name')}: {err}")
    return errors
