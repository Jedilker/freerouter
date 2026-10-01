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

## 🛠️ Destek ve Katkıda Bulunma

Eğer router motorumuzla ilgili bir sorun yaşarsanız veya kurumsal (On-Premises) kurulum talepleriniz olursa lütfen GitHub üzerinden bir `Issue` açın veya bizimle iletişime geçin.
