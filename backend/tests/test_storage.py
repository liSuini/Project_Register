import io


def test_save_returns_uuid_path_keeps_original_name(tmp_path):
    from app.services.storage import LocalFilesystemStorage

    st = LocalFilesystemStorage(tmp_path)
    f = io.BytesIO(b"hello attachment")
    sf = st.save(f, "合同扫描件 v1.pdf", 42)
    assert sf.original_name == "合同扫描件 v1.pdf"
    assert sf.stored_path.startswith("42/")
    assert sf.size == len(b"hello attachment")
    assert not sf.stored_path.endswith("合同扫描件 v1.pdf")   # 物理名是 uuid
    assert (tmp_path / sf.stored_path).exists()


def test_open_path_blocks_traversal(tmp_path):
    from app.services.storage import LocalFilesystemStorage, StorageError

    st = LocalFilesystemStorage(tmp_path)
    sf = st.save(io.BytesIO(b"x"), "a.txt", 1)
    ok = st.open_path(sf.stored_path)
    assert ok.exists()
    try:
        st.open_path("../evil.txt")
        raise AssertionError("应当拒绝路径穿越")
    except StorageError:
        pass


def test_remove_tolerates_missing(tmp_path):
    from app.services.storage import LocalFilesystemStorage

    st = LocalFilesystemStorage(tmp_path)
    sf = st.save(io.BytesIO(b"x"), "a.txt", 1)
    st.remove(sf.stored_path)
    assert not (tmp_path / sf.stored_path).exists()
    st.remove(sf.stored_path)      # 再删一次不报错
