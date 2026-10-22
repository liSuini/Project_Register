from datetime import date
from decimal import Decimal


def test_model_roundtrip(db_session):
    from app.models.entities import (AcceptanceRecord, Attachment, Node,
                                     Project, PurchaseOrder, StageHistory)
    p = Project(name="测试项目", customer="某客户", initial_stage="商机",
                current_stage="商机", contract_amount=Decimal("1000000.00"))
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    anchor = Node(project_id=p.id, parent_id=None, name="商机", stage_key="商机")
    sub = Node(project_id=p.id, parent_id=None, name="子环节", stage_key=None)
    db_session.add_all([anchor, sub])
    db_session.commit()

    db_session.add(Attachment(node_id=sub.id, original_name="合同.pdf",
                              stored_path=f"{p.id}/abc.pdf", size=100,
                              mime="application/pdf"))
    db_session.add(PurchaseOrder(project_id=p.id, name="服务器", supplier="华为",
                                 amount=Decimal("1200000.00"),
                                 order_date=date(2026, 10, 1)))
    db_session.add(AcceptanceRecord(project_id=p.id, name="初验",
                                    acceptance_date=date(2026, 10, 20),
                                    received_amount=Decimal("300000.00")))
    db_session.add(StageHistory(project_id=p.id, from_stage="商机", to_stage="中标"))
    db_session.commit()

    assert db_session.query(Project).count() == 1
    assert db_session.query(Node).count() == 2
    assert db_session.get(Attachment, 1).original_name == "合同.pdf"
    assert db_session.query(PurchaseOrder).first().amount == Decimal("1200000.00")
    assert db_session.query(AcceptanceRecord).count() == 1
    assert db_session.query(StageHistory).count() == 1


def test_dto_project_out_from_orm(db_session):
    from app.models.entities import Project
    from app.schemas.dtos import ProjectOut

    db_session.add(Project(name="DTO测试", initial_stage="签约", current_stage="签约"))
    db_session.commit()
    p = db_session.query(Project).first()
    out = ProjectOut.model_validate(p)
    assert out.name == "DTO测试"
    assert out.initial_stage == "签约"
    assert out.contract_amount == 0
