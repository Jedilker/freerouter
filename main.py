import os
import time
import secrets
import numpy as np
import requests
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, EmailStr
from sklearn.linear_model import LogisticRegression
from supabase import create_client, Client

app = FastAPI(title="Auth Entegreli Güvenli LLM Router API")

# 1. Bağlantı Ayarları
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://YOUR_SUPABASE.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HF_API_URL = "https://huggingface.co"

# 2. Model ve Eğitim Ayarları (Aynı kalıyor)
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

# 3. Pantic Veri Modelleri
class UserAuth(BaseModel):
    email: EmailStr
    password: str

class RouterRequest(BaseModel):
    prompt: str

# 4. API ANAHTARI KONTROL MEKANİZMASI (Güvenlik Katmanı)
async def verify_api_key(x_api_key: str = Header(..., description="Sistemden ürettiğiniz API anahtarı")):
    # Veritabanında bu anahtar var mı ve aktif mi kontrol et
    result = supabase.table("user_api_keys").select("*").eq("api_key", x_api_key).eq("is_active", True).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Geçersiz veya pasif API anahtarı. Lütfen giriş yapıp yeni bir anahtar üretin.")
    return result.data[0] # Giriş yapan kullanıcının bilgilerini döndürür

# 5. AUTH ENDPOINTS (Kayıt ve Giriş)
@app.post("/auth/register", tags=["Kullanıcı Yönetimi"])
async def register(user: UserAuth):
    try:
        # Supabase Auth üzerinde kullanıcı yaratır
        res = supabase.auth.sign_up({"email": user.email, "password": user.password})
        return {"message": "Kullanıcı başarıyla oluşturuldu. Lütfen e-postanızı onaylayın (eğer aktifse).", "user_id": res.user.id}
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
        # DEĞİŞİKLİK BURADA: Artık yuvarlanmış mesaj yerine gerçek hatayı ekrana basıyoruz
        raise HTTPException(status_code=400, detail=f"Supabase Hatası: {str(e)}")

# 6. KORUNAN ROUTE SERVİSİ
@app.post("/route", tags=["Yönlendirici Motoru"])
async def route_llm(request: RouterRequest, current_user: dict = Depends(verify_api_key)):
    start_time = time.time()
    try:
        prompt_vector = get_embedding(request.prompt)
        prediction = router_classifier.predict([prompt_vector])
        probabilities = router_classifier.predict_proba([prompt_vector])
        confidence = float(probabilities[prediction] * 100)
        
        target = "Llama-3-8B" if prediction == 0 else "Claude-3.5-Sonnet"
        latency = round((time.time() - start_time) * 1000, 2)
        
        # Log kaydına isteği atan kullanıcının ID'sini de ekliyoruz (Kullanım takibi için)
        supabase.table("router_logs").insert({
            "prompt": request.prompt,
            "target_model": target,
            "confidence": round(confidence, 2),
            "latency_ms": latency
        }).execute()
        
        return {"target_model": target, "confidence": round(confidence, 2), "latency_ms": latency}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
