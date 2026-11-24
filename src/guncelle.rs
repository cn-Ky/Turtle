//! Otomatik güncelleme: GitHub Releases üzerinden yeni sürüm kontrolü ve kendini güncelleme.
//!
//! * Program çalışırken günde en fazla bir kez, arka planda yeni sürüm var mı diye bakılır.
//! * Yeni sürüm varsa komut bittiğinde kısa bir bildirim yazdırılır (hiçbir şey kendiliğinden kurulmaz).
//! * `turtle guncelle` komutu yeni sürümü indirir ve çalışan dosyanın yerine koyar.
//! * Bildirimi kapatmak için: TURTLE_GUNCELLEME_KONTROLU=0

use anyhow::Result;
use self_update::update::ReleaseUpdate;
use std::fs;
use std::io::{self, Write};
use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

const SAHIP: &str = "cn-Ky";
const DEPO: &str = "Turtle";
const IKILI_AD: &str = "turtle";
const KONTROL_ARALIGI_SN: u64 = 24 * 60 * 60;

fn mevcut_surum() -> &'static str {
    self_update::cargo_crate_version!()
}

fn guncelleyici() -> Result<Box<dyn ReleaseUpdate>> {
    Ok(self_update::backends::github::Update::configure()
        .repo_owner(SAHIP)
        .repo_name(DEPO)
        .bin_name(IKILI_AD)
        .current_version(mevcut_surum())
        .show_output(false)
        .show_download_progress(true)
        .no_confirm(true) // onayı kendimiz (Türkçe) soruyoruz
        .build()?)
}

fn zaman_dosyasi() -> Option<PathBuf> {
    dirs::cache_dir().map(|d| d.join("turtle").join("son_guncelleme_kontrolu"))
}

fn simdi() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn kontrol_gerekli() -> bool {
    if std::env::var("TURTLE_GUNCELLEME_KONTROLU").as_deref() == Ok("0") {
        return false;
    }
    let Some(yol) = zaman_dosyasi() else {
        return false;
    };
    match fs::read_to_string(yol).ok().and_then(|s| s.trim().parse::<u64>().ok()) {
        Some(son) => simdi().saturating_sub(son) >= KONTROL_ARALIGI_SN,
        None => true,
    }
}

fn zaman_kaydet() {
    if let Some(yol) = zaman_dosyasi() {
        if let Some(dizin) = yol.parent() {
            let _ = fs::create_dir_all(dizin);
        }
        let _ = fs::write(yol, simdi().to_string());
    }
}

/// Daha yeni bir sürüm varsa sürüm numarasını döndürür.
fn yeni_surum() -> Result<Option<String>> {
    let son = guncelleyici()?.get_latest_release()?;
    if self_update::version::bump_is_greater(mevcut_surum(), &son.version)? {
        Ok(Some(son.version))
    } else {
        Ok(None)
    }
}

/// Arka planda sessizce kontrol eder. Kontrol gerekmiyorsa `None` döner.
pub fn arka_planda_kontrol() -> Option<Receiver<String>> {
    if !kontrol_gerekli() {
        return None;
    }
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || match yeni_surum() {
        Ok(Some(surum)) => {
            // Güncellenene kadar her çalıştırmada hatırlat: zaman damgası yazılmaz.
            let _ = tx.send(surum);
        }
        Ok(None) => zaman_kaydet(),
        Err(_) => {} // ağ yok vb.: sessizce geç
    });
    Some(rx)
}

/// Komut bittikten sonra, varsa yeni sürüm bildirimini yazdırır.
pub fn bildirimi_goster(rx: Receiver<String>) {
    if let Ok(surum) = rx.recv_timeout(Duration::from_millis(1500)) {
        eprintln!(
            "\n🐢 Yeni sürüm var: v{} (şu an: v{}). Güncellemek için: turtle guncelle",
            surum,
            mevcut_surum()
        );
    }
}

fn onay_al(soru: &str) -> bool {
    print!("{} [E/h] ", soru);
    let _ = io::stdout().flush();
    let mut satir = String::new();
    if io::stdin().read_line(&mut satir).is_err() {
        return false;
    }
    matches!(
        satir.trim().to_lowercase().as_str(),
        "" | "e" | "evet" | "y" | "yes"
    )
}

fn guncelle_senkron(evet: bool) -> Result<()> {
    println!("Güncellemeler denetleniyor (şu anki sürüm: v{})...", mevcut_surum());
    let g = guncelleyici()?;
    let son = g.get_latest_release()?;

    if !self_update::version::bump_is_greater(mevcut_surum(), &son.version)? {
        println!("✔ Zaten en güncel sürümdesin (v{}).", mevcut_surum());
        zaman_kaydet();
        return Ok(());
    }

    println!("Yeni sürüm bulundu: v{}", son.version);
    if !evet && !onay_al("İndirip kurulsun mu?") {
        println!("Güncelleme iptal edildi.");
        return Ok(());
    }

    match g.update() {
        Ok(durum) => {
            println!("✔ v{} sürümüne güncellendi. Programı yeniden çalıştırabilirsin.", durum.version());
            zaman_kaydet();
            Ok(())
        }
        Err(e) => {
            eprintln!("Güncelleme başarısız: {}", e);
            eprintln!(
                "İpucu: Program yazma izni olmayan bir klasördeyse (ör. /usr/local/bin) `sudo turtle guncelle` dene \
                 veya yeni sürümü https://github.com/{}/{}/releases adresinden elle indir.",
                SAHIP, DEPO
            );
            Err(e.into())
        }
    }
}

pub async fn calistir(evet: bool) -> Result<()> {
    // self_update engelleyici (blocking) HTTP kullanır; tokio çalışma zamanından ayrı iş parçacığında çalıştır.
    tokio::task::spawn_blocking(move || guncelle_senkron(evet)).await??;
    Ok(())
}
