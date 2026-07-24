import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"

def req(method, path, token=None, data=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "null")

print("=== 1. Admin login (JWT) ===")
st, login = req("POST", "/api/admin/login", data={"username": "admin", "password": "admin123"})
print("status", st, "| token?:", bool(login.get("token")), "| id:", login.get("id"), "| role:", login.get("role"))
token = login.get("token")
assert token, "no token"
assert st == 200

print("\n=== 2. Dashboard (new schema) ===")
st, dash = req("GET", "/api/admin/dashboard", token=token)
print("status", st)
print("keys:", sorted(dash.keys()))
print("today_orders:", dash.get("today_orders"), "| month_income:", dash.get("month_income"),
      "| profit:", dash.get("profit"), "| customer_growth:", dash.get("customer_growth"),
      "| active_routes:", dash.get("active_routes"))
print("top_routes count:", len(dash.get("top_routes", [])), "| order_trend count:", len(dash.get("order_trend", [])),
      "| pending_confirm:", dash.get("pending_confirm_orders"), "| pending_deposit:", dash.get("pending_deposit_orders"))

print("\n=== 3. Dashboard WITHOUT token -> 401 ===")
st, _ = req("GET", "/api/admin/dashboard")
print("status", st, "(expect 401)")

print("\n=== 4. Banners admin (JWT) ===")
st, bs = req("GET", "/api/banners/admin", token=token)
print("status", st, "| banners:", len(bs))
if bs:
    print("sample banner:", {k: bs[0].get(k) for k in ("id", "image", "title", "route_id", "sort", "status")})
# create -> update -> delete cycle
st, created = req("POST", "/api/banners/admin", token=token,
                  data={"image": "https://picsum.photos/seed/test/600/300", "title": "测试Banner", "sort": 99, "status": "active"})
print("create status", st, "| id:", created.get("id"))
bid = created.get("id")
st, upd = req("PUT", f"/api/banners/admin/{bid}", token=token, data={"status": "inactive"})
print("update status", st, "| status now:", upd.get("status"))
st, _ = req("DELETE", f"/api/banners/admin/{bid}", token=token)
print("delete status", st)

print("\n=== 5. Routes cost_price / gallery exposed ===")
st, routes = req("GET", "/api/routes")
print("status", st, "| routes:", len(routes))
r0 = routes[0]
print("route0 has cost_price?:", "cost_price" in r0, "| gallery:", r0.get("gallery"))
# create a route with gallery + cost
st, nr = req("POST", "/api/routes", data={"name": "测试线", "category": "国内游", "days": 3,
        "departure": "上海", "destination": "杭州", "price": 1000, "cost_price": 600,
        "gallery": ["https://x.com/a.jpg", "https://x.com/b.jpg"], "status": "active"})
print("create route status", st, "| cost_price:", nr.get("cost_price"), "| gallery:", nr.get("gallery"))
nid = nr.get("id")
st, got = req("GET", f"/api/routes/{nid}")
print("get route gallery parsed?:", got.get("gallery"))
st, _ = req("DELETE", f"/api/routes/{nid}")
print("delete test route status", st)

print("\n=== 6. Order detail + action flow ===")
# create an order
st, order = req("POST", "/api/orders", data={"name": "验证客户", "phone": "13800000000",
        "person_count": 2, "route_id": 1})
print("create order status", st, "| id:", order.get("id"), "| status:", order.get("status"), "| total:", order.get("total_amount"))
oid = order.get("id")
st, od = req("GET", f"/api/orders/{oid}")
print("get order status", st, "| status:", od.get("status"))
st, c = req("POST", f"/api/orders/{oid}/confirm", token=token)
print("confirm status", st, "| msg:", c.get("msg"), "| status:", c.get("status"))
st, comp = req("POST", f"/api/orders/{oid}/complete", token=token)
print("complete status", st, "| status:", comp.get("status"))
# cleanup
st, _ = req("DELETE", f"/api/orders/{oid}")
print("cleanup (no delete endpoint? status):", st)

print("\nALL CHECKS DONE")
