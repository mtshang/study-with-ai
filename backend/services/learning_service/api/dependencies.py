from fastapi import Depends,Request
from common.identity import resolve_principal,require_workspace
def workspace_user(request: Request,user=Depends(resolve_principal)):
    return require_workspace(request,user)
