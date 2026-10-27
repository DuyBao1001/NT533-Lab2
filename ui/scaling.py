# ui/scaling.py
"""Mục 7: Tăng/giảm số lượng máy ảo, tự động cập nhật Pool của Load Balancer."""
import streamlit as st

from api.compute import list_instances
from api.load_balancer import list_members
from api.scaling import next_names, scale_out, scale_in
from ui.common import load, invalidate, refresh_button, flash, table, choices, server_ips
from ui.instances import instance_spec_fields
from ui.loadbalancer import lb_pools, members_key

MAX_INSTANCES = 20


def _finish(action, errors):
    """Ghi kết quả vào flash và tải lại trang để bảng hiển thị dữ liệu mới."""
    if errors:
        flash("error", f"{action} chưa hoàn tất:\n\n" + "\n\n".join(f"- {e}" for e in errors))
    else:
        flash("success", f"{action} hoàn tất.")
    st.rerun()


def _render_scale_out(token, lb_id, pool_id, instances, count):
    st.markdown(f"##### Tăng thêm {count} máy ảo")
    col_prefix, col_port = st.columns(2)
    prefix = col_prefix.text_input("Tiền tố tên máy ảo", value="web", key="scale_prefix").strip()
    port = col_port.number_input("Port ứng dụng", min_value=1, max_value=65535, value=80, step=1, key="scale_port")

    with st.expander("Cấu hình máy ảo mới"):
        spec = instance_spec_fields(token, "scale")

    if not st.button(f"Tăng thêm {count} máy ảo", type="primary", width="stretch", key="scale_out"):
        return
    if not prefix or not all(spec[k] for k in ("image_id", "flavor_id", "network_id")):
        st.warning("Vui lòng nhập tiền tố tên, Image, Flavor và Network.")
        return

    names = next_names(prefix, {s.get("name") for s in instances}, count)
    with st.status("Đang tăng số lượng máy ảo...", expanded=True) as status:
        errors = scale_out(token, lb_id, pool_id, names, spec, int(port), st.write)
        status.update(label="Hoàn tất" if not errors else "Có lỗi", state="complete" if not errors else "error")
    invalidate("instances", "lb_items", members_key(pool_id))
    _finish("Tăng máy ảo", errors)


def _render_scale_in(token, lb_id, pool_id, members, vm_by_address, count):
    st.markdown(f"##### Giảm {count} máy ảo")

    def label(m):
        vm = vm_by_address.get(m.get("address"))
        return f"{m.get('address')} ({vm.get('name') if vm else 'không rõ máy ảo'})"

    options = choices(members, label)
    # Mặc định chọn các backend thêm vào gần nhất
    selected = st.multiselect(
        "Backend cần gỡ", list(options),
        default=list(options)[-count:], key=f"scale_in_{pool_id}_{count}",
    )
    delete_vms = st.checkbox("Xóa luôn các máy ảo tương ứng", value=True, key="scale_delete_vms")

    if len(selected) != count:
        st.warning(f"Cần chọn đúng {count} backend (đang chọn {len(selected)}).")
    if not st.button(f"Giảm {count} máy ảo", type="primary", width="stretch",
                     disabled=len(selected) != count, key="scale_in"):
        return

    chosen = [m for m in members if m["id"] in {options[s] for s in selected}]
    with st.status("Đang giảm số lượng máy ảo...", expanded=True) as status:
        errors = scale_in(token, lb_id, pool_id, chosen, vm_by_address, delete_vms, st.write)
        status.update(label="Hoàn tất" if not errors else "Có lỗi", state="complete" if not errors else "error")
    invalidate("instances", "lb_items", members_key(pool_id))
    _finish("Giảm máy ảo", errors)


def render_scaling(token):
    st.subheader("7. Tăng/Giảm máy ảo")
    lb_id = st.session_state.get("lb_selected_id")
    if not lb_id:
        st.info("Hãy chọn Load Balancer ở mục 6 trước.")
        return

    _, pools = lb_pools(token, lb_id)
    if not pools:
        st.info("Load Balancer đang chọn chưa có Pool.")
        return

    pool_options = choices(pools, lambda p: p.get("name") or "(Không tên)")
    pool_id = pool_options[st.selectbox("Pool", list(pool_options), key="scale_pool")]

    refresh_button("Làm mới Backend", "instances", members_key(pool_id), key="refresh_scaling")
    instances = load("instances", list_instances, token)
    members = load(members_key(pool_id), list_members, token, pool_id)
    vm_by_address = {ip: s for s in instances for ip in server_ips(s)}
    current = len(members)

    st.caption(f"Pool hiện có {current} Backend")
    if members:
        table([
            {
                "Máy ảo": vm_by_address[m["address"]].get("name") if m.get("address") in vm_by_address else "N/A",
                "Địa chỉ": m.get("address"),
                "Port": m.get("protocol_port"),
                "Provisioning": m.get("provisioning_status"),
                "Operating": m.get("operating_status"),
            }
            for m in members
        ])

    # Key chứa số lượng hiện tại để ô nhập tự đặt lại sau khi thay đổi
    desired = int(st.number_input(
        "Số lượng máy ảo mong muốn", min_value=0, max_value=MAX_INSTANCES,
        value=current, step=1, key=f"scale_desired_{pool_id}_{current}",
    ))

    if desired > current:
        _render_scale_out(token, lb_id, pool_id, instances, desired - current)
    elif desired < current:
        _render_scale_in(token, lb_id, pool_id, members, vm_by_address, current - desired)
    else:
        st.caption("Số lượng mong muốn bằng số lượng hiện tại.")
