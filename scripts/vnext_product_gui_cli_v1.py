#!/usr/bin/env python3
"""Single CLI/GUI presentation entry over canonical product startup."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def open_gui(root: Path):
    root=root.resolve(strict=True)
    sys.path.insert(0,str(root/"app/cli"))
    from product import startup
    sys.path.insert(0,str(root/"app/workflow"))
    from pastila_scout.vnext_product_gui_v1 import CanonicalProductGui
    from pastila_scout.vnext_product_orchestrator_v1 import ProductOrchestrator
    from pastila_scout.vnext_state_sqlite_v1 import SQLiteStateStore
    store=SQLiteStateStore(root=root/"state",database=Path("product.sqlite3"),writer_identity="vnext-product-runtime-v1")
    return CanonicalProductGui(product_root=root,orchestrator=ProductOrchestrator(store),canonical_startup=startup)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--workflow",required=True)
    p.add_argument("--format",choices=("json","html"),default="html")
    a=p.parse_args();gui=open_gui(a.root);view=gui.recover(a.workflow)
    if a.format=="json": print(json.dumps(view.as_dict(),sort_keys=True))
    else:
        from pastila_scout.vnext_product_gui_v1 import render_html
        print(render_html(view))
if __name__=="__main__":main()
