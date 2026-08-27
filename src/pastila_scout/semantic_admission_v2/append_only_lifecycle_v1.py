"""Append-only lifecycle events for evaluation-only subprocess evidence."""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import UTC,datetime
from pathlib import Path


class AppendOnlyLifecycleV1:
    def __init__(self,root:Path,*,actor:str)->None:
        if not actor or not actor.replace("-","").isalnum(): raise ValueError("invalid lifecycle actor")
        self.root=root;self.actor=actor;self._sequence=0
        self.root.mkdir(parents=True,exist_ok=True)

    def emit(self,event:str,**fields:object)->Path:
        self._sequence+=1
        value={"actor":self.actor,"sequence":self._sequence,"event":event,"recorded_at":datetime.now(UTC).isoformat(),
            "monotonic_seconds":time.monotonic(),**fields}
        path=self.root/f"{self.actor}-{self._sequence:05d}-{event.lower().replace('_','-')}.json"
        data=(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")
        with path.open("xb") as handle:
            handle.write(data);handle.flush();os.fsync(handle.fileno())
        return path


def run_synthetic_timeout_probe_v1(*,command:list[str],root:Path,timeout_seconds:float)->str:
    """Exercise durable timeout evidence without WSL, provider, tokenizer, or model."""
    events=AppendOnlyLifecycleV1(root,actor="synthetic")
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    events.emit("PROCESS_STARTED",pid=process.pid)
    try:
        process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        events.emit("TIMEOUT",pid=process.pid)
        process.terminate();termination="TERMINATED"
        try: process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate();termination="KILLED"
        events.emit("TERMINATION_OBSERVED",pid=process.pid,termination=termination,returncode=process.returncode)
        return termination
    raise AssertionError("synthetic timeout probe unexpectedly completed")


__all__=("AppendOnlyLifecycleV1","run_synthetic_timeout_probe_v1")
