from __future__ import annotations

from html import escape
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(prefix="/designs", tags=["designs"])

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DESIGNS_ROOT = _REPO_ROOT / "designs"

_V1_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("claude", "designs_claude", "Claude"),
    ("gpt", "designs_gpt", "GPT"),
    ("gemini", "designs_gemini", "Gemini"),
)


def _html_files(directory: Path) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".html")


@router.get("/v1", response_class=HTMLResponse)
def list_designs_v1() -> HTMLResponse:
    section_markup: list[str] = []

    for provider_slug, directory_name, display_name in _V1_SECTIONS:
        files = _html_files(_DESIGNS_ROOT / directory_name)
        if files:
            links = "\n".join(
                f'<li><a href="/designs/v1/{provider_slug}/{escape(file_path.name)}" target="_blank">{escape(file_path.name)}</a></li>'
                for file_path in files
            )
        else:
            links = '<li class="muted">No designs found.</li>'

        section_markup.append(
            f"""
            <section>
              <h2>{escape(display_name)}</h2>
              <ul>
                {links}
              </ul>
            </section>
            """
        )

    html = f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Athena Designs v1</title>
        <style>
          :root {{ color-scheme: dark; }}
          body {{
            font-family: Inter, Segoe UI, Arial, sans-serif;
            margin: 0;
            background: #0f1115;
            color: #e8ecf1;
          }}
          main {{
            max-width: 960px;
            margin: 32px auto;
            padding: 0 20px 32px;
          }}
          h1 {{ margin-bottom: 8px; }}
          p {{ color: #aab3bf; }}
          .version {{ color: #7da2ff; font-weight: 600; }}
          .grid {{
            margin-top: 24px;
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
          }}
          section {{
            border: 1px solid #2a3140;
            background: #171b24;
            border-radius: 12px;
            padding: 14px;
          }}
          h2 {{ margin: 0 0 10px; font-size: 18px; }}
          ul {{ margin: 0; padding-left: 18px; }}
          li {{ margin: 6px 0; }}
          a {{ color: #93b8ff; text-decoration: none; }}
          a:hover {{ text-decoration: underline; }}
          .muted {{ color: #8893a2; }}
          @media (max-width: 840px) {{
            .grid {{ grid-template-columns: 1fr; }}
          }}
        </style>
      </head>
      <body>
        <main>
          <h1>Design Review Hub <span class="version">v1</span></h1>
          <p>Browse current design concepts by model family.</p>
          <div class="grid">
            {''.join(section_markup)}
          </div>
        </main>
      </body>
    </html>
    """

    return HTMLResponse(content=html)


@router.get("/v1/{provider}/{filename}")
def get_design_file_v1(provider: str, filename: str) -> FileResponse:
    provider_dir = {slug: directory_name for slug, directory_name, _ in _V1_SECTIONS}.get(provider.lower())
    if provider_dir is None:
        raise HTTPException(status_code=404, detail="Unknown design provider")

    if not filename.lower().endswith(".html"):
        raise HTTPException(status_code=404, detail="Design file not found")

    file_path = (_DESIGNS_ROOT / provider_dir / filename).resolve()
    allowed_dir = (_DESIGNS_ROOT / provider_dir).resolve()

    if allowed_dir not in file_path.parents:
        raise HTTPException(status_code=404, detail="Design file not found")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Design file not found")

    return FileResponse(file_path)
