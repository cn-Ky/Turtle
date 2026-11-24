//! Çevredeki Wi-Fi ağlarının pasif listesi.
//! İşletim sisteminin kendi tarama aracını kullanır; paket enjeksiyonu / deauth YOKTUR.

use anyhow::{bail, Result};
use colored::Colorize;
use std::process::Command;

pub fn goster() -> Result<()> {
    println!("{}", "== Çevredeki Wi-Fi Ağları ==".bold().cyan());

    #[cfg(target_os = "linux")]
    return linux();
    #[cfg(target_os = "windows")]
    return windows();
    #[cfg(target_os = "macos")]
    return macos();
    #[allow(unreachable_code)]
    {
        bail!("Bu işletim sistemi desteklenmiyor");
    }
}

#[cfg(target_os = "linux")]
fn linux() -> Result<()> {
    let cikti = Command::new("nmcli")
        .args(["-t", "-f", "SSID,BSSID,CHAN,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"])
        .output();
    let cikti = match cikti {
        Ok(c) if c.status.success() => c,
        _ => bail!("nmcli bulunamadı veya çalışmadı. NetworkManager kurulu mu?"),
    };
    let metin = String::from_utf8_lossy(&cikti.stdout);
    println!("{:<28} {:<18} {:>4} {:>6}  {}", "SSID", "BSSID", "KNL", "SİNYAL", "GÜVENLİK");
    for satir in metin.lines() {
        // nmcli -t, ':' ile ayırır; BSSID içindeki ':' '\:' olarak kaçırılır.
        let temiz = satir.replace("\\:", "\u{1}");
        let p: Vec<String> = temiz.split(':').map(|s| s.replace('\u{1}', ":")).collect();
        if p.len() < 5 {
            continue;
        }
        let ssid = if p[0].is_empty() { "<gizli ağ>" } else { &p[0] };
        let guvenlik = if p[4].is_empty() { "AÇIK".red().to_string() } else { p[4].clone() };
        println!("{:<28} {:<18} {:>4} {:>5}%  {}", ssid, p[1], p[2], p[3], guvenlik);
    }
    Ok(())
}

#[cfg(target_os = "windows")]
fn windows() -> Result<()> {
    let cikti = Command::new("netsh")
        .args(["wlan", "show", "networks", "mode=bssid"])
        .output()?;
    println!("{}", String::from_utf8_lossy(&cikti.stdout));
    Ok(())
}

#[cfg(target_os = "macos")]
fn macos() -> Result<()> {
    let cikti = Command::new("system_profiler").arg("SPAirPortDataType").output()?;
    println!("{}", String::from_utf8_lossy(&cikti.stdout));
    println!("{}", "Not: Yeni macOS sürümlerinde SSID listesi için Konum İzni gerekebilir.".yellow());
    Ok(())
}
