
import csv
import io
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.pipeline import process_ticket
from app.schemas import TicketInput, TicketOutput


app = FastAPI(
    title="Support Ticket Intelligence",
    version="1.0.0",
    description=(
        "Classifies support tickets, estimates priority, "
        "and extracts structured fields."
    ),
)

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/classify", response_model=TicketOutput)
def classify(ticket: TicketInput):
    try:
        return process_ticket(ticket)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def process_batch(payload: list[TicketInput]) -> list[dict[str, Any]]:
    return [process_ticket(ticket).model_dump() for ticket in payload]


def format_csv(results: list[dict[str, Any]]) -> StreamingResponse:
    buffer = io.StringIO()
    fields = list(TicketOutput.model_fields.keys())
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=ticket_results.csv"
        },
    )


def format_batch_response(
    results: list[dict[str, Any]], output_format: str
):
    output_format = output_format.lower()

    if output_format == "csv":
        return format_csv(results)

    if output_format != "json":
        raise HTTPException(
            status_code=400,
            detail="format must be json or csv",
        )

    return {"count": len(results), "results": results}


def validate_batch_size(payload: list[TicketInput]):
    if len(payload) > 1000:
        raise HTTPException(
            status_code=413,
            detail="Maximum 1000 tickets per request.",
        )


@app.post("/batch")
def batch(payload: list[TicketInput], format: str = "json"):
    validate_batch_size(payload)
    results = process_batch(payload)
    return format_batch_response(results, format)


@app.post("/batch/upload")
async def batch_upload(
    file: UploadFile = File(...),
    format: str = "json",
):
    raw = await file.read()

    try:
        content = raw.decode("utf-8-sig")

        if file.filename and file.filename.lower().endswith(".csv"):
            rows = csv.DictReader(io.StringIO(content))
            payload = [
                TicketInput(
                    ticket_id=row.get("ticket_id") or None,
                    text=row["text"],
                )
                for row in rows
            ]
        else:
            parsed: Any = json.loads(content)

            if isinstance(parsed, dict) and "tickets" in parsed:
                parsed = parsed["tickets"]

            if not isinstance(parsed, list):
                raise ValueError(
                    "JSON input must be a list of tickets "
                    "or an object containing a 'tickets' list."
                )

            payload = [
                TicketInput.model_validate(item)
                for item in parsed
            ]

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValidationError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input file: {exc}",
        ) from exc

    validate_batch_size(payload)
    results = process_batch(payload)
    return format_batch_response(results, format)
