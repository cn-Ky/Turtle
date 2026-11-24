# agtarayici — Türkçe Ağ Analiz Aracı (Eğitim Amaçlı)

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

## Ne yapmaz? (bilinçli tasarım kararları)

- Deauth, paket enjeksiyonu, şifre kırma, handshake yakalama **yoktur**.
- Paket yükü (payload) içeriği **yazdırılmaz**; yalnızca başlık bilgisi gösterilir.
- Keşif yalnızca özel (LAN) ağlarda çalışır.
- İnternetteki (özel olmayan) hedeflerde port tarama için `--yetkili` bayrağı zorunludur.
- Kişi veya cihaz takibi / konumlandırma özelliği yoktur.

## Kurulum

```bash
git clone <depo-adresi>
cd agtarayici
cargo build --release
```

Gereksinimler:

- **Rust** (https://rustup.rs)
- **Linux:** `libpcap-dev` gerekmez (pnet ham soket kullanır); Wi-Fi taraması için `nmcli` (NetworkManager)
- **Windows:** [Npcap](https://npcap.com) ("WinPcap API-compatible mode" ile) ve yönetici terminali
- **macOS:** `sudo` ile çalıştır; Wi-Fi için Konum İzni gerekebilir

## Kullanım

```bash
agtarayici arayuzler
agtarayici wifi
sudo agtarayici lan
sudo agtarayici lan --arayuz wlan0
sudo agtarayici yakala eth0 --sayi 50 --filtre dns
sudo agtarayici yakala wlan0 --filtre port:443
agtarayici port 192.168.1.1 --aralik 1-1024
agtarayici port 203.0.113.10 --aralik 22,80,443 --yetkili
```

## Üretici (OUI) veritabanı

Daha doğru üretici adları için IEEE listesini çalışma dizinine `oui.txt` olarak indir:
https://standards-oui.ieee.org/oui/oui.txt (dosya `.gitignore` içindedir).

## Proje yapısı

```
src/
  main.rs     komut satırı arayüzü (clap)
  wifi.rs     pasif Wi-Fi listesi (nmcli / netsh / system_profiler)
  lan.rs      arayüzler + ARP keşfi
  capture.rs  başlık düzeyinde paket özeti
  ports.rs    eşzamanlı TCP connect taraması (tokio)
  oui.rs      MAC → üretici eşleme
```

## Yol haritası (fikirler)

- Terminal arayüzü (ratatui) ile canlı panel
- JSON dışa aktarım (`serde_json` zaten bağımlılıklarda)
- mDNS / SSDP ile cihaz adı ve servis keşfi
- Kendi trafiğin için `.pcap` dışa aktarımı

## Lisans

MIT
