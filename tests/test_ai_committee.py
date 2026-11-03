import json
from types import SimpleNamespace

import pytest

from conftest import make_ohlcv, make_signal
from tradingbot.ai_committee import FALLBACK_BETA, InvestmentCommittee, build_market_context
from tradingbot.config import AISettings, CostSettings
from tradingbot.costs import CostModel
from tradingbot.risk import TradePlan

GOOD = {"decision": "APPROVE", "win_probability": 0.62, "stop_loss": 98.0, "take_profit": 104.5,
        "confidence": "high", "risk_flags": [], "rationale": "Ruptura con volumen."}


def response(text, stop_reason="end_turn", iterations=None, model="claude-opus-5-5", inp=2000, out=1000):
    usage = SimpleNamespace(input_tokens=inp, output_tokens=out, cache_creation_input_tokens=0,
                            cache_read_input_tokens=0, iterations=iterations)
    content = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(content=content, stop_reason=stop_reason, usage=usage, model=model,
                           stop_details=SimpleNamespace(category="cyber") if stop_reason == "refusal" else None)


class FakeMessages:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.calls = resp, exc, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        return self.resp


def committee(resp=None, exc=None, **ai_overrides):
    beta, std = FakeMessages(resp, exc), FakeMessages(resp, exc)
    client = SimpleNamespace(messages=std, beta=SimpleNamespace(messages=beta))
    return InvestmentCommittee(AISettings(**ai_overrides), client=client), beta, std


def review(c):
    df = make_ohlcv()
    plan = TradePlan("BTC/USDT", "long", 100.0, 98.0, 104.0, 10.0, 1000.0, 22.0, 2.0)
    costs = CostModel(CostSettings()).evaluate(entry_price=100, stop_loss=98, take_profit=104, quantity=10,
                                               maker_fee=0.001, taker_fee=0.001, ai_cost=0.1)
    return c.review_entry(signal=make_signal(df=df), plan=plan, costs=costs,
                          market_context=build_market_context(df), constraints={"stop_loss_min": 96.0},
                          environment="TESTNET")


def test_entry_review_request_shape_and_cost():
    c, beta, std = committee(response(json.dumps(GOOD)))
    result = review(c)
    assert result.approved and result.verdict.win_probability == pytest.approx(0.62)
    # 2000 * $4/M + 1000 * $20/M
    assert result.cost_usd == pytest.approx(0.028)
    assert not std.calls and len(beta.calls) == 1
    call = beta.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["betas"] == [FALLBACK_BETA] and call["fallbacks"] == "default"
    assert call["thinking"] == {"type": "adaptive"}
    assert call["output_config"]["effort"] == "medium"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert not {"temperature", "top_p", "top_k"} & call.keys()
    payload = json.loads(call["messages"][0]["content"])
    assert payload["symbol"] == "BTC/USDT" and "costs_usd" in payload and "constraints" in payload


def test_without_server_fallbacks_uses_standard_endpoint():
    c, beta, std = committee(response(json.dumps(GOOD)), use_server_fallbacks=False)
    assert review(c).approved
    assert len(std.calls) == 1 and not beta.calls
    assert "fallbacks" not in std.calls[0]


def test_refusal_fails_closed():
    result = review(committee(response("", stop_reason="refusal"))[0])
    assert not result.ok and not result.approved and "declinó" in result.error


def test_truncated_response_fails_closed():
    result = review(committee(response('{"decision": "APP', stop_reason="max_tokens"))[0])
    assert not result.ok and "truncada" in result.error


@pytest.mark.parametrize("text", ["no es json", json.dumps({**GOOD, "win_probability": 1.7}),
                                  json.dumps({k: v for k, v in GOOD.items() if k != "stop_loss"})])
def test_invalid_payload_fails_closed(text):
    result = review(committee(response(text))[0])
    assert not result.ok and "JSON inválido" in result.error
    assert result.cost_usd > 0  # la consulta igual se contabiliza


def test_connection_error_fails_closed():
    import anthropic
    import httpx2
    exc = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    result = review(committee(exc=exc)[0])
    assert not result.ok and result.cost_usd == 0.0


def test_fallback_iterations_priced_per_model():
    iterations = [
        SimpleNamespace(type="message", model=None, input_tokens=1000, output_tokens=0,
                        cache_creation_input_tokens=0, cache_read_input_tokens=0),
        SimpleNamespace(type="fallback_message", model="claude-opus-5", input_tokens=1000, output_tokens=1000,
                        cache_creation_input_tokens=0, cache_read_input_tokens=0),
    ]
    c, *_ = committee(response(json.dumps(GOOD), iterations=iterations, model="claude-opus-5"))
    # 1000*$4/M (Opus 5.5) + 1000*$5/M + 1000*$25/M (Opus 5)
    assert review(c).cost_usd == pytest.approx(0.034)


def test_exit_review():
    text = json.dumps({"decision": "CLOSE", "risk_flags": ["ruptura"], "rationale": "Tendencia rota."})
    c, beta, _ = committee(response(text))
    df = make_ohlcv()
    pos = {"symbol": "BTC/USDT", "entry_price": 100.0, "stop_loss": 98.0, "take_profit": 104.0, "quantity": 1.0}
    result = c.review_exit(position=pos, last_price=99.0, alert="ruptura", indicators={"rsi": 40.0},
                           market_context=build_market_context(df), exit_cost_usd=0.15)
    assert result.ok and result.verdict.decision == "CLOSE"
    assert beta.calls[0]["output_config"]["format"]["schema"]["properties"]["decision"]["enum"] == ["HOLD", "CLOSE"]


def test_estimated_call_cost_from_settings():
    c, *_ = committee(None, estimated_input_tokens=2500, estimated_output_tokens=3000)
    assert c.estimated_call_cost() == pytest.approx(2500 * 4 / 1e6 + 3000 * 20 / 1e6)
