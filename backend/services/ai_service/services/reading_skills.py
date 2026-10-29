"""Only reviewed, packaged adapters; never execute uploaded Skill scripts."""
import hashlib,json
from pathlib import Path
from fastapi import HTTPException
ROOT=Path(__file__).resolve().parents[4]/'resources/system_skill_mcp/skills'
def catalog():
    data=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    return data['skills']
def load(skill_id):
    entry=next((s for s in catalog() if s['id']==skill_id),None)
    if not entry: raise HTTPException(422,'只允许使用已内置的资料读取技能')
    # Normalize only platform line endings; other content changes invalidate the pin.
    data=(ROOT/entry['id']/'SKILL.md').read_text(encoding='utf-8').encode('utf-8')
    if hashlib.sha256(data).hexdigest()!=entry['sha256']: raise HTTPException(503,'内置技能文件校验失败')
    return {'skill_id':skill_id,'instructions':data.decode('utf-8'),'license':entry['license'],'source':entry['upstream']}
