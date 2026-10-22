from fastapi import Request

from app.services.storage import LocalFilesystemStorage


def get_storage(request: Request) -> LocalFilesystemStorage:
    return request.app.state.storage
