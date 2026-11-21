/// Native Bionic Reading Engine for Windows
/// Supports:
/// - Parsing text into structured bionic tokens (for native GUI renderers)
/// - Converting text to Mathematical Bold Unicode glyphs for universal in-place injection across any app
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BionicWord {
    pub bold: String,
    pub rest: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BionicToken {
    Word(BionicWord),
    NonWord(String),
}

pub struct BionicEngine {
    pub fixation_ratio: f32,
}

impl Default for BionicEngine {
    fn default() -> Self {
        Self {
            fixation_ratio: 0.4,
        }
    }
}

impl BionicEngine {
    pub fn new(fixation_ratio: f32) -> Self {
        Self {
            fixation_ratio: fixation_ratio.clamp(0.1, 0.9),
        }
    }

    /// Calculate the number of characters to bold at the start of a word
    pub fn get_bold_length(len: usize, ratio: f32) -> usize {
        if len <= 1 {
            1
        } else if len <= 3 {
            len.min((len as f32 * ratio).ceil() as usize).max(1)
        } else if len == 4 {
            3.min((len as f32 * ratio).ceil() as usize).max(1)
        } else {
            (len - 1).min((len as f32 * ratio).ceil() as usize).max(1)
        }
    }

    /// Map standard Latin letters and digits to Mathematical Bold Sans-Serif Unicode glyphs
    pub fn to_bold_char(c: char) -> char {
        match c {
            'A'..='Z' => {
                let offset = (c as u32) - ('A' as u32);
                char::from_u32(0x1D5D4 + offset).unwrap_or(c)
            }
            'a'..='z' => {
                let offset = (c as u32) - ('a' as u32);
                char::from_u32(0x1D5EE + offset).unwrap_or(c)
            }
            '0'..='9' => {
                let offset = (c as u32) - ('0' as u32);
                char::from_u32(0x1D7EC + offset).unwrap_or(c)
            }
            _ => c,
        }
    }

    /// Parse a single word into bold and rest parts
    pub fn process_word(&self, word: &str) -> BionicWord {
        let chars: Vec<char> = word.chars().collect();
        let bold_len = Self::get_bold_length(chars.len(), self.fixation_ratio);

        let bold: String = chars[..bold_len].iter().collect();
        let rest: String = chars[bold_len..].iter().collect();

        BionicWord { bold, rest }
    }

    /// Tokenize arbitrary text into words and delimiters
    pub fn tokenize(&self, text: &str) -> Vec<BionicToken> {
        let mut tokens = Vec::new();
        let mut current_word = String::new();
        let mut current_non_word = String::new();

        for c in text.chars() {
            if c.is_alphanumeric() {
                if !current_non_word.is_empty() {
                    tokens.push(BionicToken::NonWord(std::mem::take(&mut current_non_word)));
                }
                current_word.push(c);
            } else {
                if !current_word.is_empty() {
                    let word = std::mem::take(&mut current_word);
                    tokens.push(BionicToken::Word(self.process_word(&word)));
                }
                current_non_word.push(c);
            }
        }

        if !current_word.is_empty() {
            tokens.push(BionicToken::Word(self.process_word(&current_word)));
        }
        if !current_non_word.is_empty() {
            tokens.push(BionicToken::NonWord(current_non_word));
        }

        tokens
    }

    /// Convert text into Mathematical Bold Sans-Serif Unicode format
    /// E.g. "Reading is" -> "𝗥𝗲𝗮ding 𝗶s"
    /// Can be pasted into any Windows input field directly
    pub fn to_unicode_bionic(&self, text: &str) -> String {
        let tokens = self.tokenize(text);
        let mut result = String::with_capacity(text.len() * 2);

        for token in tokens {
            match token {
                BionicToken::Word(w) => {
                    for c in w.bold.chars() {
                        result.push(Self::to_bold_char(c));
                    }
                    result.push_str(&w.rest);
                }
                BionicToken::NonWord(nw) => {
                    result.push_str(&nw);
                }
            }
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bold_lengths() {
        assert_eq!(BionicEngine::get_bold_length(1, 0.4), 1);
        assert_eq!(BionicEngine::get_bold_length(3, 0.4), 2);
        assert_eq!(BionicEngine::get_bold_length(4, 0.4), 2);
        assert_eq!(BionicEngine::get_bold_length(7, 0.4), 3);
    }

    #[test]
    fn test_unicode_bionic() {
        let engine = BionicEngine::default();
        let out = engine.to_unicode_bionic("Reading is reading");
        assert!(out.contains("ding"));
        assert!(out.contains("is"));
    }
}
