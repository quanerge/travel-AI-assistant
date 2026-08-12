import main
from fastapi.testclient import TestClient
from models import User
from database import SessionLocal
from routers.auth import get_current_user

db = SessionLocal()
u = db.query(User).first()
uid = u.id if u else 1
db.close()

def fake_user():
    return User(id=uid)

main.app.dependency_overrides[get_current_user] = fake_user
c = TestClient(main.app)
r = c.post("/api/ai/chat", json={"message": "用一句话测试一下，推荐一个周末周边游", "conversation_id": None})
print("STATUS:", r.status_code)
try:
    print("BODY:", r.json())
except Exception:
    print("BODY(raw):", r.text[:300])
main.app.dependency_overrides.clear()
