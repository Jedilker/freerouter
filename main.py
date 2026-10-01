# Hafif ve kararlı Python imajını kullanıyoruz
FROM python:3.10-slim

# Sunucu içerisinde çalışma dizinini oluşturuyoruz
WORKDIR /app

# Sistem bağımlılıklarını güncelliyoruz (Derleme araçları gerekirse diye)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılık listesini kopyalayıp yüklüyoruz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Embedding modelini Docker imajı derlenirken önceden indiriyoruz. 
# Bu sayede sunucu her ayağa kalktığında modeli internetten indirip vakit kaybetmez.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Proje kodlarını içeri kopyalıyoruz
COPY . .

# Uygulamanın çalışacağı portu dışarı açıyoruz
EXPOSE 8000

# FastAPI uygulamasını uvicorn ile başlatıyoruz
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
