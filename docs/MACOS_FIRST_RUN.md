# macOS — ilk açılış

GitHub Release dosyası, ilgili işlemciye göre derlenmiş bir `Turtle.app` içerir:

- Apple Silicon: `macos-arm64`
- Intel: `macos-x86_64`

1. Mac'inize uygun `.app.zip` dosyasını indirin ve Finder'da çıkarın.
2. `Turtle.app` dosyasını Applications klasörüne taşıyabilirsiniz.
3. İlk açılışta macOS, uygulama Apple tarafından imzalanmadığı için güvenlik uyarısı gösterebilir. Uygulamayı yalnızca bu projeyi kaynağından/Release sayfasından indirdiğinize eminseniz Finder'da Control-tıklayıp **Aç** seçeneğini kullanarak bir kez onaylayın.
4. Alternatif olarak, uygulamayı Applications klasörüne taşıdıktan sonra Terminal'de `xattr -dr com.apple.quarantine /Applications/Turtle.app` komutunu çalıştırıp normal şekilde açın.

**İmzalama/notarizasyon:** Bu paket Apple Developer sertifikası ve notarizasyonu olmadan üretilir. Dolayısıyla ilk açılışta Gatekeeper onayı gerekebilir. Bu, uygulamanın konsol uygulaması olduğu anlamına gelmez; `Turtle.app` gerçek macOS GUI uygulama paketidir.

Paket yakalama özelliği için Scapy ile birlikte macOS'un paket yakalama izinleri gerekir. Wi-Fi listeleme macOS sürümüne göre Konum/Wi-Fi gizlilik izni isteyebilir.
