# server/utils/pagination.py
# 通用列表分页：返回 (total, items)。
# - 调用方传入 page（从 1 开始）才分页，返回本页数据 + 写入响应头 X-Total-Count 等；
# - 不传 page（如小程序首页拉取全量线路/订单）则直接返回全部，保持旧行为，避免截断。
from fastapi import Response

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def paginate(query, page=None, page_size: int = DEFAULT_PAGE_SIZE):
    """返回 (total, items)。page 为 None 时返回全部（不分页）。"""
    if page is None:
        items = query.all()
        return len(items), items
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > MAX_PAGE_SIZE:
        page_size = MAX_PAGE_SIZE
    total = query.count()
    items = query.limit(page_size).offset((page - 1) * page_size).all()
    return total, items


def set_pagination_headers(response: Response, page, page_size: int, total: int):
    """把分页元信息写入响应头（便于前端渲染分页条）。response 为 None 时跳过。
    page 为 None（未分页）时仅写总数，不写页码/页大小。"""
    if response is None:
        return
    response.headers["X-Total-Count"] = str(total)
    if page is not None:
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(page_size)
