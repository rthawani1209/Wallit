"""The assistant's event stream, against a scripted fake of the Claude API."""
import json
from types import SimpleNamespace

import anthropic
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_db
from app.main import app
from app.services import chat, demo, rate_limit


class FakeStream:
    def __init__(self, text, final):
        self.text_stream = iter(text)
        self._final = final

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._final


def scripted_claude(monkeypatch, turns):
    """Each turn is (text_chunks, stop_reason, tool_calls). Records what was sent."""
    sent = []
    queue = list(turns)

    def stream(**kwargs):
        sent.append(kwargs["messages"][:])
        chunks, stop, tools = queue.pop(0)
        content = [SimpleNamespace(type="text", text="".join(chunks))]
        content += [SimpleNamespace(type="tool_use", id=f"tu{i}", name=n, input=a) for i, (n, a) in enumerate(tools)]
        return FakeStream(chunks, SimpleNamespace(stop_reason=stop, content=content))

    fake = SimpleNamespace(messages=SimpleNamespace(stream=stream))
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-test-not-real")
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    return sent


ASK = [{"role": "user", "content": "How much cash do I have?"}]


def test_events_show_each_tool_then_the_streamed_reply(db, monkeypatch):
    user = demo.create_demo_user(db)
    sent = scripted_claude(monkeypatch, [
        (["Let me check."], "tool_use", [("get_account_balances", {})]),
        (["You have ", "**$4,821** in checking."], "end_turn", []),
    ])

    events = list(chat.chat_events(db, user, ASK))

    assert events[0] == {"type": "text", "delta": "Let me check."}
    assert events[1] == {"type": "tool", "name": "get_account_balances", "label": "Read 3 account balances"}
    assert [e["delta"] for e in events if e["type"] == "text"][1:] == ["You have ", "**$4,821** in checking."]
    assert events[-1] == {"type": "done", "message": "You have **$4,821** in checking."}
    # the tool result went back to Claude on the second call
    tool_result = sent[1][-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert "Everyday Checking" in tool_result["content"]


def test_a_failing_tool_is_labelled_and_the_chat_goes_on(db, monkeypatch):
    user = demo.create_demo_user(db)
    scripted_claude(monkeypatch, [
        ([], "tool_use", [("create_savings_goal", {})]),
        (["I need a name for the goal."], "end_turn", []),
    ])

    events = list(chat.chat_events(db, user, ASK))

    assert events[0]["label"] == "Create savings goal failed"
    assert events[-1]["message"] == "I need a name for the goal."


def test_run_chat_returns_just_the_reply(db, monkeypatch):
    user = demo.create_demo_user(db)
    scripted_claude(monkeypatch, [(["Hi ", "there."], "end_turn", [])])
    assert chat.run_chat(db, user, ASK) == "Hi there."


def _parse_sse(body: str) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in body.splitlines() if line.startswith("data: ")]


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    rate_limit.reset_all()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_stream_endpoint_sends_server_sent_events(client, monkeypatch):
    client.post("/api/v1/demo/session")
    scripted_claude(monkeypatch, [
        ([], "tool_use", [("get_account_balances", {})]),
        (["Plenty."], "end_turn", []),
    ])

    r = client.post("/api/v1/chat/stream", json={"messages": ASK})

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "event: tool" in r.text
    events = _parse_sse(r.text)
    assert [e["type"] for e in events] == ["tool", "text", "done"]
    assert events[-1]["message"] == "Plenty."


def test_stream_endpoint_keeps_the_demo_cap(client, db, monkeypatch):
    client.post("/api/v1/demo/session")
    monkeypatch.setattr(demo, "DEMO_CHAT_LIMIT", 0)
    monkeypatch.setattr("app.routers.chat.DEMO_CHAT_LIMIT", 0)
    scripted_claude(monkeypatch, [])  # any Claude call would fail: the queue is empty

    events = _parse_sse(client.post("/api/v1/chat/stream", json={"messages": ASK}).text)

    assert events == [{"type": "done", "message": events[0]["message"]}]
    assert "limit" in events[0]["message"]


def test_stream_endpoint_rejects_a_bad_request(client):
    client.post("/api/v1/demo/session")
    r = client.post("/api/v1/chat/stream", json={"messages": [{"role": "assistant", "content": "hi"}]})
    assert r.status_code == 422


def test_stream_still_ends_with_done_when_something_breaks(client, monkeypatch):
    client.post("/api/v1/demo/session")

    def breaks_partway(db, user, messages):
        yield {"type": "tool", "name": "get_transactions", "label": "Looked up 3 transactions"}
        raise RuntimeError("database went away")

    monkeypatch.setattr("app.routers.chat.chat_events", breaks_partway)

    events = _parse_sse(client.post("/api/v1/chat/stream", json={"messages": ASK}).text)

    assert [e["type"] for e in events] == ["tool", "done"]
    assert "went wrong" in events[-1]["message"]
