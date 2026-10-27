# ui/loadbalancer.py
"""Mục 6: Load Balancer, Listener, Pool, Backend, Health Monitor, Floating IP cho VIP."""
import streamlit as st

from api.compute import list_instances
from api.load_balancer import (
    list_load_balancers, create_load_balancer, get_load_balancer,
    list_listeners, create_listener, list_pools, create_pool, update_pool_algorithm,
    list_members, add_pool_member, delete_pool_member,
    list_health_monitors, create_health_monitor,
)
from api.network import (
    get_networks, get_subnets, get_instance_ports, list_floating_ips, create_floating_ip,
)
from ui.common import (
    load, invalidate, refresh_button, flash, table, choices, external_networks,
)


# Mục đầu tiên là mặc định. Provider OVN của cloud này chấp nhận SOURCE_IP_PORT
# và từ chối ROUND_ROBIN; các thuật toán còn lại chưa được kiểm chứng.
ALGORITHMS = {
    "SOURCE_IP_PORT": "Theo IP và cổng nguồn",
    "ROUND_ROBIN": "Luân phiên lần lượt",
    "LEAST_CONNECTIONS": "Ít kết nối nhất",
    "SOURCE_IP": "Theo IP nguồn",
}


def _algorithm_label(algorithm):
    return f"{algorithm} - {ALGORITHMS[algorithm]}"


def _select_algorithm(label, key, current=None):
    """Selectbox thuật toán cân bằng tải, trả về tên thuật toán."""
    names = list(ALGORITHMS)
    index = names.index(current) if current in names else 0
    return st.selectbox(label, names, index=index, format_func=_algorithm_label, key=key)


def _ref_id(ref):
    """Octavia trả về tham chiếu dạng {"id": ...} hoặc chuỗi ID."""
    return ref.get("id") if isinstance(ref, dict) else ref


def lb_pools(token, lb_id):
    """Danh sách (listeners, pools) thuộc Load Balancer đã chọn."""
    all_listeners = load("lb_listeners", list_listeners, token)
    all_pools = load("lb_pools", list_pools, token)

    listeners = [
        l for l in all_listeners
        if l.get("loadbalancer_id") == lb_id
        or lb_id in [_ref_id(x) for x in l.get("loadbalancers") or []]
    ]
    listener_ids = {l["id"] for l in listeners}
    pools = [
        p for p in all_pools
        if p.get("listener_id") in listener_ids
        or listener_ids & {_ref_id(x) for x in p.get("listeners") or []}
    ]
    return listeners, pools


def members_key(pool_id):
    return f"lb_members_{pool_id}"


def _render_lb_select(token):
    """6.1. Trả về ID Load Balancer đang chọn (hoặc None)."""
    st.markdown("#### 6.1. Load Balancer")

    with st.expander("Tạo Load Balancer mới"):
        subnets = load("subnets", get_subnets, token)
        if not subnets:
            st.warning("Chưa có Subnet để tạo Load Balancer.")
        else:
            options = choices(subnets, lambda s: f"{s.get('name') or '(Không tên)'} | {s.get('cidr', '')}")
            with st.form("lb_create_form"):
                name = st.text_input("Tên Load Balancer", value="lb-demo")
                subnet_label = st.selectbox("Subnet chứa VIP", list(options))
                submitted = st.form_submit_button("Tạo Load Balancer", width="stretch")
            if submitted:
                if not name.strip():
                    st.warning("Vui lòng nhập tên Load Balancer.")
                else:
                    with st.spinner("Đang tạo Load Balancer..."):
                        lb, err = create_load_balancer(token, name.strip(), options[subnet_label])
                    if lb:
                        flash("success", "Đã gửi yêu cầu tạo Load Balancer.")
                        st.session_state["lb_selected_id"] = lb.get("id")
                        invalidate("lb_items")
                        st.rerun()
                    else:
                        st.error(err)

    refresh_button("Làm mới danh sách Load Balancer", "lb_items")
    lbs = load("lb_items", list_load_balancers, token)
    if not lbs:
        st.info("Chưa có Load Balancer nào. Hãy tạo mới ở trên.")
        return None

    st.caption(f"Tổng số: {len(lbs)} Load Balancer")
    table([
        {
            "ID": lb.get("id"),
            "Tên": lb.get("name") or "(Không tên)",
            "Provisioning": lb.get("provisioning_status", "N/A"),
            "Operating": lb.get("operating_status", "N/A"),
            "VIP Address": lb.get("vip_address", "N/A"),
            "VIP Subnet": lb.get("vip_subnet_id", "N/A"),
        }
        for lb in lbs
    ])

    options = choices(lbs, lambda lb: f"{lb.get('name') or '(Không tên)'} | {lb.get('provisioning_status') or 'Unknown'}")
    ids = list(options.values())
    saved = st.session_state.get("lb_selected_id")
    selected = st.selectbox(
        "Chọn Load Balancer", list(options),
        index=ids.index(saved) if saved in ids else 0,
    )
    st.session_state["lb_selected_id"] = options[selected]
    return options[selected]


def _render_listeners(token, lb_id):
    st.markdown("#### 6.2. Listener TCP")

    with st.expander("Tạo Listener TCP"):
        with st.form("lb_create_listener_form"):
            name = st.text_input("Tên Listener", value="tcp-listener-demo")
            submitted = st.form_submit_button("Tạo Listener TCP", width="stretch")
        if submitted:
            if not name.strip():
                st.warning("Vui lòng nhập tên Listener.")
            else:
                with st.spinner("Đang tạo Listener..."):
                    listener, err = create_listener(token, lb_id, name.strip())
                if listener:
                    flash("success", "Đã gửi yêu cầu tạo Listener.")
                    invalidate("lb_listeners", "lb_pools")
                    st.rerun()
                else:
                    st.error(err)

    refresh_button("Làm mới Listener", "lb_listeners")
    listeners, pools = lb_pools(token, lb_id)
    if listeners:
        table([
            {
                "Tên": l.get("name", ""),
                "ID": l.get("id", ""),
                "Protocol": l.get("protocol", ""),
                "Port": l.get("protocol_port", ""),
                "Provisioning": l.get("provisioning_status", ""),
                "Operating": l.get("operating_status", ""),
            }
            for l in listeners
        ])
    else:
        st.info("Load Balancer này chưa có Listener.")
    return listeners, pools


def _render_pools(token, listeners, pools):
    st.markdown("#### 6.3. Pool")

    if listeners:
        options = choices(listeners, lambda l: f"{l.get('name') or '(Không tên)'} | {l.get('protocol')}:{l.get('protocol_port')}")
        with st.expander("Tạo Pool mới"):
            with st.form("lb_create_pool_form"):
                name = st.text_input("Tên Pool", value="tcp-pool")
                listener_label = st.selectbox("Listener gắn với Pool", list(options))
                algorithm = _select_algorithm("Thuật toán cân bằng tải", "pool_create_algorithm")
                st.caption("Provider OVN sẽ từ chối thuật toán mà nó không hỗ trợ (ví dụ ROUND_ROBIN).")
                submitted = st.form_submit_button("Tạo Pool", width="stretch")
            if submitted:
                if not name.strip():
                    st.warning("Vui lòng nhập tên Pool.")
                else:
                    with st.spinner("Đang tạo Pool..."):
                        pool, err = create_pool(token, options[listener_label], name.strip(), algorithm)
                    if pool:
                        flash("success", "Đã gửi yêu cầu tạo Pool.")
                        invalidate("lb_pools")
                        st.rerun()
                    else:
                        st.error(err)
    else:
        st.info("Cần có Listener trước khi tạo Pool.")

    refresh_button("Làm mới Pool", "lb_pools")
    if pools:
        table([
            {
                "Tên": p.get("name", ""),
                "ID": p.get("id", ""),
                "Protocol": p.get("protocol", ""),
                "Thuật toán": p.get("lb_algorithm", ""),
                "Provisioning": p.get("provisioning_status", ""),
            }
            for p in pools
        ])
    elif listeners:
        st.info("Load Balancer này chưa có Pool.")

    if pools:
        st.markdown("##### Đổi thuật toán cân bằng tải")
        pool_options = choices(pools, lambda p: p.get("name") or "(Không tên)")
        col_pool, col_algorithm = st.columns(2)
        pool_label = col_pool.selectbox("Pool", list(pool_options), key="pool_algorithm_pool")
        pool_id = pool_options[pool_label]
        current = next((p.get("lb_algorithm") for p in pools if p["id"] == pool_id), None)
        with col_algorithm:
            algorithm = _select_algorithm("Thuật toán mới", f"pool_algorithm_{pool_id}_{current}", current)
        if st.button("Cập nhật thuật toán", width="stretch", key="pool_update_algorithm", disabled=algorithm == current):
            with st.spinner("Đang cập nhật Pool..."):
                pool, err = update_pool_algorithm(token, pool_id, algorithm)
            if pool:
                flash("success", f"Đã gửi yêu cầu đổi thuật toán sang {algorithm}.")
                invalidate("lb_pools")
                st.rerun()
            else:
                st.error(err)


def _vm_fixed_ips(token, server_id, subnet_names):
    """Fixed IP của một máy ảo: {nhãn: (ip, subnet_id)}."""
    ports = load(f"vm_ports_{server_id}", get_instance_ports, token, server_id)
    return {
        f"{f['ip_address']} | {subnet_names.get(f.get('subnet_id'), f.get('subnet_id'))}": (f["ip_address"], f.get("subnet_id"))
        for p in ports for f in p.get("fixed_ips", []) if f.get("ip_address")
    }


def _render_backends(token, pools):
    st.markdown("#### 6.4. Backend VM")
    if not pools:
        st.info("Cần có Pool trước khi thêm Backend.")
        return

    pool_options = choices(pools, lambda p: p.get("name") or "(Không tên)")
    pool_id = pool_options[st.selectbox("Pool", list(pool_options), key="backend_pool")]

    instances = load("instances", list_instances, token)
    subnets = load("subnets", get_subnets, token)
    subnet_names = {s["id"]: s.get("name") or s["id"] for s in subnets}

    vm_options = choices(instances, lambda s: s.get("name") or "(Không tên)")
    vm_id = vm_options[st.selectbox("Backend VM", list(vm_options), key="backend_vm")] if vm_options else None
    refresh_button("Làm mới Backend", members_key(pool_id), f"vm_ports_{vm_id}", key="refresh_backends")

    with st.expander("Thêm Backend"):
        if not vm_id:
            st.warning("Chưa có Instance nào.")
        else:
            ip_options = _vm_fixed_ips(token, vm_id, subnet_names)
            if not ip_options:
                st.warning("Máy ảo chưa có Fixed IP. Kiểm tra trạng thái Instance.")
            else:
                ip_label = st.selectbox("Fixed IP", list(ip_options), key="backend_ip")
                port = st.number_input("Port ứng dụng", min_value=1, max_value=65535, value=80, step=1, key="backend_port")
                if st.button("Thêm Backend", width="stretch", key="backend_add"):
                    address, subnet_id = ip_options[ip_label]
                    with st.spinner("Đang thêm Backend..."):
                        member, err = add_pool_member(token, pool_id, address, subnet_id, int(port))
                    if member:
                        flash("success", f"Đã gửi yêu cầu thêm Backend {address}.")
                        invalidate(members_key(pool_id))
                        st.rerun()
                    else:
                        st.error(err)

    members = load(members_key(pool_id), list_members, token, pool_id)
    if not members:
        st.info("Pool hiện chưa có Backend.")
        return

    table([
        {
            "Địa chỉ": m.get("address"),
            "Port": m.get("protocol_port"),
            "Provisioning": m.get("provisioning_status"),
            "Operating": m.get("operating_status"),
            "ID": m.get("id"),
        }
        for m in members
    ])

    options = choices(members, lambda m: f"{m.get('address')}:{m.get('protocol_port')}")
    selected = st.selectbox("Backend cần gỡ", list(options), key="backend_remove_select")
    if st.button("Gỡ Backend khỏi Pool", key="backend_remove", type="primary"):
        ok, err = delete_pool_member(token, pool_id, options[selected])
        if ok:
            flash("success", "Đã gửi yêu cầu gỡ Backend.")
            invalidate(members_key(pool_id))
            st.rerun()
        else:
            st.error(err)


def _render_health_monitors(token, pools):
    st.markdown("#### 6.5. Health Monitor")
    if not pools:
        st.info("Cần có Pool trước khi tạo Health Monitor.")
        return

    pool_options = choices(pools, lambda p: p.get("name") or "(Không tên)")
    pool_id = pool_options[st.selectbox("Pool cần giám sát", list(pool_options), key="hm_pool")]
    if st.button("Tạo Health Monitor TCP", width="stretch", key="hm_create"):
        with st.spinner("Đang tạo Health Monitor..."):
            hm, err = create_health_monitor(token, pool_id)
        if hm:
            flash("success", "Đã gửi yêu cầu tạo Health Monitor.")
            invalidate("lb_monitors")
            st.rerun()
        else:
            st.error(err)

    refresh_button("Làm mới Health Monitor", "lb_monitors")
    pool_ids = {p["id"] for p in pools}
    monitors = [
        hm for hm in load("lb_monitors", list_health_monitors, token)
        if hm.get("pool_id") in pool_ids
        or pool_ids & {_ref_id(x) for x in hm.get("pools") or []}
    ]
    if monitors:
        table([
            {
                "Tên": hm.get("name", ""),
                "ID": hm.get("id", ""),
                "Loại": hm.get("type", ""),
                "Delay": hm.get("delay", ""),
                "Timeout": hm.get("timeout", ""),
                "Provisioning": hm.get("provisioning_status", ""),
                "Operating": hm.get("operating_status", ""),
            }
            for hm in monitors
        ])
    else:
        st.info("Các Pool của Load Balancer này chưa có Health Monitor.")


def _render_vip_floating_ip(token, lb_id):
    st.markdown("#### 6.6. Floating IP cho VIP")
    lb = next((x for x in st.session_state.get("lb_items") or [] if x.get("id") == lb_id), {})
    vip_port_id = lb.get("vip_port_id")

    col_vip, col_status = st.columns(2)
    col_vip.metric("VIP Address", str(lb.get("vip_address") or "Chưa có"))
    col_status.metric("Provisioning", str(lb.get("provisioning_status") or "Unknown"))
    if not vip_port_id:
        st.warning("Load Balancer chưa có VIP Port.")
        return

    refresh_button("Làm mới Floating IP", "floating_ips", key="refresh_vip_fips")
    attached = [f for f in load("floating_ips", list_floating_ips, token) if f.get("port_id") == vip_port_id]
    if attached:
        address = attached[0].get("floating_ip_address")
        st.success(f"VIP đã có Floating IP: {address}")
        st.code(f"http://{address}")
        return

    externals = external_networks(load("networks", get_networks, token))
    if not externals:
        st.warning("Không tìm thấy External Network. Hãy kiểm tra quyền truy cập hoặc cấu hình mạng.")
        return

    options = choices(externals)
    ext_id = options[st.selectbox("External Network", list(options), key="vip_ext")]
    if not st.button("Gắn Floating IP vào VIP", width="stretch", key="vip_attach"):
        return

    fresh, err = get_load_balancer(token, lb_id)
    if not fresh:
        st.error(err)
    elif fresh.get("provisioning_status") != "ACTIVE":
        st.warning("Load Balancer chưa ACTIVE. Hãy chờ trạng thái ACTIVE rồi thử lại.")
    else:
        with st.spinner("Đang gắn Floating IP vào VIP..."):
            fip, err = create_floating_ip(token, ext_id, vip_port_id)
        if fip:
            flash("success", f"Đã gắn Floating IP {fip.get('floating_ip_address')} vào VIP.")
            invalidate("floating_ips", "lb_items")
            st.rerun()
        else:
            st.error(err)


def render_load_balancer(token):
    st.subheader("6. Cấu hình Load Balancer")
    lb_id = _render_lb_select(token)
    if not lb_id:
        return

    st.divider()
    listeners, pools = _render_listeners(token, lb_id)
    st.divider()
    _render_pools(token, listeners, pools)
    st.divider()
    _render_backends(token, pools)
    st.divider()
    _render_health_monitors(token, pools)
    st.divider()
    _render_vip_floating_ip(token, lb_id)
