# 🚀 LLM Router API Entegrasyon Dokümanı (SDK Örnekleri)

Bu doküman, sistemimizden aldığınız ticari `API Key` ile akıllı yönlendirici (router) motorumuzu kendi projelerinize (Python veya JavaScript/Node.js) nasıl entegre edeceğinizi gösterir.

Yönlendiricimiz gelen istemleri (prompt) milisaniyeler içinde analiz ederek en doğru ve maliyet odaklı modele otomatik olarak yönlendirir.

---

## 🔑 Başlamadan Önce: API Anahtarınızı Alın

1. `https://freerouter-zut6.onrender.com/docs` adresine gidin.
2. `/auth/register` ve `/auth/login-and-generate-key` servislerini kullanarak hesabınızı oluşturun ve `sk_live_...` ile başlayan API anahtarınızı kopyalayın.

---

## 🐍 1. Python ile Entegrasyon Örneği

Python projelerinizde akıllı yönlendirici API'mizi kullanmak için en popüler HTTP kütüphanesi olan `requests` paketini kullanabilirsiniz.

### Bağımlılığı Kurun:
```bash
pip install requests
```

### Kod Şablonu (`router_client.py`):
```python
import requests

# 1. API Ayarlarını Tanımlayın
API_URL = "https://YOUR_ROUTER_://onrender.com"
API_KEY = "sk_live_SİZİN_API_ANAHTARINIZ" # Buraya kendi anahtarınızı yazın

# 2. Test Etmek İstediğiniz Yapay Zekâ İstemini Hazırlayın
payload = {
    "prompt": "AWS üzerinde Kubernetes kümesi kurarken güvenlik duvarı kurallarını nasıl yapılandırmalıyım?"
}

# 3. Güvenlik Anahtarını Header Olarak Ekleyin
headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

try:
    # 4. İsteği Gönderin
    print("Yönlendirme kararı alınıyor...")
    response = requests.post(API_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Karar Başarılı!")
        print(f"🎯 Hedef Model: {result['target_model']}")
        print(f"📊 Güven Skoru: %{result['confidence']}")
        print(f"⚡ Gecikme (Latency): {result['latency_ms']} ms")
        
        # PROJENİZDEKİ AKSİYON:
        # Burada dönen 'target_model' değerine göre isteğinizi 
        # OpenAI API'sine mi yoksa Anthropic API'sine mi atacağınıza karar verebilirsiniz.
        
    else:
        print(f"❌ Hata Oluştu! Durum Kodu: {response.status_code}")
        print(response.json())

except Exception as e:
    print(f"Sunucuya bağlanırken bir hata yaşandı: {e}")
```

---

## 🟨 2. JavaScript / Node.js ile Entegrasyon Örneği

Modern JavaScript projelerinizde (Node.js, React, Next.js vb.) tarayıcı tabanlı yerel `fetch` fonksiyonunu kullanarak entegrasyonu saniyeler içinde tamamlayabilirsiniz.

### Kod Şablonu (`router_client.js`):
```javascript
// 1. API Ayarlarını Tanımlayın
const API_URL = "https://YOUR_ROUTER_://onrender.com";
const API_KEY = "sk_live_SİZİN_API_ANAHTARINIZ"; // Buraya kendi anahtarınızı yazın

// 2. İstek Verisini Hazırlayın
const requestData = {
    prompt: "Bana Javascript ile hızlı bir sıralama (sort) fonksiyonu yazar mısın?"
};

async function getLLMRoute() {
    try {
        console.log("Yönlendirme kararı alınıyor...");
        
        // 3. İsteği Gönderin
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();

        if (response.ok) {
            console.log("\n✅ Karar Başarılı!");
            console.log(`🎯 Hedef Model: ${result.target_model}`);
            console.log(`📊 Güven Skoru: %${result.confidence}`);
            console.log(`⚡ Gecikme (Latency): ${result.latency_ms} ms`);
        } else {
            console.error(`❌ Hata Oluştu: ${result.detail || 'Bilinmeyen Hata'}`);
        }

    } catch (error) {
        console.error("Sunucu ile iletişim kurulurken bir hata yaşandı:", error);
    }
}

// Fonksiyonu çalıştırın
getLLMRoute();
```

---
# ⚡ FreeRouter: The Ultra-Fast, Open-Source & Privacy-First LLM Router

[![License: MIT](https://shields.io)](https://opensource.org)
[![FastAPI](https://shields.io)](https://tiangolo.com)
[![Render](https://shields.io)](https://render.com)
[![Supabase](https://shields.io)](https://supabase.com)

**FreeRouter**, yapay zekâ uygulamalarınızdaki API maliyetlerini %50'ye varan oranda düşüren, bağımlılık riskini (vendor lock-in) ortadan kaldıran ve kararları ışık hızında veren açık kaynaklı bir **LLM Router (Yönlendirici)** projesidir. 

Ağır ve maliyetli LLM katmanları kullanan rakiplerin aksine, FreeRouter yerel gömülü matematiksel motoru sayesinde yönlendirme kararlarını **sadece 15-30ms** içinde, tamamen ücretsiz ve güvenli bir şekilde verir.

---

## 🎯 Neden FreeRouter? (Temel Değer Önerileri)

* **💰 %50+ Maliyet Tasarrufu:** Basit istekleri otomatik olarak ultra ucuz açık kaynaklı modellere (Llama-3-8B vb.), karmaşık analizleri ise gelişmiş modellere (Claude 3.5 Sonnet vb.) yönlendirir.
* **⚡ Işık Hızında Karar (Low Latency):** Arkada karar vermek için ikinci bir LLM çalıştırmaz. Embedding tabanlı akıllı sınıflandırıcısı sayesinde kararlar milisaniyeler içinde alınır.
* **🔄 %100 Kesintisiz Hizmet (Fallback / Uptime):** Bir sağlayıcının API'si (Örn: OpenAI) çöktüğünde veya yavaşladığında, trafiği anında alternatif modellere aktarır.
* **🛡️ Gizlilik ve Güvenlik (Privacy-First):** Kurumsal verilerinizi dışarı aktarmaz. İsterseniz Docker altyapısı sayesinde tamamen kendi sunucularınızda (On-Premises) çalıştırabilirsiniz.
* **📊 Canlı Finansal Dashboard:** Müşteri paneli üzerinden toplam istek sayınızı, model dağılım grafiklerinizi ve cebinizde kalan net dolar tasarrufunuzu canlı olarak izleyin.

---

## 🛠️ Mimari ve Teknolojik Altyapı

FreeRouter, modern yazılım standartları ve bulut teknolojileriyle sıfır maliyetle ölçeklenebilecek şekilde tasarlanmıştır:
* **Backend:** [FastAPI](https://tiangolo.com) (Asenkron ve Yüksek Performanslı Web API)
* **Karar Motoru:** Yerel [Scikit-Learn](https://scikit-learn.org) ve Bulut Tabanlı Embedding Entegrasyonu (Jev felsefesiyle üretilmiş hafif alternatif)
* **Veritabanı & Kimlik Doğrulama:** [Supabase](https://supabase.com) (PostgreSQL + Canlı Loglama + Güvenli API Key Auth)
* **Konteynerizasyon:** [Docker](https://docker.com) (Her bulut platformuna tek tıkla kurulum uyumlu)

---

## 💻 Canlı Panel Görüntüsü (Dashboard)

Uygulamanın ana dizinine girdiğinizde sizi karşılayan modern arayüz üzerinden:
1. Kayıt olabilir ve kendinize özel güvenli ticari `API Key` üretebilirsiniz.
2. Ürettiğiniz anahtarı girerek yapay zekâ harcamalarınızı ve model dağılım pasta grafiklerinizi anlık olarak takip edebilirsiniz.

---

## 🚀 Hızlı Başlangıç ve Entegrasyon

FreeRouter'ı kendi projenize entegre etmek sadece 3 satır kod sürer.

---

## 💰 SaaS İş Modeli ve Lisans

FreeRouter, **MIT Lisansı** ile tamamen açık kaynaklıdır. Projeyi ticari bir SaaS ürünü olarak konumlandırırken şu modeller uygulanabilir:
1. **Developer Tier (\$0):** Aylık 50.000 isteğe kadar ücretsiz akıllı yönlendirme (BYOK - Kendi Anahtarını Getir mantığıyla).
2. **Startup Tier (\$49/Ay):** Gelişmiş dashboard özellikleri, takım yönetimi ve geçmişe dönük analitik verileri.
3. **Enterprise (Özel):** Tamamen şirkete özel sunucu kurulumu (On-Premises), özel güvenlik duvarları (guardrails) ve SLA garantisi.

---

## 🤝 Katkıda Bulunun

FreeRouter topluluk destekli bir projedir. Geliştirme sürecine katkıda bulunmak, yeni akıllı yönlendirme kuralları eklemek veya hata bildirmek için lütfen bir `Issue` açın veya `Pull Request` gönderin!

## 🛠️ Destek ve Katkıda Bulunma

Eğer router motorumuzla ilgili bir sorun yaşarsanız veya kurumsal (On-Premises) kurulum talepleriniz olursa lütfen GitHub üzerinden bir `Issue` açın veya bizimle iletişime geçin.
