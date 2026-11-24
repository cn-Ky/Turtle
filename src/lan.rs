//! Arayüz listesi ve bağlı olunan ağda ARP ile cihaz keşfi.

use crate::oui::OuiVeritabani;
use anyhow::{anyhow, bail, Result};
use colored::Colorize;
use pnet::datalink::{self, Channel, Config, NetworkInterface};
use pnet::packet::arp::{ArpHardwareTypes, ArpOperations, ArpPacket, MutableArpPacket};
use pnet::packet::ethernet::{EtherTypes, EthernetPacket, MutableEthernetPacket};
use pnet::packet::Packet;
use pnet::util::MacAddr;
use std::collections::BTreeMap;
use std::net::{IpAddr, Ipv4Addr};
use std::time::{Duration, Instant};

pub fn arayuzleri_listele() {
    println!("{}", "== Ağ Arayüzleri ==".bold().cyan());
    for a in datalink::interfaces() {
        let durum = if a.is_up() { "AÇIK".green() } else { "KAPALI".red() };
        let mac = a.mac.map(|m| m.to_string()).unwrap_or_else(|| "-".into());
        println!("{}  [{}]  MAC: {}", a.name.bold(), durum, mac);
        for ip in &a.ips {
            println!("    {}", ip);
        }
    }
}

fn arayuz_sec(ad: Option<String>) -> Result<NetworkInterface> {
    let tum = datalink::interfaces();
    if let Some(ad) = ad {
        return tum
            .into_iter()
            .find(|a| a.name == ad)
            .ok_or_else(|| anyhow!("'{}' adlı arayüz bulunamadı", ad));
    }
    tum.into_iter()
        .find(|a| a.is_up() && !a.is_loopback() && a.mac.is_some() && a.ips.iter().any(|i| i.is_ipv4()))
        .ok_or_else(|| anyhow!("Uygun arayüz bulunamadı; --arayuz ile belirt"))
}

pub async fn kesfet(ad: Option<String>) -> Result<()> {
    let arayuz = arayuz_sec(ad)?;
    let mac = arayuz.mac.ok_or_else(|| anyhow!("Arayüzün MAC adresi yok"))?;
    let ag = arayuz
        .ips
        .iter()
        .find_map(|i| match i.ip() {
            IpAddr::V4(v4) => Some((v4, i.prefix())),
            _ => None,
        })
        .ok_or_else(|| anyhow!("Arayüzde IPv4 adresi yok"))?;
    let (kendi_ip, prefix) = ag;

    // Güvenlik: yalnızca özel (LAN) ağlarda ve en fazla /22 boyutunda tara.
    if !kendi_ip.is_private() && !kendi_ip.is_link_local() {
        bail!("Yalnızca özel (LAN) ağlarda keşif yapılır.");
    }
    let prefix = prefix.max(22);
    let maske: u32 = if prefix == 0 { 0 } else { u32::MAX << (32 - prefix) };
    let ag_adresi = u32::from(kendi_ip) & maske;
    let yayin = ag_adresi | !maske;

    println!(
        "{}  {} üzerinde {}/{} taranıyor...",
        "▶".green(),
        arayuz.name.bold(),
        Ipv4Addr::from(ag_adresi),
        prefix
    );

    let cfg = Config { read_timeout: Some(Duration::from_millis(200)), ..Default::default() };
    let (mut tx, mut rx) = match datalink::channel(&arayuz, cfg) {
        Ok(Channel::Ethernet(tx, rx)) => (tx, rx),
        Ok(_) => bail!("Desteklenmeyen kanal türü"),
        Err(e) => bail!("Kanal açılamadı: {} (yönetici/root ve Npcap/libpcap gerekebilir)", e),
    };

    for h in (ag_adresi + 1)..yayin {
        let hedef = Ipv4Addr::from(h);
        if hedef == kendi_ip {
            continue;
        }
        let mut eth_buf = [0u8; 42];
        {
            let mut eth = MutableEthernetPacket::new(&mut eth_buf).unwrap();
            eth.set_destination(MacAddr::broadcast());
            eth.set_source(mac);
            eth.set_ethertype(EtherTypes::Arp);
            let mut arp_buf = [0u8; 28];
            let mut arp = MutableArpPacket::new(&mut arp_buf).unwrap();
            arp.set_hardware_type(ArpHardwareTypes::Ethernet);
            arp.set_protocol_type(EtherTypes::Ipv4);
            arp.set_hw_addr_len(6);
            arp.set_proto_addr_len(4);
            arp.set_operation(ArpOperations::Request);
            arp.set_sender_hw_addr(mac);
            arp.set_sender_proto_addr(kendi_ip);
            arp.set_target_hw_addr(MacAddr::zero());
            arp.set_target_proto_addr(hedef);
            eth.set_payload(arp.packet());
        }
        if let Some(Err(e)) = tx.send_to(&eth_buf, None) {
            eprintln!("Gönderim hatası: {}", e);
            break;
        }
    }

    let mut bulunan: BTreeMap<Ipv4Addr, MacAddr> = BTreeMap::new();
    let bitis = Instant::now() + Duration::from_secs(3);
    while Instant::now() < bitis {
        match rx.next() {
            Ok(veri) => {
                if let Some(eth) = EthernetPacket::new(veri) {
                    if eth.get_ethertype() == EtherTypes::Arp {
                        if let Some(arp) = ArpPacket::new(eth.payload()) {
                            if arp.get_operation() == ArpOperations::Reply {
                                bulunan.insert(arp.get_sender_proto_addr(), arp.get_sender_hw_addr());
                            }
                        }
                    }
                }
            }
            Err(_) => continue, // zaman aşımı
        }
    }

    let oui = OuiVeritabani::yukle();
    println!("\n{:<16} {:<19} {:<30} {}", "IP", "MAC", "ÜRETİCİ", "ANA BİLGİSAYAR ADI");
    for (ip, m) in &bulunan {
        let m_str = m.to_string();
        let ad = dns_lookup::lookup_addr(&IpAddr::V4(*ip)).unwrap_or_else(|_| "-".into());
        println!("{:<16} {:<19} {:<30} {}", ip, m_str, oui.uretici(&m_str), ad);
    }
    println!("\n{} cihaz bulundu.", bulunan.len().to_string().bold().green());
    Ok(())
}
