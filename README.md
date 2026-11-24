# 🐢 Turtle — Türkçe Ağ Analiz Aracı (Eğitim Amaçlı)

Rust ile yazılmış, Windows / macOS / Linux üzerinde çalışan, sade ve Türkçe arayüzlü bir ağ analiz aracı.

> ⚠️ **Yasal uyarı:** Bu proje yalnızca eğitim amaçlıdır. Sadece **kendi ağında** veya **yazılı izin aldığın**
> sistemlerde kullan. İzinsiz tarama, dinleme veya erişim Türk Ceza Kanunu (m. 132, 133, 243, 244) ve KVKK
> kapsamında suç/ihlal oluşturabilir. Yazarlar kötüye kullanımdan sorumlu değildir.

## Ne yapar?

| Komut | Açıklama |
|-------|----------|
| `arayuzler` | Ağ arayüzlerini, IP ve MAC adreslerini listeler |
| `wifi` | Çevredeki Wi-Fi ağlarını **pasif** olarak listeler (SSID, BSSID, kanal, sinyal, güvenlik) |
| `lan` | Bağlı olduğun yerel ağdaki cihazları ARP ile keşfeder (IP, MAC, üretici, ana bilgisayar adı) |
| `yakala` | Kendi arayüzünde **başlık düzeyinde** paket özeti gösterir (TCP/UDP/DNS/ICMP/ARP) |
| `port` | Hedefte açık TCP portlarını tarar |
| `guncelle` | Yeni sürüm varsa indirir ve programı günceller |
