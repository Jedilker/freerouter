import os
import time
import secrets
import numpy as np
import requests
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from sklearn.linear_model import LogisticRegression
from supabase import create_client, Client

# 1. FastAPI ve Şablon Motoru Kurulumu
app = FastAPI(title="Auth Entegreli Güvenli LLM Router API")
templates = Jinja2Templates(directory="templates")

# 2. Bağlantı Ayarları
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://YOUR_SUPABASE.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HF_API_URL = "https://huggingface.co"

# 3. Model ve Eğitim Ayarları
def get_embedding(text: str):
    response = requests.post(HF_API_URL, json={"inputs": text})
    return response.json() if response.status_code == 200 else [0.0] * 384

train_prompts = [
    "Bu metni özetle.", "Naber?", "10 ile 25'i topla.",
    "Python ile mikroservis mimarisi tasarla.", "Kuantum fiziği nedir?", "Risk analizi raporu yap."
]
train_labels = [0, 0, 0, 1, 1, 1]

X_train = [get_embedding(p) for p in train_prompts]
router_classifier = LogisticRegression().fit(X_train, np.array(train_labels))

# 4. Pydantic Veri Modelleri
class UserAuth(BaseModel):
    email: EmailStr
    password: str

class RouterRequest(BaseModel):
    prompt: str

# 5. API Anahtarı Kontrol Mekanizması
async def verify_api_key(x_api_key: str = Header(..., description="Sistemden ürettiğiniz API anahtarı")):
    result = supabase.table("user_api_keys").select("*").eq("api_key", x_api_key).eq("is_active", True).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Geçersiz veya pasif API anahtarı.")
    return result.data

# 6. GÖRSEL ARAYÜZ (Ana Sayfa) - Klasör arama zorunluluğunu kaldıran kararlı sürüm
@app.get("/", response_class=HTMLResponse, tags=["Görsel Arayüz"])
async def index_page(request: Request):
    try:
        # Kodun yanındaki dashboard.html dosyasını doğrudan düz metin olarak okur
        with open("dashboard.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        # Eğer dosya templates klasörünün içindeyse oradan okumayı dener (Yedek Plan)
        try:
            with open("templates/dashboard.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        except Exception:
            raise HTTPException(status_code=404, detail="dashboard.html dosyası sunucuda hiçbir yerde bulunamadı!")

# 7. Auth Uç Noktaları
@app.post("/auth/register", tags=["Kullanıcı Yönetimi"])
async def register(user: UserAuth):
    try:
        res = supabase.auth.sign_up({"email": user.email, "password": user.password})
        return {"message": "Kullanıcı başarıyla oluşturuldu.", "user_id": res.user.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login-and-generate-key", tags=["Kullanıcı Yönetimi"])
async def login_and_generate_key(user: UserAuth):
    try:
        res = supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
        new_key = f"sk_live_{secrets.token_hex(24)}"
        supabase.table("user_api_keys").insert({"user_id": res.user.id, "api_key": new_key}).execute()
        return {"status": "Giriş Başarılı", "your_api_key": new_key}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Supabase Hatası: {str(e)}")

# 8. Korunan Router Servisi
@app.post("/route", tags=["Yönlendirici Motoru"])
async def route_llm(request: RouterRequest, current_user: dict = Depends(verify_api_key)):
    start_time = time.time()
    try:
        prompt_vector = get_embedding(request.prompt)
        X_test = np.array(prompt_vector).reshape(1, -1)
        
        prediction = router_classifier.predict(X_test)
        probabilities = router_classifier.predict_proba(X_test)
        confidence = float(probabilities[prediction] * 100)
        
        target = "Llama-3-8B" if prediction == 0 else "Claude-3.5-Sonnet"
        latency = round((time.time() - start_time) * 1000, 2)
        
        supabase.table("router_logs").insert({
            "prompt": request.prompt,
            "target_model": target,
            "confidence": round(confidence, 2),
            "latency_ms": latency
        }).execute()
        
        return {"target_model": target, "confidence": round(confidence, 2), "latency_ms": latency}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Router İç Hatası: {str(e)}")

# 9. Analitik ve Raporlama Servisi
@app.get("/analytics", tags=["Müşteri Paneli & Analitik"])
async def get_user_analytics(current_user: dict = Depends(verify_api_key)):
    try:
        logs_result = supabase.table("router_logs").select("*").execute()
        logs = logs_result.data
        
        if not logs:
            return {
                "summary": {
                    "total_requests": 0, "average_latency_ms": 0.0,
                    "financials": {"total_saved_usd": 0.0, "saved_currency_text": "$0.00 USD Tasarruf Edildi"}
                },
                "chart_data": {"labels": ["Llama-3-8B (Ucuz)", "Claude-3.5 (Pahalı)"], "datasets": [0, 0]},
                "status": "success"
            }
            
        total_requests = len(logs)
        cheap_model_count = sum(1 for log in logs if log["target_model"] == "Llama-3-8B")
        expensive_model_count = sum(1 for log in logs if log["target_model"] == "Claude-3.5-Sonnet")
        
        total_saved_usd = round(cheap_model_count * 0.00245, 5)
        total_latency = sum(log["latency_ms"] for log in logs)
        average_latency_ms = round(total_latency / total_requests, 2)
        
        return {
            "summary": {
                "total_requests": total_requests,
                "average_latency_ms": average_latency_ms,
                "financials": {
                    "total_saved_usd": total_saved_usd,
                    "saved_currency_text": f"${total_saved_usd} USD Tasarruf Edildi"
                }
            },
            "chart_data": {
                "labels": ["Llama-3-8B (Ucuz)", "Claude-3.5 (Pahalı)"],
                "datasets": [cheap_model_count, expensive_model_count]
            },
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analitik Raporu Alınamadı: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
