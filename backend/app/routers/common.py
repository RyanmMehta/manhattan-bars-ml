from fastapi import Response

from ..context import Ctx


def set_list_headers(response: Response, rows: list[dict], total: int | None = None) -> None:
    flags = {bool(r.get("is_synthetic")) for r in rows}
    response.headers["X-Data"] = (
        "mixed" if flags == {True, False} else "synthetic" if flags == {True} else "real"
    )
    if total is not None:
        response.headers["X-Total-Count"] = str(total)


def label(ctx: Ctx) -> str:
    return ctx.engine_label
