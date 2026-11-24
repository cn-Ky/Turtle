# Turtle GUI — Network Explorer

Turtle, Windows, macOS ve Linux üzerinde çalışan Türkçe masaüstü ağ keşif ve analiz aracıdır. Bu depo sürümü Python/Tkinter GUI uygulamasıdır; GitHub Actions artık Rust konsol ikilisi üretmez. Release iş akışı PyInstaller kullanarak doğrudan açılabilen platforma özgü GUI uygulamalarını paketler.

## Özellikler

- **Genel Bakış:** Uygulama modüllerine ve güvenlik notlarına hızlı erişim.
- **Ağ Arayüzleri:** Arayüz adı, bağlantı durumu, IPv4 ve MAC adresleri.
- **Wi-Fi Ağları:** İşletim sisteminin yerel aracıyla yakındaki kablosuz ağların listelenmesi.
- **Yerel Ağ Keşfi:** Yalnızca bağlı olunan özel IPv4 ağında, en fazla `/22` sınırıyla cihaz keşfi.
- **Paket İzleme:** Scapy ile TCP/UDP/DNS/ICMP/ARP başlık metaverisi. Paket payload'ı okunmaz, kaydedilmez veya gösterilmez.
- **Port Analizi:** TCP port kontrolü; özel olmayan hedefler için açık yetki onayı gerekir. Tek tarama en fazla 4096 portla sınırlıdır.

## GitHub Actions çıktıları

`main` dalına push yapıldığında dört hedef derlenir ve otomatik olarak bir **development prerelease** oluşturulur. `v*` biçiminde Git etiketi gönderildiğinde normal GitHub Release oluşturulur.

| Release dosyası | İçerik |
|---|---|
| `Turtle-GUI-*-macos-arm64.app.zip` | Apple Silicon için gerçek `Turtle.app` |
| `Turtle-GUI-*-macos-x86_64.app.zip` | Intel Mac için gerçek `Turtle.app` |
| `Turtle-GUI-*-windows-x86_64.zip` | Konsol penceresi açmayan `Turtle.exe` |
| `Turtle-GUI-*-linux-x86_64.tar.gz` | Linux GUI çalıştırılabilir dosyası |
| `SHA256SUMS.txt` | Release dosyalarının SHA-256 özetleri |

macOS `.app` paketleri, PyInstaller tarafından GUI uygulaması olarak üretilir (`--windowed`). macOS paketleri Apple Developer sertifikası olmadan imzalanmamış/notarize edilmemiştir; ilk açılış için [macOS ilk açılış yönergesine](docs/MACOS_FIRST_RUN.md) bakın.

## Kaynak koddan çalıştırma

Python 3.10 veya üzeri ve Tkinter gerekir.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

İsterseniz `./run.sh` başlatıcısını kullanabilirsiniz.

### Windows

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

`run.bat` başlatıcısı da aynı işlemi otomatik yapar.

## Paket yakalama gereksinimleri

Scapy Python bağımlılığı pakete dahil edilir. Ancak işletim sisteminin paket yakalama katmanı ayrıca gerekir:

- Windows: Npcap ve uygun kullanıcı yetkisi.
- macOS: paket yakalama için gerekli sistem izinleri/yetkileri.
- Linux: libpcap ve uygun yetkiler (dağıtıma göre `sudo`/capabilities gerekebilir).

Wi-Fi listesi, işletim sisteminin kendi komutlarını kullanır. Linux üzerinde NetworkManager/`nmcli` gerekir. macOS'ta Wi-Fi/Konum gizlilik izni istenebilir.

## Manuel GUI paketlemesi

Derleme bağımlılıklarını kurun:

```bash
python -m pip install -r requirements-build.txt
```

macOS:

```bash
pyinstaller --noconfirm --clean --windowed --onedir --name Turtle \
  --osx-bundle-identifier com.cnky.turtle --collect-all scapy app.py
```

Windows / Linux:

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name Turtle \
  --collect-all scapy app.py
```

## Güvenlik ve yetkili kullanım

Bu araç yalnızca kendi ağınızda veya yazılı izin aldığınız sistemlerde kullanılmalıdır. LAN keşfi bağlı olunan özel IPv4 alt ağıyla sınırlıdır ve en fazla `/22` adres alanı kontrol eder. Genel/özel olmayan IP adreslerinde port taraması, kullanıcı açık yetki onayı vermeden başlamaz. Port taraması tek seferde en fazla 4096 portla sınırlıdır. Paket izleme yalnızca protokol, adres ve port gibi başlık metaverisini listeler; payload içeriğini okumaz, kaydetmez veya göstermez.

## Sürüm ve lisans

GUI sürümü: `1.1.0`  
Lisans: MIT (`LICENSE`).
