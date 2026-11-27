use flate2::read::GzDecoder;
use serde::Deserialize;
use std::collections::HashMap;
use std::io::Read;

const MAX_PHONEMES: usize = 510;
const US_LEXICON_GZ: &[u8] = include_bytes!("../../assets/misaki_us.tsv.gz");
const GB_LEXICON_GZ: &[u8] = include_bytes!("../../assets/misaki_gb.tsv.gz");
const PARADEE_CONFIG_JSON: &str = include_str!("../../assets/paradee_config.json");

#[derive(Deserialize)]
struct ParadeeModelConfig {
    voices: Vec<String>,
    vocab: HashMap<String, i64>,
}

pub struct MisakiG2p {
    us_lexicon: HashMap<String, String>,
    gb_lexicon: HashMap<String, String>,
    vocab: HashMap<char, i64>,
    voices: Vec<String>,
}

impl MisakiG2p {
    pub fn load_embedded() -> Result<Self, String> {
        let cfg: ParadeeModelConfig = serde_json::from_str(PARADEE_CONFIG_JSON)
            .map_err(|e| format!("Failed to parse paradee_config.json: {e}"))?;

        let mut vocab = HashMap::with_capacity(cfg.vocab.len());
        for (k, v) in cfg.vocab {
            if let Some(ch) = k.chars().next() {
                vocab.insert(ch, v);
            }
        }

        let us_lexicon = Self::decode_tsv_gz(US_LEXICON_GZ)?;
        let gb_lexicon = Self::decode_tsv_gz(GB_LEXICON_GZ)?;

        Ok(Self {
            us_lexicon,
            gb_lexicon,
            vocab,
            voices: cfg.voices,
        })
    }

    fn decode_tsv_gz(bytes: &[u8]) -> Result<HashMap<String, String>, String> {
        let mut decoder = GzDecoder::new(bytes);
        let mut raw = String::new();
        decoder
            .read_to_string(&mut raw)
            .map_err(|e| format!("Failed to decompress Misaki lexicon: {e}"))?;

        let mut map = HashMap::with_capacity(200_000);
        for line in raw.lines() {
            if let Some((word, phonemes)) = line.split_once('\t') {
                map.insert(word.to_string(), phonemes.to_string());
            }
        }
        Ok(map)
    }

    pub fn voice_index(&self, voice_name: &str) -> i64 {
        self.voices
            .iter()
            .position(|v| v == voice_name)
            .unwrap_or(1) as i64 // default bf_isabella = 1
    }

    /// Splits input text into readable sentences matching Paradee's chunking rules.
    pub fn split_sentences(text: &str) -> Vec<String> {
        let mut out = Vec::new();
        let mut current = String::new();
        let chars: Vec<char> = text.trim().chars().collect();
        let mut i = 0;

        while i < chars.len() {
            let c = chars[i];
            if c == '\n' || c == '\r' {
                let s = current.trim().to_string();
                if !s.is_empty() {
                    out.push(s);
                }
                current.clear();
                i += 1;
                continue;
            }
            current.push(c);
            if matches!(c, '.' | '!' | '?' | '…') {
                let next_is_ws = i + 1 >= chars.len() || chars[i + 1].is_whitespace();
                if next_is_ws {
                    let s = current.trim().to_string();
                    if !s.is_empty() {
                        out.push(s);
                    }
                    current.clear();
                }
            }
            i += 1;
        }

        let rem = current.trim().to_string();
        if !rem.is_empty() {
            out.push(rem);
        }
        out
    }

    /// Converts a sentence into one or more token ID vectors (each wrapped with 0 BOS/EOS, len <= 512).
    pub fn text_to_token_chunks(&self, sentence: &str, british: bool) -> Vec<Vec<i64>> {
        let phonemes = self.phonemize_sentence(sentence, british);
        if phonemes.is_empty() {
            return Vec::new();
        }

        let mut chunks = Vec::new();
        let mut rest = phonemes.as_str();

        while !rest.is_empty() {
            let char_count = rest.chars().count();
            let piece = if char_count <= MAX_PHONEMES {
                let p = rest;
                rest = "";
                p
            } else {
                // Find byte offset of <= MAX_PHONEMES chars, breaking cleanly at space
                let limit_byte = rest
                    .char_indices()
                    .nth(MAX_PHONEMES)
                    .map(|(idx, _)| idx)
                    .unwrap_or(rest.len());
                let slice = &rest[..limit_byte];
                let cut_byte = slice.rfind(' ').filter(|&pos| pos > 0).unwrap_or(limit_byte);
                let p = &rest[..cut_byte];
                rest = rest[cut_byte..].trim_start();
                p
            };

            let mut ids = Vec::with_capacity(piece.chars().count() + 2);
            ids.push(0);
            for ch in piece.chars() {
                if let Some(&id) = self.vocab.get(&ch) {
                    ids.push(id);
                }
            }
            ids.push(0);

            if ids.len() > 2 {
                chunks.push(ids);
            }
        }

        chunks
    }

    pub fn phonemize_sentence(&self, sentence: &str, british: bool) -> String {
        let normalized = Self::normalize_text(sentence);
        let lex = if british {
            &self.gb_lexicon
        } else {
            &self.us_lexicon
        };

        let mut out = String::new();
        let chars: Vec<char> = normalized.chars().collect();
        let mut i = 0;

        while i < chars.len() {
            let c = chars[i];
            if c.is_whitespace() {
                if !out.is_empty() && !out.ends_with(' ') {
                    out.push(' ');
                }
                i += 1;
                continue;
            }

            if Self::is_word_start(c) {
                let start = i;
                i += 1;
                while i < chars.len()
                    && (chars[i].is_alphanumeric()
                        || chars[i] == '\''
                        || chars[i] == '’'
                        || chars[i] == '-')
                {
                    i += 1;
                }
                // Trim trailing hyphens/apostrophes back if standalone
                let word: String = chars[start..i].iter().collect();
                let word_clean = word.replace('’', "'");
                let ps = self.phonemize_word_or_compound(&word_clean, lex, british);
                if !ps.is_empty() {
                    if !out.is_empty() && !out.ends_with(' ') && !out.ends_with('“') && !out.ends_with('(') {
                        out.push(' ');
                    }
                    out.push_str(&ps);
                }
                continue;
            }

            // Punctuation kept directly if in vocab
            let mapped = match c {
                '\'' | '`' => None,
                '–' => Some('—'),
                _ if self.vocab.contains_key(&c) => Some(c),
                _ => None,
            };
            if let Some(p) = mapped {
                out.push(p);
            }
            i += 1;
        }

        out.trim().to_string()
    }

    fn is_word_start(c: char) -> bool {
        c.is_alphanumeric()
    }

    fn normalize_text(text: &str) -> String {
        let mut out = String::with_capacity(text.len() + 16);
        let chars: Vec<char> = text.chars().collect();
        let mut i = 0;

        while i < chars.len() {
            let c = chars[i];
            // Handle simple currencies like $25
            if matches!(c, '$' | '£' | '€')
                && i + 1 < chars.len()
                && chars[i + 1].is_ascii_digit()
            {
                let unit = match c {
                    '$' => "dollars",
                    '£' => "pounds",
                    '€' => "euros",
                    _ => "",
                };
                i += 1;
                let num_start = i;
                while i < chars.len() && (chars[i].is_ascii_digit() || chars[i] == '.') {
                    i += 1;
                }
                let num_str: String = chars[num_start..i].iter().collect();
                out.push_str(&Self::expand_number_str(&num_str));
                out.push(' ');
                out.push_str(unit);
                out.push(' ');
                continue;
            }

            if c.is_ascii_digit() {
                let start = i;
                while i < chars.len() && (chars[i].is_ascii_digit() || chars[i] == ',') {
                    i += 1;
                }
                // Check decimals
                if i + 1 < chars.len() && chars[i] == '.' && chars[i + 1].is_ascii_digit() {
                    i += 1;
                    while i < chars.len() && chars[i].is_ascii_digit() {
                        i += 1;
                    }
                }
                let num_str: String = chars[start..i].iter().filter(|&&ch| ch != ',').collect();
                out.push_str(&Self::expand_number_str(&num_str));
                continue;
            }

            match c {
                '%' => out.push_str(" percent "),
                '&' => out.push_str(" and "),
                '+' => out.push_str(" plus "),
                '@' => out.push_str(" at "),
                '/' => out.push(' '),
                '_' => out.push(' '),
                _ => out.push(c),
            }
            i += 1;
        }
        out
    }

    fn expand_number_str(s: &str) -> String {
        if let Some((whole, frac)) = s.split_once('.') {
            let mut res = Self::number_to_words(whole.parse::<u64>().unwrap_or(0));
            res.push_str(" point");
            for ch in frac.chars() {
                if let Some(d) = ch.to_digit(10) {
                    res.push(' ');
                    res.push_str(Self::digit_word(d as u64));
                }
            }
            res
        } else if let Ok(n) = s.parse::<u64>() {
            Self::number_to_words(n)
        } else {
            s.chars()
                .filter_map(|c| c.to_digit(10).map(|d| Self::digit_word(d as u64)))
                .collect::<Vec<_>>()
                .join(" ")
        }
    }

    fn digit_word(d: u64) -> &'static str {
        match d {
            0 => "zero",
            1 => "one",
            2 => "two",
            3 => "three",
            4 => "four",
            5 => "five",
            6 => "six",
            7 => "seven",
            8 => "eight",
            9 => "nine",
            _ => "",
        }
    }

    fn number_to_words(n: u64) -> String {
        if n == 0 {
            return "zero".to_string();
        }
        const ONES: [&str; 20] = [
            "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
            "eighteen", "nineteen",
        ];
        const TENS: [&str; 10] = [
            "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
        ];

        fn below_1000(num: u64) -> String {
            let mut parts = Vec::new();
            let hundreds = num / 100;
            let rem = num % 100;
            if hundreds > 0 {
                parts.push(ONES[hundreds as usize].to_string());
                parts.push("hundred".to_string());
            }
            if rem >= 20 {
                let t = TENS[(rem / 10) as usize];
                let o = ONES[(rem % 10) as usize];
                if o.is_empty() {
                    parts.push(t.to_string());
                } else {
                    parts.push(format!("{t} {o}"));
                }
            } else if rem > 0 {
                parts.push(ONES[rem as usize].to_string());
            }
            parts.join(" ")
        }

        let scales = [(1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")];
        let mut rem = n;
        let mut parts = Vec::new();
        for (div, label) in scales {
            if rem >= div {
                parts.push(below_1000(rem / div));
                parts.push(label.to_string());
                rem %= div;
            }
        }
        if rem > 0 {
            parts.push(below_1000(rem));
        }
        parts.join(" ")
    }

    fn phonemize_word_or_compound(
        &self,
        raw: &str,
        lex: &HashMap<String, String>,
        british: bool,
    ) -> String {
        let trimmed = raw.trim_matches(|c: char| !c.is_alphanumeric());
        if trimmed.is_empty() {
            return String::new();
        }
        if let Some(hit) = self.lookup_word(trimmed, lex, british) {
            return hit;
        }
        if trimmed.contains('-') {
            let parts: Vec<String> = trimmed
                .split('-')
                .filter(|p| !p.is_empty())
                .map(|p| self.phonemize_word_or_compound(p, lex, british))
                .filter(|p| !p.is_empty())
                .collect();
            if !parts.is_empty() {
                return parts.join(" ");
            }
        }
        Self::fallback_lts(trimmed, british)
    }

    fn lookup_direct(word: &str, lex: &HashMap<String, String>) -> Option<String> {
        if let Some(p) = lex.get(word) {
            return Some(p.clone());
        }
        let lower = word.to_ascii_lowercase();
        if let Some(p) = lex.get(&lower) {
            return Some(p.clone());
        }
        // Try Title Case in dictionary
        let mut chars = lower.chars();
        if let Some(first) = chars.next() {
            let titled = format!("{}{}", first.to_ascii_uppercase(), chars.as_str());
            if let Some(p) = lex.get(&titled) {
                return Some(p.clone());
            }
        }
        None
    }

    fn lookup_word(&self, word: &str, lex: &HashMap<String, String>, british: bool) -> Option<String> {
        if let Some(p) = Self::lookup_direct(word, lex) {
            return Some(p);
        }

        // Acronym spell-out (2..=5 uppercase letters not found in lexicon, e.g. STT, TTS, HUD)
        if (2..=5).contains(&word.len()) && word.chars().all(|c| c.is_ascii_uppercase()) {
            let mut letters = Vec::new();
            let mut ok = true;
            for ch in word.chars() {
                let s = ch.to_string();
                if let Some(lp) = Self::lookup_direct(&s, lex) {
                    letters.push(lp);
                } else {
                    ok = false;
                    break;
                }
            }
            if ok && !letters.is_empty() {
                return Some(letters.join(" "));
            }
        }

        // Possessive / common suffix stemming (matching Misaki suffix voicing rules)
        let lower = word.to_ascii_lowercase();
        if let Some(stem) = lower.strip_suffix("'s") {
            if let Some(base) = Self::lookup_direct(stem, lex) {
                return Some(Self::append_sibilant(&base));
            }
        }
        if let Some(stem) = lower.strip_suffix("n't") {
            if let Some(base) = Self::lookup_direct(stem, lex) {
                return Some(format!("{base}nt"));
            }
        }
        if let Some(stem) = lower.strip_suffix("s") {
            if stem.len() >= 2 {
                if let Some(base) = Self::lookup_direct(stem, lex) {
                    return Some(Self::append_sibilant(&base));
                }
            }
        }
        if let Some(stem) = lower.strip_suffix("es") {
            if stem.len() >= 2 {
                if let Some(base) = Self::lookup_direct(stem, lex) {
                    return Some(Self::append_sibilant(&base));
                }
            }
        }
        if let Some(stem) = lower.strip_suffix("ed") {
            if stem.len() >= 2 {
                let base_opt = Self::lookup_direct(stem, lex)
                    .or_else(|| Self::lookup_direct(&format!("{stem}e"), lex))
                    .or_else(|| {
                        Self::undouble_consonant(stem)
                            .and_then(|s| Self::lookup_direct(s, lex))
                    });
                if let Some(base) = base_opt {
                    return Some(Self::append_ed(&base));
                }
            }
        }
        if let Some(stem) = lower.strip_suffix("ing") {
            if stem.len() >= 2 {
                let base_opt = Self::lookup_direct(stem, lex)
                    .or_else(|| Self::lookup_direct(&format!("{stem}e"), lex))
                    .or_else(|| {
                        Self::undouble_consonant(stem)
                            .and_then(|s| Self::lookup_direct(s, lex))
                    });
                if let Some(base) = base_opt {
                    return Some(Self::append_ing(&base, british));
                }
            }
        }
        if let Some(stem) = lower.strip_suffix("ly") {
            if stem.len() >= 2 {
                if let Some(base) = Self::lookup_direct(stem, lex) {
                    return Some(format!("{base}li"));
                }
            }
        }

        None
    }

    fn undouble_consonant(stem: &str) -> Option<&str> {
        let bytes = stem.as_bytes();
        if bytes.len() >= 3 && bytes[bytes.len() - 1] == bytes[bytes.len() - 2] {
            std::str::from_utf8(&bytes[..bytes.len() - 1]).ok()
        } else {
            None
        }
    }

    fn append_sibilant(base: &str) -> String {
        match base.chars().last() {
            Some('s' | 'z' | 'ʃ' | 'ʒ' | 'ʧ' | 'ʤ') => format!("{base}ɪz"),
            Some('p' | 't' | 'k' | 'f' | 'θ') => format!("{base}s"),
            _ => format!("{base}z"),
        }
    }

    fn append_ed(base: &str) -> String {
        match base.chars().last() {
            Some('t' | 'd') => format!("{base}ɪd"),
            Some('p' | 'k' | 'f' | 'θ' | 's' | 'ʃ' | 'ʧ') => format!("{base}t"),
            _ => format!("{base}d"),
        }
    }

    fn append_ing(base: &str, _british: bool) -> String {
        format!("{base}ɪŋ")
    }

    /// Rule-based English Letter-to-Sound fallback using Misaki IPA tokens for unseen words.
    fn fallback_lts(word: &str, british: bool) -> String {
        let lower: Vec<char> = word.to_ascii_lowercase().chars().collect();
        let mut ps = String::from("ˈ");
        let mut i = 0;
        let len = lower.len();

        let rest_slice = |idx: usize| -> String { lower[idx..].iter().collect() };

        while i < len {
            let rem = rest_slice(i);
            if rem.starts_with("tion") {
                ps.push_str("ʃən");
                i += 4;
                continue;
            }
            if rem.starts_with("sion") {
                ps.push_str("ʒən");
                i += 4;
                continue;
            }
            if rem.starts_with("igh") {
                ps.push('I');
                i += 3;
                continue;
            }
            if rem.starts_with("ous") {
                ps.push_str("əs");
                i += 3;
                continue;
            }
            if rem.starts_with("ing") && i + 3 == len {
                ps.push_str("ɪŋ");
                i += 3;
                continue;
            }

            if i + 1 < len {
                let d: String = lower[i..i + 2].iter().collect();
                let mapped = match d.as_str() {
                    "ch" | "tc" => Some("ʧ"),
                    "sh" => Some("ʃ"),
                    "th" => Some("θ"),
                    "ph" => Some("f"),
                    "wh" => Some("w"),
                    "ng" => Some("ŋ"),
                    "qu" => Some("kw"),
                    "ck" => Some("k"),
                    "ee" | "ea" => Some("i"),
                    "oo" => Some("u"),
                    "ai" | "ay" => Some("A"),
                    "oa" | "ow" => Some(if british { "Q" } else { "O" }),
                    "ou" => Some("W"),
                    "oi" | "oy" => Some("Y"),
                    "au" | "aw" => Some("ɔ"),
                    "er" | "ir" | "ur" => Some(if british { "ɜː" } else { "ɜɹ" }),
                    "ar" => Some(if british { "ɑː" } else { "ɑɹ" }),
                    "or" => Some(if british { "ɔː" } else { "ɔɹ" }),
                    _ => None,
                };
                if let Some(m) = mapped {
                    ps.push_str(m);
                    i += 2;
                    continue;
                }
            }

            let c = lower[i];
            // Silent trailing 'e' on multi-letter words
            if c == 'e' && i == len - 1 && len > 2 {
                i += 1;
                continue;
            }

            let next_c = lower.get(i + 1).copied();
            let s = match c {
                'a' => "æ",
                'b' => "b",
                'c' => {
                    if matches!(next_c, Some('e' | 'i' | 'y')) {
                        "s"
                    } else {
                        "k"
                    }
                }
                'd' => "d",
                'e' => "ɛ",
                'f' => "f",
                'g' => {
                    if matches!(next_c, Some('e' | 'i' | 'y')) {
                        "ʤ"
                    } else {
                        "ɡ"
                    }
                }
                'h' => "h",
                'i' => "ɪ",
                'j' => "ʤ",
                'k' => "k",
                'l' => "l",
                'm' => "m",
                'n' => "n",
                'o' => "ɑ",
                'p' => "p",
                'q' => "k",
                'r' => "ɹ",
                's' => "s",
                't' => "t",
                'u' => "ʌ",
                'v' => "v",
                'w' => "w",
                'x' => "ks",
                'y' => if i == 0 { "j" } else { "i" },
                'z' => "z",
                _ => "",
            };
            ps.push_str(s);
            i += 1;
        }
        ps
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loads_embedded_lexicons_and_tokenizes() {
        let g2p = MisakiG2p::load_embedded().expect("MisakiG2p should load cleanly");
        assert!(g2p.us_lexicon.len() > 150_000);
        assert!(g2p.gb_lexicon.len() > 150_000);

        let chunks = g2p.text_to_token_chunks("Hello from SpeakThat in pure Rust! It runs offline at 100% speed.", true);
        assert!(!chunks.is_empty());
        for c in &chunks {
            assert_eq!(c[0], 0);
            assert_eq!(*c.last().unwrap(), 0);
            assert!(c.len() <= 512);
        }
    }

    #[test]
    fn suffix_stemming_and_oov_work() {
        let g2p = MisakiG2p::load_embedded().unwrap();
        let ps = g2p.phonemize_sentence("running apples walked xyzzyx", false);
        assert!(!ps.is_empty());
        assert!(ps.contains("ɪŋ"));
    }
}
