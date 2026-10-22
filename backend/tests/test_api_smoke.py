def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_app_error_contract(client):
    """领域异常统一错误契约：{code, message}，409 映射。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.config import make_settings
    from app.errors import ConflictError
    from app.main import create_app

    app = create_app(make_settings(str(client.app.state.settings.data_dir) + "-err"))

    def boom():
        raise ConflictError("测试冲突")

    app.add_api_route("/api/boom", boom, methods=["GET"])
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/boom")
        assert r.status_code == 409
        assert r.json() == {"code": "conflict", "message": "测试冲突"}
