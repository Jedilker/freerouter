import hashlib
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from supabase import Client, create_client


app = FastAPI(
    title="FreeRouter API",
    description="Deterministic model selection API. It does not call model providers.",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = BASE_DIR / "dashboard.html"
ANALYTICS_SAMPLE_LIMIT = 1000
_supabase: Client | None = None

COMPLEXITY_TERMS = re.compile(
    r"\b(architecture|architect|security|threat model|distributed|scalab\w*|"
    r"concurren\w*|trade-?off\w*|compare|migration|optimi[sz]\w*|"
    r"risk analysis|deep dive|in detail|kapsamlı|mimari|güvenlik|"
    r"karşılaştır|optimiz\w*|ölçeklen\w*|dağıtık|detaylı analiz)\b",
    re.IGNORECASE,
)
MULTI_STEP_TERMS = re.compile(
    r"\b(then|after that|step by step|and also|as well as|"
    r"ayrıca|ardından|adım adım|bunun yanında)\b",
    re.IGNORECASE,
)


class UserAuth(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RouterRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)


def get_supabase() -> Client:
    global _supabase
    if _supabase is not None:
        return _supabase

    url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_role_key:
        raise HTTPException(
            status_code=503,
            detail="Authentication and persistence are unavailable: configure Supabase.",
        )

    try:
        _supabase = create_client(url, service_role_key)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Supabase configuration is invalid or unavailable.",
        ) from None
    return _supabase


def get_auth_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not anon_key:
        raise HTTPException(
            status_code=503,
            detail="Authentication is unavailable: configure Supabase Auth.",
        )
    try:
        return create_client(url, anon_key)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Supabase Auth configuration is invalid or unavailable.",
        ) from None


def get_model_names() -> tuple[str, str]:
    budget_model = os.getenv("ROUTER_BUDGET_MODEL", "").strip()
    quality_model = os.getenv("ROUTER_QUALITY_MODEL", "").strip()
    if not budget_model or not quality_model or budget_model == quality_model:
        raise HTTPException(
            status_code=503,
            detail="Configure distinct budget and quality model names.",
        )
    return budget_model, quality_model


def choose_model(prompt: str) -> tuple[str, str]:
    """Choose a configured model with transparent, deterministic prompt heuristics."""
    words = re.findall(r"\w+", prompt, flags=re.UNICODE)
    score = 0
    if len(words) >= 180:
        score += 2
    elif len(words) >= 70:
        score += 1

    score += min(2, len(COMPLEXITY_TERMS.findall(prompt)))
    if MULTI_STEP_TERMS.search(prompt):
        score += 1
    if "```" in prompt or re.search(r"(?m)^\s*(def |class |function |SELECT )", prompt):
        score += 2

    budget_model, quality_model = get_model_names()
    if score >= 2:
        return quality_model, "complexity_rules"
    return budget_model, "simple_request"


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> dict[str, Any]:
    if not x_api_key or not x_api_key.startswith("sk_live_"):
        raise HTTPException(status_code=401, detail="A valid API key is required.")

    key_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    try:
        result = (
            get_supabase()
            .table("user_api_keys")
            .select("user_id")
            .eq("key_hash", key_hash)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503, detail="API key validation is temporarily unavailable."
        ) from None
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")
    return {"user_id": result.data[0]["user_id"]}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(DASHBOARD_PATH, media_type="text/html")


@app.get("/health", tags=["Operations"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", tags=["Authentication"])
def register(user: UserAuth) -> dict[str, str]:
    try:
        result = get_auth_client().auth.sign_up(
            {"email": str(user.email), "password": user.password}
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Registration failed. Check the email and password or try signing in.",
        ) from None

    if not result.user:
        raise HTTPException(
            status_code=400,
            detail="Registration could not be completed. Check your email settings.",
        )
    return {"message": "Registration successful. Verify your email if required."}


@app.post("/auth/login-and-generate-key", tags=["Authentication"])
def login_and_generate_key(user: UserAuth) -> dict[str, str]:
    try:
        result = get_auth_client().auth.sign_in_with_password(
            {"email": str(user.email), "password": user.password}
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password.") from None

    if not result.user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    api_key = f"sk_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    try:
        get_supabase().table("user_api_keys").insert(
            {
                "user_id": str(result.user.id),
                "key_hash": key_hash,
                "key_prefix": api_key[:16],
                "is_active": True,
            }
        ).execute()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="The API key could not be saved. Please try again.",
        ) from None

    return {
        "status": "success",
        "api_key": api_key,
        "message": "Store this key securely; it will not be shown again.",
    }


@app.post("/route", tags=["Router"])
def route_llm(
    request: RouterRequest,
    current_user: dict[str, Any] = Depends(require_api_key),
) -> dict[str, Any]:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt must not be blank.")

    started_at = time.perf_counter()
    target_model, routing_reason = choose_model(prompt)
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

    try:
        get_supabase().table("router_logs").insert(
            {
                "user_id": current_user["user_id"],
                "target_model": target_model,
                "routing_reason": routing_reason,
                "latency_ms": latency_ms,
            }
        ).execute()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="The routing decision could not be recorded. Please retry.",
        ) from None

    return {
        "target_model": target_model,
        "routing_reason": routing_reason,
        "latency_ms": latency_ms,
        "note": "Selection only; send the prompt to your model provider separately.",
    }


@app.get("/analytics", tags=["Analytics"])
def get_user_analytics(
    current_user: dict[str, Any] = Depends(require_api_key),
) -> dict[str, Any]:
    client = get_supabase()
    user_id = current_user["user_id"]
    budget_model, quality_model = get_model_names()
    try:
        total_result = (
            client.table("router_logs")
            .select("id", count="exact", head=True)
            .eq("user_id", user_id)
            .execute()
        )
        logs_result = (
            client.table("router_logs")
            .select("target_model,latency_ms")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(ANALYTICS_SAMPLE_LIMIT)
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=503, detail="Analytics are temporarily unavailable."
        ) from None

    logs = logs_result.data or []
    total_requests = total_result.count or 0
    model_counts: dict[str, int] = {}
    for log in logs:
        model = log["target_model"]
        model_counts[model] = model_counts.get(model, 0) + 1

    average_latency = (
        round(sum(float(log["latency_ms"]) for log in logs) / len(logs), 2)
        if logs
        else 0.0
    )
    labels = [budget_model, quality_model]
    counts = [model_counts.get(model, 0) for model in labels]
    return {
        "summary": {
            "total_requests": total_requests,
            "average_latency_ms": average_latency,
        },
        "chart_data": {"labels": labels, "datasets": counts},
        "sampled_requests": len(logs),
        "sample_limit": ANALYTICS_SAMPLE_LIMIT,
    }
