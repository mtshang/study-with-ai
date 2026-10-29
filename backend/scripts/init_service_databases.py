"""Initialize local Docker MySQL service databases; preserve existing config and records."""
from pathlib import Path
import argparse
import os
import secrets
import shutil
import subprocess
import re
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test',action='store_true',help='Create only the dedicated service test databases')
    args=parser.parse_args()
    source=ROOT/'.env'
    if not source.is_file(): raise SystemExit('Configure root .env for Docker MySQL first')
    config=ROOT/('.env.services.test' if args.test else '.env.services')
    if not config.exists():
        values={'INTERNAL_SERVICE_KEY':secrets.token_hex(32)}
        for name in ['identity','learning','ai']:
            database=f'study_{name}'+('_test' if args.test else '')
            values.update({f'{name.upper()}_MYSQL_DATABASE':database,f'{name.upper()}_MYSQL_USER':database,
                           f'{name.upper()}_MYSQL_PASSWORD':secrets.token_hex(24)})
        # Exclusive creation: do not overwrite an existing credentials file.
        with config.open('x',encoding='utf-8') as file:
            file.write(source.read_text(encoding='utf-8')+'\n# Service database configuration; ignored by Git.\n')
            file.write('\n'.join(f'{key}={value}' for key,value in values.items())+'\n')
    values=dotenv_values(config)
    statements=[]
    for name in ['identity','learning','ai']:
        database=values[f'{name.upper()}_MYSQL_DATABASE'];user=values[f'{name.upper()}_MYSQL_USER'];password=values[f'{name.upper()}_MYSQL_PASSWORD']
        expected=f'study_{name}'+('_test' if args.test else '')
        if database!=expected or user!=expected: raise SystemExit('Unexpected database/user name; provision custom deployments separately')
        if not password or not re.fullmatch(r'[A-Za-z0-9_-]{24,128}',password):
            raise SystemExit('Local initializer expects generated alphanumeric credentials')
        statements.extend([f'CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4;',
            f"CREATE USER IF NOT EXISTS '{user}'@'%' IDENTIFIED BY '{password}';",
            f"GRANT ALL PRIVILEGES ON `{database}`.* TO '{user}'@'%';"])
    docker=shutil.which('docker')
    if not docker: raise SystemExit('Docker CLI not found')
    result=subprocess.run([docker,'compose','exec','-T','mysql','sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot'],
                          cwd=ROOT,input='\n'.join(statements).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode: raise SystemExit('Database initialization failed; configuration retained. No secret output printed.')
    print('Service databases provisioned. Existing passwords and records are not changed.')

if __name__=='__main__': main()
