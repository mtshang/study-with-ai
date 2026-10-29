"""Bounded Skill packages; imported instructions never grant tool authority.

Design reference: DeerFlow skills/installer.py and frontmatter.py. This
implementation keeps a normalized ZIP instead of extracting uploaded paths.
"""
import hashlib
import io
import re
import stat
import zipfile
from pathlib import PurePosixPath
import yaml
from fastapi import HTTPException

MAX_UPLOAD = 10 * 1024 * 1024
MAX_TOTAL = 20 * 1024 * 1024
MAX_FILE = 5 * 1024 * 1024
MAX_ENTRIES = 256


def fail(message):
    raise HTTPException(422, message)


def safe_name(name):
    if not name or len(name) > 240 or '\\' in name or ':' in name or '\x00' in name:
        fail('技能包路径不合法')
    parts = name.rstrip('/').split('/')
    if any(not p or p in ('.', '..') or p.endswith((' ', '.')) for p in parts):
        fail('技能包不能包含绝对路径或上级目录')
    if any(re.fullmatch(r'(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p, re.I) for p in parts):
        fail('技能包包含保留的文件名')
    return '/'.join(parts)


class MetadataLoader(yaml.SafeLoader):
    """No aliases, duplicate keys or object constructors in small metadata."""
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            fail('技能元数据不支持 YAML 别名')
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        result = {}
        for k, v in node.value:
            key = self.construct_object(k, deep=deep)
            if not isinstance(key, str) or key in result:
                fail('技能元数据键必须是唯一字符串')
            result[key] = self.construct_object(v, deep=deep)
        return result


def metadata(raw):
    try:
        text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    except UnicodeError:
        fail('SKILL.md 必须使用 UTF-8 编码')
    if len(raw) > 128 * 1024:
        fail('SKILL.md 超过 128KB 限制')
    match = re.match(r'\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)', text, re.S)
    if not match or len(match[1]) > 8192:
        fail('SKILL.md 需要不超过 8KB 的 YAML 元数据')
    try:
        meta = yaml.load(match[1], Loader=MetadataLoader)
    except (yaml.YAMLError, RecursionError):
        fail('技能 YAML 元数据无法解析')
    if not isinstance(meta, dict):
        fail('技能元数据必须是对象')
    name, description = meta.get('name'), meta.get('description')
    if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) > 64:
        fail('技能 name 使用小写英文字母、数字和单个连字符，最多64字符')
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= 1024:
        fail('技能 description 必须是1–1024字符的文字')
    body = text[match.end():].strip()
    if not body:
        fail('技能正文不能为空')
    return {'name': name, 'description': description.strip(),
            'license': str(meta.get('license', ''))[:300],
            'compatibility': str(meta.get('compatibility', ''))[:500]}, text


def normalize(raw, filename):
    if not raw or len(raw) > MAX_UPLOAD:
        fail('技能文件不能为空，上传最多10MB')
    files = {}
    if filename.lower().endswith('.md'):
        files['SKILL.md'] = raw
    elif filename.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                infos = archive.infolist()
                if len(infos) > MAX_ENTRIES:
                    fail('技能包最多包含256个条目')
                total, seen = 0, set()
                for info in infos:
                    path = safe_name(info.orig_filename)
                    folded = path.casefold()
                    if folded in seen:
                        fail('技能包包含重复或仅大小写不同的路径')
                    seen.add(folded)
                    mode = info.external_attr >> 16
                    if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                        fail('技能包不允许链接或特殊文件')
                    if info.flag_bits & 1:
                        fail('技能包不支持加密文件')
                    if info.is_dir():
                        continue
                    if info.file_size > MAX_FILE:
                        fail('技能包单文件最多5MB')
                    with archive.open(info) as f:
                        content = f.read(MAX_FILE + 1)
                    total += len(content)
                    if len(content) > MAX_FILE or total > MAX_TOTAL:
                        fail('技能包解压内容超过限制')
                    files[path] = content
        except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError):
            fail('无法读取技能 ZIP 文件')
    else:
        fail('请上传 .md 或 .zip 技能包')
    roots = [p for p in files if p == 'SKILL.md' or p.endswith('/SKILL.md')]
    if len(roots) != 1:
        fail('一个导入包必须且只能包含一个 SKILL.md')
    prefix = roots[0][:-len('SKILL.md')]
    if any(not p.startswith(prefix) for p in files):
        fail('所有文件必须位于技能根目录内')
    files = {p[len(prefix):]: b for p, b in files.items()}
    meta, _ = metadata(files['SKILL.md'])
    # Logical paths stay inside the archive; real storage paths are generated IDs.
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, content in sorted(files.items()):
            archive.writestr(zipfile.ZipInfo(path, (1980, 1, 1, 0, 0, 0)), content, compress_type=zipfile.ZIP_DEFLATED)
    package = output.getvalue()
    manifest = [{'path': p, 'size': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
                 'script': p.startswith('scripts/')} for p, b in sorted(files.items())]
    return package, {**meta, 'files': manifest, 'sha256': hashlib.sha256(package).hexdigest()}


def read_text(package, path, offset=0):
    path = safe_name(path)
    if PurePosixPath(path).suffix.lower() not in ('.md', '.txt', '.json', '.yaml', '.yml', '.csv', '.py', '.js', '.ts'):
        fail('当前只读取技能包内文本文件，不执行脚本或解析二进制附件')
    try:
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            data = archive.read(path)
        text = data.decode('utf-8-sig')
    except KeyError:
        raise HTTPException(404, '技能文件不存在') from None
    except UnicodeError:
        fail('该文件不是 UTF-8 文本')
    if offset < 0 or offset > len(text):
        fail('读取位置超出范围')
    return {'path': path, 'text': text[offset:offset+12000], 'offset': offset,
            'next_offset': min(len(text), offset+12000), 'total': len(text),
            'sha256': hashlib.sha256(data).hexdigest()}
