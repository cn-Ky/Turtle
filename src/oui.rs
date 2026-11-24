//! MAC adresinden üretici (OUI) bulma.
//! Çalışma dizininde `oui.txt` varsa kullanılır (IEEE formatı veya "AABBCC<TAB>Üretici").
//! Yoksa küçük bir yerleşik liste kullanılır.

use std::collections::HashMap;
use std::fs;

pub struct OuiVeritabani {
    harita: HashMap<String, String>,
}

const YERLESIK: &[(&str, &str)] = &[
    ("001A11", "Google"),
    ("3C5AB4", "Google"),
    ("F4F5D8", "Google"),
    ("001CB3", "Apple"),
    ("A4D1D2", "Apple"),
    ("F0DCE2", "Apple"),
    ("000C29", "VMware"),
    ("080027", "VirtualBox"),
    ("B827EB", "Raspberry Pi"),
    ("DCA632", "Raspberry Pi"),
    ("001018", "Broadcom"),
    ("0050F2", "Microsoft"),
    ("001E58", "D-Link"),
    ("C83A35", "Tenda"),
    ("50C7BF", "TP-Link"),
    ("F4F26D", "TP-Link"),
    ("0026B6", "Askey (Türk Telekom modem)"),
    ("A0F3C1", "TP-Link"),
];

impl OuiVeritabani {
    pub fn yukle() -> Self {
        let mut harita: HashMap<String, String> = YERLESIK
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();

        if let Ok(icerik) = fs::read_to_string("oui.txt") {
            for satir in icerik.lines() {
                // IEEE: "AA-BB-CC   (hex)\t\tÜretici"
                if let Some((on, geri)) = satir.split_once("(hex)") {
                    let anahtar: String = on
                        .chars()
                        .filter(|c| c.is_ascii_hexdigit())
                        .collect::<String>()
                        .to_uppercase();
                    if anahtar.len() == 6 {
                        harita.insert(anahtar, geri.trim().to_string());
                    }
                    continue;
                }
                // Basit: "AABBCC\tÜretici"
                if let Some((on, geri)) = satir.split_once('\t') {
                    let anahtar = on.trim().replace([':', '-'], "").to_uppercase();
                    if anahtar.len() == 6 {
                        harita.insert(anahtar, geri.trim().to_string());
                    }
                }
            }
        }
        Self { harita }
    }

    pub fn uretici(&self, mac: &str) -> String {
        let temiz: String = mac
            .chars()
            .filter(|c| c.is_ascii_hexdigit())
            .collect::<String>()
            .to_uppercase();
        if temiz.len() < 6 {
            return "?".into();
        }
        // Yerel yönetilen (rastgele) MAC: ilk baytın 2. biti
        if let Ok(ilk) = u8::from_str_radix(&temiz[0..2], 16) {
            if ilk & 0x02 != 0 {
                return "Rastgele/yerel MAC (gizlilik özelliği olabilir)".into();
            }
        }
        self.harita
            .get(&temiz[0..6])
            .cloned()
            .unwrap_or_else(|| "Bilinmiyor".into())
    }
}
