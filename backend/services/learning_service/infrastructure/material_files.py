import uuid,unicodedata
from common.storage import user_path
from common.errors import BusinessError as HTTPException
from . import config


def file_location(user, course_id, material_id):
    base = user_path(config.settings.user_root, user.storage_dir)
    path = base / 'courses' / str(uuid.UUID(str(course_id))) / 'materials' / (str(uuid.UUID(str(material_id))) + '.blob')
    if not path.resolve().is_relative_to(base):
        raise HTTPException(503, '资料目录不可用')
    return path

def display_filename(name):
    name = (name or 'file').replace('\\', '/').split('/')[-1]
    name = ''.join((c for c in name if not unicodedata.category(c).startswith('C'))).strip().strip('.')
    return (name or 'file')[:200]