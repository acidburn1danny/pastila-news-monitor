#!/usr/bin/env python3
from pathlib import PurePosixPath
MANAGED_ROOTS=('app','config','contracts','foundation','manifest')
AUTHORIZED_COMPONENT_PATHS=('components/editor-r2','platform/python-ml')
DECLARED_ALLOWED=('state/*.sqlite3-wal','state/*.sqlite3-shm')
MANAGED='MANAGED';ALLOWED_REGENERABLE_RUNTIME='ALLOWED_REGENERABLE_RUNTIME';MUTABLE_STATE='MUTABLE_STATE';FORBIDDEN='FORBIDDEN'
def normalize(value):
 if not isinstance(value,str) or not value or '\\' in value or value.startswith('/') or '\x00' in value:raise ValueError('unsafe path')
 p=PurePosixPath(value)
 if any(x in ('','.', '..') for x in p.parts):raise ValueError('unsafe path')
 n=p.as_posix()
 if n!=value:raise ValueError('ambiguous path')
 return n,p.parts
def classify(value,is_symlink=False):
 try:n,parts=normalize(value)
 except ValueError:return FORBIDDEN
 if is_symlink or n.endswith('.pyc') or '__pycache__' in parts:return FORBIDDEN
 if n=='product-lock.json':return MANAGED
 if parts[0] in ('components','platform'):
  return MANAGED if any(n==x or n.startswith(x+'/') for x in AUTHORIZED_COMPONENT_PATHS) else FORBIDDEN
 if parts[0] in MANAGED_ROOTS:return MANAGED
 if n=='state/product.sqlite3':return MUTABLE_STATE
 if n in ('state/product.sqlite3-wal','state/product.sqlite3-shm'):return ALLOWED_REGENERABLE_RUNTIME
 return FORBIDDEN
def application_inventory_class(value,is_symlink=False):return classify(value,is_symlink)
