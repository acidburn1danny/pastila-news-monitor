from __future__ import annotations
import json,time
from pastila_scout.semantic_admission_v2.stage_p_generation_callback_heartbeat_v1 import StagePGenerationCallbackHeartbeatV1
def test_wait_and_callback_receipts_are_independent_and_durable(tmp_path):
    h=StagePGenerationCallbackHeartbeatV1(lifecycle_root=tmp_path,interval_seconds=.01);h.start();time.sleep(.025)
    h.callback(generated_ids=[1,2],elapsed_seconds=.04,allowed_token_count=7,dfa_mode="STRING",decoded="ab")
    h.stop(outcome="SYNTHETIC_COMPLETE")
    values=[json.loads(path.read_bytes()) for path in sorted(tmp_path.glob("*.json"))]
    events=[value["event"] for value in values]
    assert "GENERATION_WAIT_HEARTBEAT" in events and "TOKEN_CALLBACK_COMPLETED" in events
    callback=next(value for value in values if value["event"]=="TOKEN_CALLBACK_COMPLETED")
    assert callback["callback_seconds"]==.04 and "ab" not in json.dumps(callback)
