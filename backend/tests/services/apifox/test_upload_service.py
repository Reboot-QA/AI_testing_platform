"""Apifox 上传文件（Binary body）· 创建限大小 / 取字节回调项目隔离。"""

import pytest

from app.services.apifox import upload_service as svc


def _create(db, project_id=1, data=b"hello", filename="f.bin", content_type="application/octet-stream"):
    return svc.create_upload(db, project_id, filename, content_type, data)


def test_create_persists_metadata_and_size(db):
    out = _create(db, data=b"abc", filename="x.png", content_type="image/png")

    assert out.filename == "x.png"
    assert out.content_type == "image/png"
    assert out.size == 3


def test_create_empty_data_rejected(db):
    with pytest.raises(ValueError, match="为空"):
        _create(db, data=b"")


def test_create_over_size_limit_rejected(db):
    with pytest.raises(ValueError, match="上限"):
        _create(db, data=b"x" * (svc.MAX_UPLOAD_BYTES + 1))


def test_binary_loader_returns_bytes_and_content_type_for_owned_file(db):
    out = _create(db, project_id=1, data=b"payload", content_type="text/plain")
    loader = svc.make_binary_loader(db, project_id=1)

    assert loader(out.id) == (b"payload", "text/plain")


def test_binary_loader_isolates_cross_project(db):
    out = _create(db, project_id=2, data=b"secret")
    loader = svc.make_binary_loader(db, project_id=1)

    assert loader(out.id) is None


def test_binary_loader_missing_file_returns_none(db):
    loader = svc.make_binary_loader(db, project_id=1)

    assert loader(99999) is None
