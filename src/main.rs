//! Turtle — eğitim amaçlı, Türkçe ağ analiz aracı.
//!
//! Tasarım ilkeleri:
//!  * Wi-Fi taraması pasiftir (işletim sisteminin kendi taramasını kullanır).
//!  * Yerel ağ keşfi yalnızca BAĞLI OLDUĞUN ağda çalışır.
//!  * Paket yakalama yalnızca başlık bilgisini gösterir; içerik (payload) yazdırılmaz.
//!  * Port tarama, özel (LAN) olmayan hedeflerde açık `--yetkili` onayı ister.

mod capture;
mod guncelle;
mod lan;
mod oui;
mod ports;
mod wifi;

use anyhow::Result;
use clap::{Parser, Subcommand};
use std::net::IpAddr;

#[derive(Parser)]
#[command(
    name = "turtle",
    version,
    about = "Eğitim amaçlı, Türkçe ağ analiz aracı: Wi-Fi, yerel ağ keşfi, paket yakalama, port tarama"
)]
struct Cli {
    #[command(subcommand)]
    komut: Komut,
}

#[derive(Subcommand)]
enum Komut {
    /// Ağ arayüzlerini listele
    Arayuzler,
    /// Çevredeki Wi-Fi ağlarını (pasif) listele
    Wifi,
    /// Bağlı olduğun yerel ağdaki cihazları keşfet
    Lan {
        /// Arayüz adı (boşsa otomatik seçilir)
        #[arg(long)]
        arayuz: Option<String>,
    },
    /// Kendi arayüzünde başlık düzeyinde paket yakala (yönetici/root gerekir)
    Yakala {
        /// Arayüz adı (bkz. `arayuzler`)
        arayuz: String,
        /// Kaç paketten sonra dursun (0 = Ctrl+C'ye kadar)
        #[arg(long, default_value_t = 0)]
        sayi: usize,
        /// Filtre: tcp, udp, icmp, arp, dns veya port:443
        #[arg(long)]
        filtre: Option<String>,
    },
    /// Hedefte açık TCP portlarını tara
    Port {
        hedef: IpAddr,
        /// Örn: 1-1024 veya 22,80,443
        #[arg(long, default_value = "1-1024")]
        aralik: String,
        /// Özel olmayan (internet) adresler için yazılı yetkin olduğunu onayla
        #[arg(long)]
        yetkili: bool,
    },
    /// Yeni sürüm var mı diye bak ve varsa kendini güncelle
    Guncelle {
        /// Onay sormadan güncelle
        #[arg(long)]
        evet: bool,
    },
}

fn uyari() {
    eprintln!(
        "ℹ  Bu araç eğitim amaçlıdır. Yalnızca kendi ağında veya yazılı izin aldığın sistemlerde kullan.\n   \
         İzinsiz tarama/dinleme TCK 132, 133, 243, 244 ve KVKK kapsamında suç/ihlal olabilir.\n"
    );
}

async fn calistir(komut: Komut) -> Result<()> {
    match komut {
        Komut::Arayuzler => lan::arayuzleri_listele(),
        Komut::Wifi => wifi::goster()?,
        Komut::Lan { arayuz } => lan::kesfet(arayuz).await?,
        Komut::Yakala { arayuz, sayi, filtre } => capture::yakala(&arayuz, sayi, filtre)?,
        Komut::Port { hedef, aralik, yetkili } => ports::tara(hedef, &aralik, yetkili).await?,
        Komut::Guncelle { evet } => guncelle::calistir(evet).await?,
    }
    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    uyari();

    // `guncelle` komutu zaten kendi kontrolünü yapar; diğer komutlarda arka planda bakılır.
    let bildirim = if matches!(cli.komut, Komut::Guncelle { .. }) {
        None
    } else {
        guncelle::arka_planda_kontrol()
    };

    let sonuc = calistir(cli.komut).await;

    if let Some(rx) = bildirim {
        guncelle::bildirimi_goster(rx);
    }
    sonuc
}
