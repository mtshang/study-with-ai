"""One-off copy into EMPTY service databases. Stop writers and take a backup first.
The original schema and user files are preserved. Never use this to merge active databases.
"""
import uuid
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine,URL,MetaData,Table,select,func
from common.config import ROOT
from dotenv import dotenv_values
from services.identity_service.infrastructure.database import engine as identity_engine
from services.learning_service.infrastructure.database import engine as learning_engine
from services.identity_service.models import Base as IdentityBase
from services.learning_service.models import Base as LearningBase,CourseChange

def main():
    values=dotenv_values(ROOT/'.env')
    source=create_engine(URL.create('mysql+pymysql',username=values.get('MYSQL_USER','study_app'),password=values['MYSQL_PASSWORD'],
        host=values.get('MYSQL_HOST','127.0.0.1'),port=int(values.get('MYSQL_PORT',3306)),database=values.get('MYSQL_DATABASE','study_with_ai')),
        hide_parameters=True)
    plans=[(identity_engine,IdentityBase,['users','login_sessions']),
           (learning_engine,LearningBase,['courses','chapters','course_revisions','activities','submissions','materials'])]
    for engine,base,names in plans:
        if engine.url.database==source.url.database: raise RuntimeError('Target must differ from legacy database')
        with engine.connect() as conn:
            for name in names+(['course_changes'] if base is LearningBase else []):
                if conn.scalar(select(func.count()).select_from(base.metadata.tables[name])):
                    raise RuntimeError('Target contains data; import refuses to overwrite or merge')
    counts={}
    with source.connect().execution_options(isolation_level='REPEATABLE READ') as old:
        old.exec_driver_sql('SET TRANSACTION READ ONLY')
        for engine,base,names in plans:
            with engine.begin() as new:
                for name in names:
                    table=Table(name,MetaData(),autoload_with=old)
                    rows=[dict(row) for row in old.execute(select(table)).mappings()]
                    if name=='courses':
                        for row in rows: row['change_seq']=1
                    if rows: new.execute(base.metadata.tables[name].insert(),rows)
                    counts[name]=len(rows)
                if base is LearningBase:
                    courses=list(new.execute(select(base.metadata.tables['courses'])).mappings())
                    if courses:
                        new.execute(CourseChange.__table__.insert(),[
                            dict(id=str(uuid.uuid4()),course_id=c['id'],sequence=1,course_version=c['version'],
                                 actor_id=c['owner_id'],kind='migration.baseline',target_id=c['id'],
                                 summary='旧系统迁移：以当前状态建立变更基线') for c in courses])
                # Compare every preserved value, not just row counts.
                for name in names:
                    table=Table(name,MetaData(),autoload_with=old)
                    columns=list(table.c.keys())
                    def canonical(row): return repr(sorted(dict(row).items()))
                    before=sorted(canonical(r) for r in old.execute(select(table)).mappings())
                    # Reflect both sides so MySQL BOOLEAN/TINYINT values compare with
                    # the same conversion rules rather than Python bool vs int repr.
                    target=Table(name,MetaData(),autoload_with=new)
                    after=sorted(canonical(r) for r in new.execute(select(*(target.c[c] for c in columns))).mappings())
                    if before!=after: raise RuntimeError(f'Imported data mismatch: {name}')
    source.dispose()
    print('Copied and verified preserved rows:',counts)
if __name__=='__main__': main()
