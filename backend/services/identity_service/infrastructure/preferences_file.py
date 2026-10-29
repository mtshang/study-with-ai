import json,os,tempfile
from pathlib import Path
from pydantic import ValidationError
from common.errors import BusinessError as HTTPException
from common.storage import user_path
from . import config
from ..schemas.preferences import DisplayPreferences


def settings_path(user):
    base = user_path(config.settings.user_root, user.storage_dir)
    path = base / 'settings.json'
    if path.is_symlink() or path.resolve().parent != base:
        raise HTTPException(503, '个人设置文件不可用')
    return path

def read_settings(path):
    try:
        with path.open('rb') as f:
            raw = f.read(16385)
        if len(raw) > 16384:
            raise ValueError('Settings too large')
        document = json.loads(raw)
        if not isinstance(document, dict):
            raise ValueError('Expected object')
        value = DisplayPreferences.model_validate(document.get('display', {}))
        return (document, value)
    except (OSError, ValueError, ValidationError):
        raise HTTPException(503, '个人设置读取失败，原文件已保留，请检查文件后重试') from None

def write_settings(path: Path, document):
    temporary = None
    try:
        content = json.dumps(document, ensure_ascii=False, indent=2).encode('utf-8') + b'\n'
        if len(content) > 16384:
            raise ValueError('Settings too large')
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, prefix='.settings-', suffix='.tmp', delete=False) as f:
            temporary = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    except (OSError, ValueError):
        raise HTTPException(503, '个人设置保存失败，请重试') from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass