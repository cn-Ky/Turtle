//! Basit, eşzamanlı TCP connect taraması.
//! Özel (LAN) olmayan hedefler için `--yetkili` bayrağı zorunludur.

use anyhow::{bail, Result};
use colored::Colorize;
use std::net::{IpAddr, SocketAddr};
use std::sync::Arc;
use std::time::Duration;
use tokio::net::TcpStream;
use tokio::sync::Semaphore;
use tokio::time::timeout;

fn ozel_mi(ip: &IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => v4.is_private() || v4.is_loopback() || v4.is_link_local(),
        IpAddr::V6(v6) => v6.is_loopback() || (v6.segments()[0] & 0xfe00) == 0xfc00,
    }
}

fn aralik_coz(s: &str) -> Result<Vec<u16>> {
    let mut sonuc = Vec::new();
    for parca in s.split(',') {
        let parca = parca.trim();
        if let Some((a, b)) = parca.split_once('-') {
            let (a, b): (u16, u16) = (a.parse()?, b.parse()?);
            if a > b {
                bail!("Geçersiz aralık: {}", parca);
            }
            sonuc.extend(a..=b);
        } else {
            sonuc.push(parca.parse()?);
        }
    }
    sonuc.sort_unstable();
    sonuc.dedup();
    Ok(sonuc)
}

fn servis(port: u16) -> &'static str {
    match port {
        21 => "ftp",
        22 => "ssh",
        23 => "telnet",
        25 => "smtp",
        53 => "dns",
        80 => "http",
        110 => "pop3",
        143 => "imap",
        443 => "https",
        445 => "smb",
        3306 => "mysql",
        3389 => "rdp",
        5432 => "postgresql",
        8080 => "http-alt",
        _ => "-",
    }
}

pub async fn tara(hedef: IpAddr, aralik: &str, yetkili: bool) -> Result<()> {
    if !ozel_mi(&hedef) && !yetkili {
        bail!(
            "{} özel (LAN) bir adres değil. Yalnızca yazılı izniniz olan sistemleri tarayabilirsiniz; \
             onaylıyorsanız --yetkili bayrağını ekleyin.",
            hedef
        );
    }
    let portlar = aralik_coz(aralik)?;
    println!("{} {} üzerinde {} port taranıyor...", "▶".green(), hedef, portlar.len());

    let sinir = Arc::new(Semaphore::new(256));
    let mut isler = Vec::new();
    for p in portlar {
        let izin = sinir.clone().acquire_owned().await?;
        isler.push(tokio::spawn(async move {
            let _izin = izin;
            let adres = SocketAddr::new(hedef, p);
            let acik = matches!(timeout(Duration::from_millis(800), TcpStream::connect(adres)).await, Ok(Ok(_)));
            (p, acik)
        }));
    }

    let mut acik_portlar = Vec::new();
    for is in isler {
        let (p, acik) = is.await?;
        if acik {
            acik_portlar.push(p);
        }
    }
    acik_portlar.sort_unstable();

    println!("\n{:<8} {}", "PORT", "SERVİS");
    for p in &acik_portlar {
        println!("{:<8} {}", p.to_string().green(), servis(*p));
    }
    println!("\n{} açık port bulundu.", acik_portlar.len().to_string().bold().green());
    Ok(())
}
