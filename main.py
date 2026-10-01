import os
import time
import numpy as np
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sklearn.linear_model import LogisticRegression
from supabase import create_client, Client

app = FastAPI(title="Hafifletilmiş LLM Router API")

# Supabase Bağlantıları
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://YOUR_SUPABASE.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Ücretsiz Hugging Face Karar Motoru (Token zorunlu değildir ama limitsiz olması için ekleyebilirsiniz)
HF_API_URL = "https://huggingface.co"
headers = {}

# Sunucu yükünü sıfıra indiren embedding fonksiyonu
def get_embedding(text: str):
    response = requests.post(HF_API_URL, headers=headers, json={"inputs": text})
    if response.status_code == 200:
        return response.json()
    else:
        # Hata durumunda yerel bir sahte vektör döndür (Sistemin çökmesini önler)
        return [0.0] * 384

# Router Eğitim Verisi
train_prompts = [
    "Bu metni özetle: ...", "Naber nasılsın?", "10 ile 25'i topla.", "Yazım hatalarını düzelt.",
    "Python ile mikroservis mimarisi tasarla.", "Kuantum fiziği nedir?", "Finansal risk analizi raporu yap."
]
train_labels = [0, 0, 0, 0, 1, 1, 1]

print("Hafif Vektörler Alınıyor...")
# Eğitim verilerini API üzerinden hızlıca vektörleştiriyoruz
X_train = [get_embedding(p) for p in train_prompts]
y_train = np.array(train_labels)

router_classifier = LogisticRegression()
router_classifier.fit(X_train, y_train)
print("Hafif Router Motoru Hazır!")

class RouterRequest(BaseModel):
    prompt: str

class RouterResponse(BaseModel):
    target_model: str
    confidence: float
    latency_ms: float

@app.post("/route", response_model=RouterResponse)
async def route_llm(request: RouterRequest):
    start_time = time.time()
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt boş olamaz.")
    
    try:
        prompt_vector = get_embedding(request.prompt)
        prediction = router_classifier.predict([prompt_vector])
        
        probabilities = router_classifier.predict_proba([prompt_vector])
        confidence = float(probabilities[0][prediction[0]] * 100)
        
        target = "Llama-3-8B" if prediction[0] == 0 else "Claude-3.5-Sonnet"
        end_time = time.time()
        latency = round((end_time - start_time) * 1000, 2)
        
        log_data = {
            "prompt": request.prompt,
            "target_model": target,
            "confidence": round(confidence, 2),
            "latency_ms": latency
        }
        supabase.table("router_logs").insert(log_data).execute()
        
        return RouterResponse(target_model=target, confidence=round(confidence, 2), latency_ms=latency)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
