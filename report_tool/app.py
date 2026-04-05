import os
import uuid
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
from urllib.parse import quote

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="行业智能化分析报告工具")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
STATIC_DIR = BASE_DIR / "static"


# ─── Pydantic Models ────────────────────────────────────────────────────────

class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    level: Optional[int] = None

class ChapterCreate(BaseModel):
    title: str
    content: str = ""
    level: int = 2
    tags: List[str] = []

class ProjectCreate(BaseModel):
    title: str
    description: str = ""

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class AIGenerateRequest(BaseModel):
    project_id: str
    chapter_id: str
    context: str = ""
    report_context: str = ""

class ReorderRequest(BaseModel):
    chapter_ids: List[str]


# ─── Helpers ────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_project(project_id: str) -> dict:
    path = DATA_DIR / f"{project_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="项目数据损坏")

def save_project(project: dict) -> None:
    project["updated_at"] = now_iso()
    path = DATA_DIR / f"{project['id']}.json"
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_md_to_chapters(content: str) -> List[dict]:
    """Parse Markdown content into a flat chapter list."""
    lines = content.split("\n")
    chapters: List[dict] = []
    current_title: Optional[str] = None
    current_level: int = 0
    current_body: List[str] = []
    in_code_block: bool = False

    def flush():
        nonlocal current_title, current_level, current_body
        if current_title is None:
            return
        heading_prefix = "#" * current_level
        full_content = f"{heading_prefix} {current_title}\n" + "\n".join(current_body)
        chapters.append({
            "id": str(uuid.uuid4()),
            "title": current_title,
            "level": current_level,
            "content": full_content.strip(),
            "tags": [],
            "order": len(chapters),
        })

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block

        if not in_code_block:
            m = re.match(r"^(#{1,6})\s+(.+)", line)
            if m:
                flush()
                current_level = len(m.group(1))
                current_title = m.group(2).strip()
                current_body = []
                continue

        current_body.append(line)

    flush()
    return chapters

def extract_excerpt(content: str, keyword: str, context: int = 150) -> str:
    idx = content.lower().find(keyword.lower())
    if idx == -1:
        return content[:200] + ("..." if len(content) > 200 else "")
    start = max(0, idx - 80)
    end = min(len(content), idx + context)
    return ("…" if start > 0 else "") + content[start:end] + ("…" if end < len(content) else "")


# ─── Routes ─────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return FileResponse(str(STATIC_DIR / "index.html"))


# Projects

@app.get("/api/projects")
def list_projects():
    projects = []
    for f in DATA_DIR.glob("*.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            projects.append({
                "id": p["id"],
                "title": p["title"],
                "description": p.get("description", ""),
                "created_at": p["created_at"],
                "updated_at": p["updated_at"],
                "chapter_count": len(p.get("chapters", [])),
            })
        except Exception:
            continue
    projects.sort(key=lambda x: x["updated_at"], reverse=True)
    return projects

@app.post("/api/projects")
def create_project(body: ProjectCreate):
    project = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "description": body.description,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "chapters": [],
    }
    save_project(project)
    return project

@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    return load_project(project_id)

@app.put("/api/projects/{project_id}")
def update_project(project_id: str, body: ProjectUpdate):
    project = load_project(project_id)
    if body.title is not None:
        project["title"] = body.title
    if body.description is not None:
        project["description"] = body.description
    save_project(project)
    return project

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    path = DATA_DIR / f"{project_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    path.unlink()
    return {"ok": True}


# Import

@app.post("/api/import")
async def import_md(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="replace")

    chapters = parse_md_to_chapters(text)

    title = (file.filename or "未命名报告").replace(".md", "")
    if chapters and chapters[0]["level"] == 1:
        title = chapters[0]["title"]

    project = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": "",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "chapters": chapters,
    }
    save_project(project)
    return project


# Chapters

@app.post("/api/chapters/{project_id}")
def add_chapter(project_id: str, body: ChapterCreate):
    project = load_project(project_id)
    heading_prefix = "#" * body.level
    content = body.content or f"{heading_prefix} {body.title}\n\n（请在此处填写内容）"
    chapter = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "level": body.level,
        "content": content,
        "tags": body.tags,
        "order": len(project["chapters"]),
    }
    project["chapters"].append(chapter)
    save_project(project)
    return project

@app.put("/api/chapters/{project_id}/{chapter_id}")
def update_chapter(project_id: str, chapter_id: str, body: ChapterUpdate):
    project = load_project(project_id)
    chapter = next((c for c in project["chapters"] if c["id"] == chapter_id), None)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    if body.title is not None:
        chapter["title"] = body.title
    if body.content is not None:
        chapter["content"] = body.content
    if body.tags is not None:
        chapter["tags"] = body.tags
    if body.level is not None:
        chapter["level"] = body.level
    save_project(project)
    return project

@app.delete("/api/chapters/{project_id}/{chapter_id}")
def delete_chapter(project_id: str, chapter_id: str):
    project = load_project(project_id)
    project["chapters"] = [c for c in project["chapters"] if c["id"] != chapter_id]
    for i, c in enumerate(project["chapters"]):
        c["order"] = i
    save_project(project)
    return project


# Reorder

@app.post("/api/reorder/{project_id}")
def reorder_chapters(project_id: str, req: ReorderRequest):
    project = load_project(project_id)
    chapter_map = {c["id"]: c for c in project["chapters"]}
    reordered = []
    for i, cid in enumerate(req.chapter_ids):
        if cid not in chapter_map:
            raise HTTPException(status_code=400, detail=f"章节 {cid} 不存在")
        chapter_map[cid]["order"] = i
        reordered.append(chapter_map[cid])
    project["chapters"] = reordered
    save_project(project)
    return project


# AI Generate

@app.post("/api/ai/generate")
def ai_generate(req: AIGenerateRequest):
    project = load_project(req.project_id)
    chapter = next((c for c in project["chapters"] if c["id"] == req.chapter_id), None)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="未配置 ANTHROPIC_API_KEY，请在 .env 文件中设置")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = (
            "你是行业智能化分析报告专家，专注于AI产业发展趋势、行业落地挑战与核心方法论研究。"
            "报告风格：结构清晰、数据驱动、洞察深刻、语言专业。"
            "请用Markdown格式输出，不要重复输出章节标题行，直接从正文内容开始。"
        )

        user_content = f"请为以下章节生成详细的分析内容：\n\n章节标题：{chapter['title']}\n章节级别：H{chapter['level']}\n"
        if req.context:
            user_content += f"\n用户补充要求：{req.context}\n"
        if req.report_context:
            user_content += f"\n报告其他章节背景：\n{req.report_context}\n"
        user_content += "\n请生成该章节的完整Markdown正文内容："

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            timeout=60.0,
        )
        return {"content": message.content[0].text, "chapter_id": req.chapter_id}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI生成失败：{str(e)}")


# Search

@app.get("/api/search/local")
def search_local(q: str):
    if not q.strip():
        return {"query": q, "results": [], "count": 0}
    results = []
    for f in DATA_DIR.glob("*.json"):
        try:
            project = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for chapter in project.get("chapters", []):
            title = chapter.get("title", "")
            content = chapter.get("content", "")
            if q.lower() in title.lower() or q.lower() in content.lower():
                results.append({
                    "project_id": project["id"],
                    "project_title": project["title"],
                    "chapter_id": chapter["id"],
                    "chapter_title": title,
                    "excerpt": extract_excerpt(content, q),
                    "match_in": "title" if q.lower() in title.lower() else "content",
                })
    return {"query": q, "results": results, "count": len(results)}

@app.get("/api/search/web")
def search_web(q: str):
    if not q.strip():
        return {"query": q, "results": []}
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.text(q, max_results=8))
        results = [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in raw
        ]
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"联网搜索失败：{str(e)}")


# Export

@app.get("/api/export/{project_id}")
def export_project(project_id: str):
    project = load_project(project_id)
    chapters = sorted(project["chapters"], key=lambda c: c.get("order", 0))

    lines = []
    if project.get("description"):
        lines += [project["description"], ""]

    for chapter in chapters:
        content = chapter.get("content", "").strip()
        if content:
            lines.append(content)
            lines.append("")

    md_content = "\n".join(lines).strip()

    safe_title = re.sub(r"[^\w\u4e00-\u9fff\s\-]", "", project["title"])[:50].strip()
    filename = f"{safe_title}.md"
    encoded_filename = quote(filename, safe="")

    return Response(
        content=md_content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        },
    )


# Mount static files LAST
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
