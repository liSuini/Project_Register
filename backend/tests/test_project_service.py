import pytest
from app.schemas.dtos import ProjectCreate, ProjectUpdate


def test_create_from_any_stage_with_anchors(db_session):
    from app.models.entities import Node
    from app.services import project_service as ps

    p = ps.create_project(db_session, ProjectCreate(
        name="存量项目", customer="某局", initial_stage="采购",
        contract_amount=8600000))
    assert p.current_stage == p.initial_stage == "采购"
    assert db_session.query(Node).filter_by(project_id=p.id).count() == 9


def test_create_invalid_stage(db_session):
    from app.errors import InvalidError
    from app.services import project_service as ps

    with pytest.raises(InvalidError):
        ps.create_project(db_session, ProjectCreate(name="x", initial_stage="神秘阶段"))


def test_search(db_session):
    from app.services import project_service as ps

    ps.create_project(db_session, ProjectCreate(name="政务云灾备", initial_stage="商机"))
    ps.create_project(db_session, ProjectCreate(name="卫健大模型", initial_stage="商机"))
    ps.create_project(db_session, ProjectCreate(name="园区一期", initial_stage="采购"))
    [p] = ps.search_projects(db_session, keyword="卫健")
    assert p.name == "卫健大模型"
    assert len(ps.search_projects(db_session, stage="采购")) == 1
    assert len(ps.search_projects(db_session)) == 3


def test_update_project(db_session):
    from app.services import project_service as ps

    p = ps.create_project(db_session, ProjectCreate(name="更名前", initial_stage="商机"))
    p2 = ps.update_project(db_session, p.id,
                           ProjectUpdate(name="更名后", contract_amount=500000))
    assert p2.name == "更名后"
    assert p2.contract_amount == 500000
    # 阶段字段不受 update 影响
    assert p2.current_stage == "商机"


def test_change_stage_matrix(db_session):
    from app.errors import InvalidError
    from app.models.entities import StageHistory
    from app.services import project_service as ps

    p = ps.create_project(db_session, ProjectCreate(name="流转", initial_stage="商机"))
    p = ps.change_stage(db_session, p.id, "签约")     # 跳转
    assert p.current_stage == "签约"
    p = ps.change_stage(db_session, p.id, "立项")     # 推进
    p = ps.change_stage(db_session, p.id, "商机")     # 回退
    assert p.current_stage == "商机"
    hist = db_session.query(StageHistory) \
        .filter_by(project_id=p.id).order_by(StageHistory.id).all()
    assert [(h.from_stage, h.to_stage) for h in hist] == \
        [("商机", "签约"), ("签约", "立项"), ("立项", "商机")]
    with pytest.raises(InvalidError):
        ps.change_stage(db_session, p.id, "不存在阶段")
    # 同阶段流转不产生历史
    ps.change_stage(db_session, p.id, "商机")
    assert db_session.query(StageHistory).filter_by(project_id=p.id).count() == 3


def test_get_ledger_complete(db_session):
    from app.schemas.dtos import AcceptanceCreate, PurchaseCreate
    from app.services import project_service as ps
    from app.services.detail_service import (create_acceptance,
                                             create_purchase)

    p = ps.create_project(db_session, ProjectCreate(
        name="一账", initial_stage="采购", contract_amount=1000000))
    create_purchase(db_session, p.id, PurchaseCreate(name="防火墙", amount=1200000))
    create_purchase(db_session, p.id, PurchaseCreate(name="交换机", amount=800000))
    create_acceptance(db_session, p.id, AcceptanceCreate(name="初验", received_amount=300000))

    ledger = ps.get_ledger(db_session, p.id)
    assert ledger.project.id == p.id
    assert [t.name for t in ledger.tree][0] == "商机"
    assert len(ledger.tree) == 9
    assert len(ledger.purchases) == 2
    assert len(ledger.acceptances) == 1
    assert float(ledger.totals.purchase_amount) == 2000000
    assert float(ledger.totals.received_amount) == 300000


def test_ledger_404(db_session):
    from app.errors import NotFoundError
    from app.services import project_service as ps

    with pytest.raises(NotFoundError):
        ps.get_ledger(db_session, 99999)
