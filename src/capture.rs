//! Kendi arayüzünde başlık düzeyinde paket yakalama.
//! Yük (payload) içeriği ASLA yazdırılmaz — yalnızca L2/L3/L4 başlık özeti gösterilir.

use anyhow::{bail, Result};
use colored::Colorize;
use pnet::datalink::{self, Channel, Config};
use pnet::packet::arp::ArpPacket;
use pnet::packet::ethernet::{EtherTypes, EthernetPacket};
use pnet::packet::icmp::IcmpPacket;
use pnet::packet::ip::{IpNextHeaderProtocol, IpNextHeaderProtocols};
use pnet::packet::ipv4::Ipv4Packet;
use pnet::packet::ipv6::Ipv6Packet;
use pnet::packet::tcp::TcpPacket;
use pnet::packet::udp::UdpPacket;
use pnet::packet::Packet;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

enum Filtre {
    Yok,
    Tcp,
    Udp,
    Icmp,
    Arp,
    Dns,
    Port(u16),
}

fn filtre_coz(f: Option<String>) -> Result<Filtre> {
    Ok(match f.as_deref() {
        None => Filtre::Yok,
        Some("tcp") => Filtre::Tcp,
        Some("udp") => Filtre::Udp,
        Some("icmp") => Filtre::Icmp,
        Some("arp") => Filtre::Arp,
        Some("dns") => Filtre::Dns,
        Some(s) if s.starts_with("port:") => Filtre::Port(s[5..].parse()?),
        Some(s) => bail!("Bilinmeyen filtre: {}", s),
    })
}

struct Ozet {
    protokol: &'static str,
    kaynak: String,
    hedef: String,
    bilgi: String,
    portlar: (u16, u16),
}

fn katman4(proto: IpNextHeaderProtocol, veri: &[u8]) -> (&'static str, String, (u16, u16)) {
    match proto {
        IpNextHeaderProtocols::Tcp => {
            if let Some(t) = TcpPacket::new(veri) {
                let mut bayrak = String::new();
                let b = t.get_flags();
                for (bit, ad) in [(0x02, "SYN"), (0x10, "ACK"), (0x01, "FIN"), (0x04, "RST"), (0x08, "PSH")] {
                    if b & bit != 0 {
                        bayrak.push_str(ad);
                        bayrak.push(' ');
                    }
                }
                return (
                    "TCP",
                    format!("{} → {} [{}] uzunluk={}", t.get_source(), t.get_destination(), bayrak.trim(), veri.len()),
                    (t.get_source(), t.get_destination()),
                );
            }
            ("TCP", "kısa paket".into(), (0, 0))
        }
        IpNextHeaderProtocols::Udp => {
            if let Some(u) = UdpPacket::new(veri) {
                let ad = if u.get_source() == 53 || u.get_destination() == 53 { "DNS" } else { "UDP" };
                return (
                    ad,
                    format!("{} → {} uzunluk={}", u.get_source(), u.get_destination(), u.get_length()),
                    (u.get_source(), u.get_destination()),
                );
            }
            ("UDP", "kısa paket".into(), (0, 0))
        }
        IpNextHeaderProtocols::Icmp | IpNextHeaderProtocols::Icmpv6 => {
            let tip = IcmpPacket::new(veri).map(|i| i.get_icmp_type().0).unwrap_or(0);
            ("ICMP", format!("tip={}", tip), (0, 0))
        }
        _ => ("DİĞER", format!("protokol={}", proto), (0, 0)),
    }
}

fn coz(veri: &[u8]) -> Option<Ozet> {
    let eth = EthernetPacket::new(veri)?;
    match eth.get_ethertype() {
        EtherTypes::Arp => {
            let a = ArpPacket::new(eth.payload())?;
            let islem = if a.get_operation().0 == 1 { "kim bu?" } else { "cevap" };
            Some(Ozet {
                protokol: "ARP",
                kaynak: a.get_sender_proto_addr().to_string(),
                hedef: a.get_target_proto_addr().to_string(),
                bilgi: islem.into(),
                portlar: (0, 0),
            })
        }
        EtherTypes::Ipv4 => {
            let ip = Ipv4Packet::new(eth.payload())?;
            let (p, bilgi, portlar) = katman4(ip.get_next_level_protocol(), ip.payload());
            Some(Ozet { protokol: p, kaynak: ip.get_source().to_string(), hedef: ip.get_destination().to_string(), bilgi, portlar })
        }
        EtherTypes::Ipv6 => {
            let ip = Ipv6Packet::new(eth.payload())?;
            let (p, bilgi, portlar) = katman4(ip.get_next_header(), ip.payload());
            Some(Ozet { protokol: p, kaynak: ip.get_source().to_string(), hedef: ip.get_destination().to_string(), bilgi, portlar })
        }
        _ => None,
    }
}

fn uygun(f: &Filtre, o: &Ozet) -> bool {
    match f {
        Filtre::Yok => true,
        Filtre::Tcp => o.protokol == "TCP",
        Filtre::Udp => o.protokol == "UDP" || o.protokol == "DNS",
        Filtre::Icmp => o.protokol == "ICMP",
        Filtre::Arp => o.protokol == "ARP",
        Filtre::Dns => o.protokol == "DNS",
        Filtre::Port(p) => o.portlar.0 == *p || o.portlar.1 == *p,
    }
}

pub fn yakala(arayuz_adi: &str, sayi: usize, filtre: Option<String>) -> Result<()> {
    let filtre = filtre_coz(filtre)?;
    let arayuz = match datalink::interfaces().into_iter().find(|a| a.name == arayuz_adi) {
        Some(a) => a,
        None => bail!("'{}' bulunamadı. `agtarayici arayuzler` ile listele.", arayuz_adi),
    };
    let cfg = Config { read_timeout: Some(Duration::from_millis(250)), ..Default::default() };
    let mut rx = match datalink::channel(&arayuz, cfg) {
        Ok(Channel::Ethernet(_, rx)) => rx,
        Ok(_) => bail!("Desteklenmeyen kanal türü"),
        Err(e) => bail!("Kanal açılamadı: {} (yönetici/root ve Npcap/libpcap gerekebilir)", e),
    };

    let calisiyor = Arc::new(AtomicBool::new(true));
    let c = calisiyor.clone();
    ctrlc::set_handler(move || c.store(false, Ordering::SeqCst))?;

    println!("{} {} dinleniyor (durdurmak için Ctrl+C). Yalnızca başlık özeti gösterilir.", "▶".green(), arayuz.name.bold());
    let mut toplam = 0usize;
    while calisiyor.load(Ordering::SeqCst) {
        match rx.next() {
            Ok(veri) => {
                if let Some(o) = coz(veri) {
                    if !uygun(&filtre, &o) {
                        continue;
                    }
                    toplam += 1;
                    let renkli = match o.protokol {
                        "TCP" => o.protokol.blue(),
                        "UDP" => o.protokol.cyan(),
                        "DNS" => o.protokol.magenta(),
                        "ARP" => o.protokol.yellow(),
                        _ => o.protokol.normal(),
                    };
                    println!("{:>6}  {:<5} {:<40} → {:<40} {}", toplam, renkli, o.kaynak, o.hedef, o.bilgi);
                    if sayi != 0 && toplam >= sayi {
                        break;
                    }
                }
            }
            Err(_) => continue, // zaman aşımı; Ctrl+C kontrolü için döngü devam eder
        }
    }
    println!("\nToplam {} paket gösterildi.", toplam);
    Ok(())
}
