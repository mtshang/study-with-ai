from ..infrastructure.preferences_file import settings_path, read_settings, write_settings
from ..repositories import preferences as repository
from common.errors import BusinessError as HTTPException
from ..schemas.preferences import DisplayPreferences

def get_display(user):
    return read_settings(settings_path(user))[1]

def put_display(data, db, user):
    locked = repository.lock_user(db, user)
    if locked is None:
        raise HTTPException(401, '请重新登录')
    path = settings_path(locked)
    document, current = read_settings(path)
    same = data.fontOffset == current.fontOffset and data.compact == current.compact
    if data.version != current.version:
        if same and data.version + 1 == current.version:
            return current
        raise HTTPException(409, '显示设置已在其他页面修改，请重新读取已保存设置后再调整')
    if same:
        return current
    updated = DisplayPreferences(version=current.version + 1, fontOffset=data.fontOffset, compact=data.compact)
    write_settings(path, {**document, 'display': updated.model_dump()})
    return updated
