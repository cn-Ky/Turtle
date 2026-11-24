# Turtle GUI — Network Explorer

Turtle'ın terminal odaklı ağ keşif akışını Türkçe bir masaüstü arayüzüne taşıyan, Python/Tkinter tabanlı sürüm.

- Ağ arayüzlerini ve IP/MAC bilgilerini görüntüleme
- İşletim sisteminin yerel aracıyla yakındaki Wi-Fi ağlarını listeleme
- Bağlı olunan özel IPv4 LAN üzerinde cihaz keşfi (en fazla `/22`)
- Scapy ile yalnızca paket başlık metaverisini izleme (payload gösterilmez)
- TCP port analizi (özel olmayan hedeflerde açık yazılı yetki onayı gerekir)
- Kaynak depo ve lisans bilgilerine uygulama içinden erişim

## Gereksinimler

- Python 3.10 veya üzeri
- Tkinter (çoğu Python dağıtımında Python ile gelir)
- `psutil` (kurulum adımında yüklenir)
- Paket izleme özelliği için isteğe bağlı `scapy` ve işletim sisteminin libpcap/Npcap bileşeni

## macOS (Apple Silicon / Intel)

Terminal'i bu klasörde aç:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Paket izleme için ayrıca:

```bash
python -m pip install scapy
sudo .venv/bin/python app.py
```

Not: macOS'ta Wi-Fi listeleme, işletim sistemi sürümüne ve Gizlilik/Güvenlik izinlerine göre değişebilir. Terminal'e Wi-Fi/konum izni verilmesi gerekebilir.

## Windows

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Paket izleme için `python -m pip install scapy` ve Npcap gerekebilir. Yönetici olarak çalıştırmak gerekebilir.

## Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Wi-Fi listesi için NetworkManager/`nmcli` gerekir. Paket yakalama için Scapy, libpcap ve uygun yetkiler gerekir.

## Başlatıcılar

macOS/Linux: `./run.sh`

Windows: `run.bat`

İlk açılışta başlatıcı `.venv` ortamını oluşturur ve temel bağımlılıkları yükler.

## Güvenlik sınırları

- Bu araç yalnızca kendi ağında veya yazılı izin alınmış sistemlerde kullanılmalıdır.
- LAN keşfi bağlı olunan özel IPv4 alt ağıyla sınırlıdır ve en fazla `/22` büyüklüğünde adres alanı kontrol eder.
- Genel/özel olmayan IP adreslerinde port taraması, kullanıcı açık yetki onayını vermeden başlatılmaz.
- Port taraması tek seferde en fazla 4096 portla sınırlandırılmıştır.
- Paket izleme payload içeriğini okumaz, kaydetmez veya göstermez; yalnızca protokol, adres ve port gibi başlık metaverisini listeler.
- Wi-Fi listeleme işletim sisteminin kendi tarama komutlarını kullanır; paket enjeksiyonu veya deauthentication yapmaz.

Bu proje eğitim ve yetkili ağ yönetimi içindir. İzinsiz tarama/dinleme veya erişim hukuki sorumluluk doğurabilir.
