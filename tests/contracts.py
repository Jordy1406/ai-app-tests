"""Response contracts for FinAssist ID, written from its README spec (not from observed output).

`extra="forbid"` makes an unexpected field a failure: a silent API change should break the contract tests.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Strict):
    id: str = Field(pattern=r"^[a-z0-9_]+#\d{3}$")
    title: str = Field(min_length=1)
    section: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    score: float = Field(ge=-1, le=1)


class ChatResponse(Strict):
    answer: str = Field(min_length=1)
    refused: bool
    sources: list[Source]

    @model_validator(mode="after")
    def refusal_has_no_sources(self):
        # README: a refusal returns the fixed refusal text and no sources; an answer cites at least one source.
        if self.refused and self.sources:
            raise ValueError("refused answer must not carry sources")
        if not self.refused and not self.sources:
            raise ValueError("non-refused answer must cite at least one source")
        return self


class ToolCall(Strict):
    seq: int = Field(ge=1)
    turn: int = Field(ge=1)
    tool: str
    arguments: dict
    status: Literal["ok", "error", "pending_confirmation", "executed", "cancelled"]
    result: dict | None
    error_code: str | None
    at: str


class PendingOrder(Strict):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0, multiple_of=100)
    price: int = Field(gt=0)
    value: int = Field(gt=0)


class AgentResponse(Strict):
    session_id: str = Field(min_length=1)
    reply: str = Field(min_length=1)
    pending_order: PendingOrder | None
    tool_calls: list[ToolCall]


class AgentLog(Strict):
    session_id: str
    tool_calls: list[ToolCall]


class Order(Strict):
    order_id: str = Field(pattern=r"^ORD-\d{4}$")
    ticker: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0, multiple_of=100)
    price: int
    value: int
    timestamp: str


class Position(Strict):
    ticker: str
    shares: int
    lots: int
    avg_price: float
    last_price: int
    market_value: int
    unrealized_pl: float


class Portfolio(Strict):
    cash: int
    positions: list[Position]
    equity_value: int
    total_value: int


class AgentState(Strict):
    session_id: str
    portfolio: Portfolio
    orders: list[Order]
    pending_order: PendingOrder | None


REFUSAL_TEXT = "Maaf, saya tidak menemukan jawabannya di dokumen yang saya miliki."
