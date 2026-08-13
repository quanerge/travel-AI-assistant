# server/seed.py —— 初始化演示数据（线路 + 管理员）
from database import SessionLocal, engine, Base, migrate
import models
from models import Route, RouteDay, AdminUser, Banner
import bcrypt


def fake_hash(pwd: str) -> str:
    return "h:" + pwd


def seed():
    Base.metadata.create_all(bind=engine)
    migrate()  # 确保历史库补齐新列（强度维度等），否则下方回填查询会因列不存在报错
    db = SessionLocal()

    if db.query(Route).count() == 0:
        routes = [
            Route(name="云南8日深度游", category="国内游", days=8, departure="上海",
                  destination="云南", price=2999, rating=4.9, signup_count=18, group_size=20,
                  description="大理丽江香格里拉，慢节奏深度体验。",
                  fee_included="住宿、门票、当地交通、部分餐食",
                  fee_excluded="往返大交通、个人消费",
                  notice="高原注意防晒，建议提前 15 天报名。",
                  intensity_level="easy", max_altitude=3200, daily_walk=6,
                  suitable_crowd="节奏轻松，适合大多数中老年", suitable_age_min=55, suitable_age_max=80),
            Route(name="新疆15日深度游", category="国内游", days=15, departure="上海",
                  destination="新疆", price=3999, rating=4.8, signup_count=28, group_size=20,
                  description="天山南北大环线，一次看遍雪山湖泊沙漠。",
                  fee_included="住宿、门票、用车、导游",
                  fee_excluded="往返大交通、午餐、自费项目",
                  notice="新疆与内地有 2 小时时差，行程宽松安排。",
                  intensity_level="moderate", max_altitude=2000, daily_walk=8,
                  suitable_crowd="行程较长，需一定体力", suitable_age_min=50, suitable_age_max=75),
            Route(name="川西自驾7日", category="短途游", days=7, departure="成都",
                  destination="川西", price=2680, rating=4.7, signup_count=12, group_size=15,
                  description="色达稻城亚丁，自驾摄影天堂。",
                  fee_included="领队、住宿、保险",
                  fee_excluded="车辆油费、门票、餐食",
                  notice="高原路段，需备红景天。",
                  intensity_level="challenge", max_altitude=4500, daily_walk=5,
                  suitable_crowd="高原路段，需提前备红景天", suitable_age_min=45, suitable_age_max=70),
        ]
        for r in routes:
            db.add(r)
        db.flush()
        db.add_all([
            RouteDay(route_id=1, day_no=1, title="抵达大理", content="接机，入住洱海民宿",
                     meals="晚", accommodation="洱海民宿", traffic="飞机"),
            RouteDay(route_id=1, day_no=2, title="洱海环湖", content="骑行环海，双廊古镇",
                     meals="早/晚", accommodation="洱海民宿", traffic="商务车"),
            RouteDay(route_id=2, day_no=1, title="乌鲁木齐", content="集合日，自由活动",
                     meals="无", accommodation="乌市四星", traffic="飞机"),
            RouteDay(route_id=2, day_no=2, title="天山天池", content="天池景区，雪山倒影",
                     meals="早/晚", accommodation="乌市四星", traffic="大巴"),
        ])
        print("已写入 3 条线路及行程。")

    # 功能1：为强度字段缺失的老库线路补默认值（按名称关键词匹配）；未知线路给通用默认
    _intensity_defaults = {
        "云南": dict(intensity_level="easy", max_altitude=3200, daily_walk=6,
                     suitable_crowd="节奏轻松，适合大多数中老年", suitable_age_min=55, suitable_age_max=80),
        "新疆": dict(intensity_level="moderate", max_altitude=2000, daily_walk=8,
                     suitable_crowd="行程较长，需一定体力", suitable_age_min=50, suitable_age_max=75),
        "川西": dict(intensity_level="challenge", max_altitude=4500, daily_walk=5,
                     suitable_crowd="高原路段，需提前备红景天", suitable_age_min=45, suitable_age_max=70),
    }
    _updated = False
    for _r in db.query(Route).filter(Route.intensity_level.is_(None)).all():
        _matched = False
        for _key, _vals in _intensity_defaults.items():
            if _key in (getattr(_r, "name", "") or ""):
                for _k, _v in _vals.items():
                    setattr(_r, _k, _v)
                _matched = True
                break
        if not _matched:
            _r.intensity_level = "normal"
            _r.suitable_crowd = "具体强度请详询顾问"
        _updated = True
    if _updated:
        db.commit()

    if db.query(AdminUser).count() == 0:
        db.add(AdminUser(
            username="admin",
            password_hash=bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            role="super", phone="4000000000"))
        print("已创建管理员 admin / admin123（bcrypt）")

    # 演示用顾问账号（便于体验「用户管理」页角色/权限差异）
    if not db.query(AdminUser).filter(AdminUser.username == "advisor").first():
        db.add(AdminUser(
            username="advisor",
            password_hash=bcrypt.hashpw("advisor123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            role="advisor", phone="4000000001"))
        print("已创建顾问账号 advisor / advisor123（bcrypt）")

    if db.query(Banner).count() == 0:
        db.add_all([
            Banner(image="https://picsum.photos/seed/yunnan/600/300", title="云南8日深度游", route_id=1, sort=1),
            Banner(image="https://picsum.photos/seed/xinjiang/600/300", title="新疆15日深度游", route_id=2, sort=2),
            Banner(image="https://picsum.photos/seed/chuanxi/600/300", title="川西自驾7日", route_id=3, sort=3),
        ])
        print("已写入 3 条 Banner。")

    db.commit()
    db.close()


if __name__ == "__main__":
    seed()
