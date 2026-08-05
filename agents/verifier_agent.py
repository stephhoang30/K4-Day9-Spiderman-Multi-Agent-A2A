from typing import Dict, Any
import json
import config

try:
    from services.llm import generate_completion
except Exception:
    generate_completion = None


class VerifierAgent:
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm and getattr(config, 'MODEL_NAME', None) is not None and generate_completion is not None

    def _deterministic(self, output: Dict[str, Any]) -> (bool, str):
        try:
            aids = output.get('affected_entities', {})
            if len(aids.get('order_ids', [])) > 5:
                return False, 'too_many_order_ids'
            if len(aids.get('item_ids', [])) > 5:
                return False, 'too_many_item_ids'
            if len(aids.get('seller_ids', [])) > 3:
                return False, 'too_many_seller_ids'
            if len(output.get('evidence_ids', [])) > 20:
                return False, 'too_many_evidence'
            conf = output.get('case_assessment', {}).get('confidence')
            if conf is None or conf < 0 or conf > 1:
                return False, 'invalid_confidence'
        except Exception as e:
            return False, f'verifier_exception:{e}'
        return True, 'ok'

    def verify(self, output: Dict[str, Any]) -> (bool, str):
        if not self.use_llm:
            return self._deterministic(output)
        prompt = {'task': 'verify_output', 'output': output}
        try:
            raw = generate_completion(json.dumps(prompt), model=getattr(config, 'MODEL_NAME', None))
            parsed = json.loads(raw)
            ok = parsed.get('ok')
            reason = parsed.get('reason', 'llm_verification')
            if isinstance(ok, bool):
                return ok, reason
        except Exception:
            pass
        return self._deterministic(output)
