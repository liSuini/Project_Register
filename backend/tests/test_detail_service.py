import pytest
from app.schemas.dtos import AcceptanceCreate, PurchaseCreate


@pytest.fixture
def project(db_session):
    from app.models.entities import Project

    p = Project(name="明细测试", initial_stage="采购", current_stage="采购")
    db_session.add(p)
    db_session.commit()
    return p


def test_purchase_crud_and_sum(db_session, project):
    from app.services import detail_service as ds

    ds.create_purchase(db_session, project.id,
                       PurchaseCreate(name="防火墙", supplier="华为", amount=1200000))
    ds.create_purchase(db_session, project.id,
                       PurchaseCreate(name="交换机", supplier="新华三", amount=800000))
    rows = ds.list_purchases(db_session, project.id)
    assert len(rows) == 2
    assert sum(r.amount for r in rows) == 1200000 + 800000
    ds.delete_purchase(db_session, rows[0].id)
    assert len(ds.list_purchases(db_session, project.id)) == 1


def test_acceptance_crud_and_update(db_session, project):
    from app.services import detail_service as ds
    from app.schemas.dtos import AcceptanceUpdate

    ds.create_acceptance(db_session, project.id,
                         AcceptanceCreate(name="初验", received_amount=300000))
    rows = ds.list_acceptances(db_session, project.id)
    assert float(rows[0].received_amount) == 300000
    ds.update_acceptance(db_session, rows[0].id,
                         AcceptanceUpdate(received_amount=350000))
    assert float(ds.list_acceptances(db_session, project.id)[0].received_amount) == 350000
    ds.delete_acceptance(db_session, rows[0].id)
    assert ds.list_acceptances(db_session, project.id) == []


def test_negative_amount_rejected(db_session, project):
    from app.errors import InvalidError
    from app.services import detail_service as ds

    with pytest.raises(InvalidError):
        ds.create_purchase(db_session, project.id,
                           PurchaseCreate(name="x", amount=-1))
    with pytest.raises(InvalidError):
        ds.create_acceptance(db_session, project.id,
                             AcceptanceCreate(name="y", received_amount=-5))


def test_project_must_exist(db_session):
    from app.errors import NotFoundError
    from app.services import detail_service as ds

    with pytest.raises(NotFoundError):
        ds.create_purchase(db_session, 99999, PurchaseCreate(name="x"))
    with pytest.raises(NotFoundError):
        ds.list_acceptances(db_session, 99999)
