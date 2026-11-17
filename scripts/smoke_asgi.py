"""Check the real FastAPI ASGI app without binding a forbidden socket."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.api.app import app
from src.api.contracts import TRAJECTORY_CONTRACT_VERSION, validate_trajectory


async def get(url):
    parsed = urlsplit(url)
    sent = []
    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"}, "http_version": "1.1",
             "method": "GET", "scheme": "http", "path": parsed.path,
             "raw_path": parsed.path.encode(), "query_string": parsed.query.encode(),
             "root_path": "", "headers": [], "client": ("local-test", 0),
             "server": ("local-test", 80)}
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)
    status = next(x["status"] for x in sent if x["type"] == "http.response.start")
    body = b"".join(x.get("body", b"") for x in sent if x["type"] == "http.response.body")
    return status, json.loads(body)


async def main():
    health_status, health = await get("/health")
    assert health_status == 200 and health["status"] == "ok"
    assert health['trajectory_contract_version'] == TRAJECTORY_CONTRACT_VERSION
    profile_status, profile = await get("/students/79021/profile")
    assert profile_status == 200 and len(profile["skills"]) == 149
    route_status, route = await get("/students/79021/trajectory")
    assert route_status == 200 and len(route["trajectory"]) == 5
    validate_trajectory(route)
    assert set(route["focus_skill_ids"]) == {"292", "299", "290", "2_37_70"}
    assert "76" in {x["skill_id"] for x in route["without_materials"]}
    material_status, material = await get("/materials?skill=292")
    assert material_status == 200 and material[0]["skill_id"] == "292"
    catalog_status, catalog = await get("/materials?limit=50")
    assert catalog_status == 200 and len(catalog) == 23
    assert all(x['learning_goal'] and x['worked_example']['solution'] and x['practice_exercises'] for x in catalog)
    other = {}
    for uid, expected in (("75169", 2), ("78970", 4)):
        status, body = await get(f"/students/{uid}/trajectory")
        assert status == 200 and len(body["trajectory"]) == expected
        validate_trajectory(body)
        other[uid] = [x["skill_id"] for x in body["trajectory"]]
    missing_status, _ = await get("/students/unknown/profile")
    invalid_status, _ = await get("/students?limit=0")
    assert missing_status == 404 and invalid_status == 422
    result = {"mode": "in-process ASGI with direct handler shim; no socket or threadpool", "health": health["status"],
              "contract_version": route["contract_version"],
              "all_23_lessons_present": True,
              "profile_skill_ids": len(profile["skills"]),
              "route_79021": [x["skill_id"] for x in route["trajectory"]],
              "other_routes": other, "material_checked": material[0]["title"],
              "catalog_materials": len(catalog),
              "missing_status": missing_status, "invalid_status": invalid_status}
    target = ROOT / "reports/asgi_integration.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    async def direct_handler(func, *args, **kwargs):
        return func(*args, **kwargs)

    # This sandbox also blocks AnyIO worker threads used for sync handlers.
    # The shim exercises FastAPI routing/validation/serialization in-process.
    with patch("fastapi.routing.run_in_threadpool", direct_handler):
        asyncio.run(main())
