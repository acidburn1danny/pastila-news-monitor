"""Independent durable generation-wait and callback timing receipts."""
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path

from .append_only_lifecycle_v1 import AppendOnlyLifecycleV1


class StagePGenerationCallbackHeartbeatV1:
    def __init__(self, *, lifecycle_root:Path, interval_seconds:float=10.0)->None:
        if interval_seconds<=0:raise ValueError("HEARTBEAT_INTERVAL_INVALID")
        self.events=AppendOnlyLifecycleV1(lifecycle_root,actor="runner-heartbeat")
        self.interval_seconds=interval_seconds;self._stop=threading.Event();self._thread=None
        self._started=0.0;self.callback_count=0;self.generated_tokens=0

    def start(self)->None:
        if self._thread is not None:raise RuntimeError("HEARTBEAT_ALREADY_STARTED")
        self._started=time.monotonic();self.events.emit("GENERATION_WAIT_STARTED")
        self._thread=threading.Thread(target=self._loop,name="stage-p-heartbeat",daemon=True);self._thread.start()

    def _loop(self)->None:
        while not self._stop.wait(self.interval_seconds):
            self.events.emit("GENERATION_WAIT_HEARTBEAT",elapsed_seconds=round(time.monotonic()-self._started,6),
                callback_count=self.callback_count,generated_tokens=self.generated_tokens)

    def callback(self, *, generated_ids:list[int], elapsed_seconds:float,
                 allowed_token_count:int, dfa_mode:str, decoded:str)->None:
        self.callback_count+=1;self.generated_tokens=len(generated_ids)
        self.events.emit("TOKEN_CALLBACK_COMPLETED",callback_count=self.callback_count,
            generated_tokens=self.generated_tokens,callback_seconds=round(elapsed_seconds,6),
            allowed_token_count=allowed_token_count,dfa_mode=dfa_mode,
            decoded_sha256=hashlib.sha256(decoded.encode()).hexdigest(),
            decoded_utf8_bytes=len(decoded.encode()))

    def stop(self, *, outcome:str)->None:
        self._stop.set()
        if self._thread is not None:self._thread.join(timeout=max(1.0,self.interval_seconds*2))
        self.events.emit("GENERATION_WAIT_STOPPED",outcome=outcome,
            elapsed_seconds=round(time.monotonic()-self._started,6),
            callback_count=self.callback_count,generated_tokens=self.generated_tokens)


__all__=("StagePGenerationCallbackHeartbeatV1",)
