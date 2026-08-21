"""BVR-Star command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from bvr_star.config import public_config
from bvr_star.location.nominatim import NominatimGeocoder
from bvr_star.location.resolve import resolve_location
from bvr_star.models.errors import BVRStarError
from bvr_star.models.request import BirthInput, ChartRequest
from bvr_star.prompting import render_prompt
from bvr_star.service import ChartService

app = typer.Typer(help="Raman sidereal Jyotish calculations for AI-assisted readings.", no_args_is_help=True)


def _print_error(exc: Exception) -> None:
    data = (
        exc.to_dict()
        if isinstance(exc, BVRStarError)
        else {"error": {"code": "UNEXPECTED_ERROR", "message": str(exc)}}
    )
    typer.echo(json.dumps(data, ensure_ascii=False), err=True)


@app.command()
def calculate(
    input: Annotated[Path, typer.Option("--input", "-i", exists=True, readable=True)],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Calculate a chart from a JSON request file."""
    try:
        request = ChartRequest.model_validate_json(input.read_text(encoding="utf-8"))
        text = ChartService().calculate(request).model_dump_json(indent=2)
        if output:
            output.write_text(text + "\n", encoding="utf-8")
        else:
            typer.echo(text)
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(1) from exc


@app.command("resolve-location")
def resolve_location_command(address: str) -> None:
    try:
        birth = BirthInput(date="2000-01-01", place=address)
        result = resolve_location(birth, NominatimGeocoder())
        typer.echo(result.model_dump_json(indent=2))
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(1) from exc


@app.command()
def config() -> None:
    typer.echo(json.dumps(public_config(), ensure_ascii=False, indent=2))


@app.command()
def prompt(language: str = typer.Option("zh-TW", "--language", "-l")) -> None:
    try:
        typer.echo(render_prompt(language))
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(1) from exc


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    uvicorn.run("bvr_star.api.app:app", host=host, port=port)
