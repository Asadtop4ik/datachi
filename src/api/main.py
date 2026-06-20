"""FastAPI ilova: /health va /chat.

/chat (BUILD_PLAN §8.5, §8.12): stateless — agentga FAQAT joriy xabar uzatiladi. Tarix app DB'ga
yoziladi (ko'rsatish uchun), LLM'ga UZATILMAYDI. Javob: {conversation_id, text, sql, rows,
vega_spec, chart_title}. Xato bo'lsa muloyim matn (xom stack-trace demo'da KO'RSATILMAYDI).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agent.analyst import Outcome, get_demo_cache, run_analysis
from src.db import get_app_engine
from src.models import Conversation, Message, SavedChart

app = FastAPI(title="Datachi AI Analytics")


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    conversation_id: int
    text: str
    sql: str | None
    rows: list[dict[str, Any]]
    vega_spec: dict[str, Any] | None
    chart_title: str
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    error_detail: str | None = None


class SaveChartRequest(BaseModel):
    conversation_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    vega_spec: dict[str, Any]
    sql: str | None = None


class SavedChartOut(BaseModel):
    id: int
    conversation_id: int | None
    title: str
    vega_spec: dict[str, Any]
    sql: str | None
    created_at: datetime


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _persist(conversation_id: int | None, message: str, outcome: Outcome) -> int:
    """User + assistant xabarlarni app DB'ga yozadi, conversation_id qaytaradi."""
    with Session(get_app_engine()) as session:
        if conversation_id is not None:
            conv = session.get(Conversation, conversation_id)
            if conv is None:
                raise HTTPException(status_code=404, detail="conversation topilmadi")
        else:
            conv = Conversation(title=message[:120])
            session.add(conv)
            session.flush()  # conv.id ni olish uchun

        session.add(Message(conversation_id=conv.id, role="user", content=message))
        session.add(
            Message(
                conversation_id=conv.id,
                role="assistant",
                content=outcome.text,
                sql=outcome.sql,
                vega_spec=outcome.vega_spec,
                chart_title=outcome.chart_title or None,
            )
        )
        session.commit()
        return conv.id


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="bo'sh xabar")

    # cache: live LLM kvota/tarmoq qoqilsa keshlangan demo javobi qaytadi (pitch yiqilmaydi).
    outcome = run_analysis(message, cache=get_demo_cache())
    conversation_id = _persist(req.conversation_id, message, outcome)

    return ChatResponse(
        conversation_id=conversation_id,
        text=outcome.text,
        sql=outcome.sql,
        rows=outcome.rows,
        vega_spec=outcome.vega_spec,
        chart_title=outcome.chart_title,
        metrics=outcome.metrics,
        error_detail=outcome.error_detail,
    )


def _chart_out(chart: SavedChart) -> SavedChartOut:
    return SavedChartOut(
        id=chart.id,
        conversation_id=chart.conversation_id,
        title=chart.title,
        vega_spec=chart.vega_spec,
        sql=chart.sql,
        created_at=chart.created_at,
    )


@app.post("/charts", response_model=SavedChartOut, status_code=201)
def save_chart(req: SaveChartRequest) -> SavedChartOut:
    """Grafikni saqlaydi (saved_charts). conversation_id berilsa, mavjudligi tekshiriladi."""
    with Session(get_app_engine()) as session:
        cid = req.conversation_id
        if cid is not None and session.get(Conversation, cid) is None:
            raise HTTPException(status_code=404, detail="conversation topilmadi")
        chart = SavedChart(
            conversation_id=req.conversation_id,
            title=req.title,
            vega_spec=req.vega_spec,
            sql=req.sql,
        )
        session.add(chart)
        session.commit()
        session.refresh(chart)
        return _chart_out(chart)


@app.get("/charts", response_model=list[SavedChartOut])
def list_charts(limit: int = 50) -> list[SavedChartOut]:
    """Saqlangan grafiklar (eng yangisi birinchi)."""
    with Session(get_app_engine()) as session:
        charts = (
            session.execute(
                select(SavedChart)
                .order_by(SavedChart.created_at.desc(), SavedChart.id.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [_chart_out(c) for c in charts]


@app.delete("/charts/{chart_id}", status_code=204)
def delete_chart(chart_id: int) -> Response:
    """Saqlangan grafikni o'chiradi."""
    with Session(get_app_engine()) as session:
        chart = session.get(SavedChart, chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="chart topilmadi")
        session.delete(chart)
        session.commit()
    return Response(status_code=204)
