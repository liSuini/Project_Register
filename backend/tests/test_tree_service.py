import pytest


@pytest.fixture
def project(db_session):
    from app.models.entities import Project

    p = Project(name="树测试", initial_stage="采购", current_stage="采购")
    db_session.add(p)
    db_session.commit()
    return p


def test_create_tree_nine_anchors(db_session, project):
    from app.core.constants import STAGES
    from app.services.tree_service import create_project_tree, get_tree

    create_project_tree(db_session, project.id)
    tree = get_tree(db_session, project.id)
    assert [t.name for t in tree] == STAGES            # 顺序=生命周期顺序
    assert all(t.is_anchor for t in tree)
    assert all(t.attachment_count == 0 for t in tree)


def test_add_and_nest_node(db_session, project):
    from app.services.tree_service import add_node, create_project_tree, get_tree

    create_project_tree(db_session, project.id)
    anchor = get_tree(db_session, project.id)[4]       # 采购锚点
    sub = add_node(db_session, anchor.id, "硬件采购")
    subsub = add_node(db_session, sub.id, "二标段")
    assert sub.project_id == subsub.project_id == project.id
    tree = get_tree(db_session, project.id)
    buy = tree[4]
    assert buy.children[0].name == "硬件采购"
    assert buy.children[0].children[0].name == "二标段"


def test_rename_anchor_forbidden(db_session, project):
    from app.errors import ConflictError
    from app.models.entities import Node
    from app.services.tree_service import create_project_tree, rename_node

    create_project_tree(db_session, project.id)
    anchor = db_session.query(Node).filter_by(stage_key="采购", project_id=project.id).one()
    with pytest.raises(ConflictError):
        rename_node(db_session, anchor.id, "改名")


def test_delete_rules(db_session, project):
    from app.errors import ConflictError, NotFoundError
    from app.models.entities import Attachment, Node
    from app.services.tree_service import add_node, create_project_tree, delete_node

    create_project_tree(db_session, project.id)
    anchor = db_session.query(Node).filter_by(stage_key="采购", project_id=project.id).one()
    sub = add_node(db_session, anchor.id, "硬件采购")
    child = add_node(db_session, sub.id, "二标段")

    with pytest.raises(ConflictError):    # 锚点不可删
        delete_node(db_session, anchor.id)
    with pytest.raises(ConflictError):    # 有子环节禁删
        delete_node(db_session, sub.id)
    delete_node(db_session, child.id)     # 清掉子环节
    db_session.add(Attachment(node_id=sub.id, original_name="x.pdf",
                              stored_path="1/x.pdf", size=1))
    db_session.commit()
    with pytest.raises(ConflictError):    # 有附件禁删
        delete_node(db_session, sub.id)
    db_session.query(Attachment).filter_by(node_id=sub.id).delete()
    db_session.commit()
    delete_node(db_session, sub.id)       # 清空后可删
    with pytest.raises(NotFoundError):    # 不存在的节点
        delete_node(db_session, 99999)


def test_add_node_missing_parent_404(db_session, project):
    from app.errors import NotFoundError
    from app.services.tree_service import add_node

    with pytest.raises(NotFoundError):
        add_node(db_session, 99999, "无父")


def test_attachment_count_in_tree(db_session, project):
    from app.models.entities import Attachment, Node
    from app.services.tree_service import add_node, create_project_tree, get_tree

    create_project_tree(db_session, project.id)
    anchor = db_session.query(Node).filter_by(
        stage_key="采购", project_id=project.id).one()
    sub = add_node(db_session, anchor.id, "硬件")
    db_session.add_all([
        Attachment(node_id=sub.id, original_name="a.pdf", stored_path="1/a.pdf", size=1),
        Attachment(node_id=sub.id, original_name="b.pdf", stored_path="1/b.pdf", size=2),
    ])
    db_session.commit()
    tree = get_tree(db_session, project.id)
    assert tree[4].children[0].attachment_count == 2
