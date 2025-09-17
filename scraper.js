const puppeteer = require('puppeteer');
const express = require('express');
const cors = require('cors');

class LyricsScraper {
    constructor() {
        this.browser = null;
    }

    async init() {
        this.browser = await puppeteer.launch({
            headless: 'new',
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
    }

    async close() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    cleanText(text) {
        return text
            .replace(/\([^)]*\)/g, '')
            .replace(/\[[^\]]*\]/g, '')
            .replace(/feat\.|ft\.|featuring/gi, '')
            .replace(/[^\w\s-]/g, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    cleanLyrics(lyrics) {
        if (!lyrics) return lyrics;

        let cleaned = lyrics;

        // Remove common unwanted patterns
        const unwantedPatterns = [
            // Contributors and translation info
            /\d+\s*Contributors?/gi,
            /Translations?\w*/gi,
            /\d+\s*Embed/gi,

            // Song title repetition at start (e.g., "Love in My Pocket Lyrics")
            /^.*?Lyrics\s*/i,

            // Language indicators
            /Español|Français|Deutsch|Italiano|Português|العربية|中文|日本語|한국어|Русский/gi,

            // Website metadata
            /genius\.com|azlyrics\.com|lyrics\.com/gi,
            /\bgenius\b|\bazlyrics\b/gi,

            // Copyright and legal text
            /©.*?\d{4}/g,
            /All rights reserved/gi,
            /Powered by.*$/gmi,

            // Social media and sharing
            /Share on Facebook|Tweet|Share|Like|Follow/gi,
            /www\.|http[s]?:\/\//gi,

            // Advertisement text
            /Advertisement/gi,
            /Sponsored/gi,

            // Navigation elements
            /Home|About|Contact|Privacy|Terms/gi,

            // Common metadata patterns
            /Album:|Artist:|Released:/gi,
            /\bfrom the album\b/gi,

            // Multiple spaces, tabs, newlines
            /\s{3,}/g,
            /\t+/g,
            /\n{3,}/g
        ];

        // Apply all patterns
        unwantedPatterns.forEach(pattern => {
            cleaned = cleaned.replace(pattern, ' ');
        });

        // Clean up structure
        cleaned = cleaned
            .split('\n')
            .map(line => line.trim())
            .filter(line => {
                // Remove lines that are likely metadata
                if (line.length === 0) return false;
                if (line.match(/^\d+$/)) return false; // Just numbers
                if (line.match(/^[^\w]*$/)) return false; // Just punctuation
                if (line.length < 3 && !line.match(/^[A-Za-z]+$/)) return false; // Very short non-word lines
                return true;
            })
            .join('\n')
            .replace(/\n{2,}/g, '\n\n') // Max 2 consecutive newlines
            .trim();

        return cleaned;
    }

    async scrapeGenius(title, artist) {
        let page = null;
        try {
            page = await this.browser.newPage();
            await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

            const cleanArtist = this.cleanText(artist).replace(/\s+/g, '-');
            const cleanTitle = this.cleanText(title).replace(/\s+/g, '-');
            const url = `https://genius.com/${cleanArtist}-${cleanTitle}-lyrics`;

            await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });

            // Wait for lyrics container
            await page.waitForSelector('[data-lyrics-container="true"]', { timeout: 8000 });

            const lyrics = await page.evaluate(() => {
                const containers = document.querySelectorAll('[data-lyrics-container="true"]');
                let text = '';
                containers.forEach(container => {
                    // Replace br tags with newlines
                    container.innerHTML = container.innerHTML.replace(/<br>/g, '\n');
                    text += container.innerText + '\n';
                });
                return text.trim();
            });

            return this.cleanLyrics(lyrics);
        } catch (error) {
            console.log(`Genius scraping failed: ${error.message}`);
            return null;
        } finally {
            if (page) {
                try {
                    await page.close();
                } catch (e) {
                    console.log('Error closing page:', e.message);
                }
            }
        }
    }

    async scrapeAZLyrics(title, artist) {
        const page = await this.browser.newPage();
        try {
            const cleanArtist = artist.toLowerCase().replace(/[^a-z0-9]/g, '');
            const cleanTitle = title.toLowerCase().replace(/[^a-z0-9]/g, '');
            const url = `https://www.azlyrics.com/lyrics/${cleanArtist}/${cleanTitle}.html`;
            
            await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
            
            // AZLyrics stores lyrics in a div without class or id, after a specific comment
            const lyrics = await page.evaluate(() => {
                const comment = Array.from(document.childNodes)
                    .find(node => node.nodeType === 8 && node.textContent.includes('Usage of azlyrics'));

                if (comment) {
                    let nextElement = comment.nextSibling;
                    while (nextElement && nextElement.nodeType !== 1) {
                        nextElement = nextElement.nextSibling;
                    }
                    if (nextElement && nextElement.tagName === 'DIV') {
                        return nextElement.innerText.trim();
                    }
                }

                // Fallback method
                const divs = document.querySelectorAll('div');
                for (let div of divs) {
                    if (!div.className && !div.id && div.innerText.length > 200) {
                        return div.innerText.trim();
                    }
                }
                return null;
            });

            return lyrics ? this.cleanLyrics(lyrics) : null;
        } catch (error) {
            console.log(`AZLyrics scraping failed: ${error.message}`);
            return null;
        } finally {
            await page.close();
        }
    }

    async scrapeGoogle(title, artist) {
        const page = await this.browser.newPage();
        try {
            const query = encodeURIComponent(`${artist} ${title} lyrics`);
            const url = `https://www.google.com/search?q=${query}`;
            
            await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
            
            // Google often shows lyrics directly in search results
            const lyrics = await page.evaluate(() => {
                // Try to find lyrics in knowledge panel
                const lyricsDiv = document.querySelector('[data-lyricid]');
                if (lyricsDiv) {
                    return lyricsDiv.innerText.trim();
                }

                // Try alternative selector
                const altDiv = document.querySelector('.PZPZlf');
                if (altDiv) {
                    return altDiv.innerText.trim();
                }

                return null;
            });

            return lyrics ? this.cleanLyrics(lyrics) : null;
        } catch (error) {
            console.log(`Google scraping failed: ${error.message}`);
            return null;
        } finally {
            await page.close();
        }
    }

    async scrapeLyrics(title, artist) {
        console.log(`Searching for: ${artist} - ${title}`);
        
        // Try different sources
        const sources = [
            { name: 'Genius', method: this.scrapeGenius.bind(this) },
            { name: 'AZLyrics', method: this.scrapeAZLyrics.bind(this) },
            { name: 'Google', method: this.scrapeGoogle.bind(this) }
        ];
        
        for (const source of sources) {
            console.log(`Trying ${source.name}...`);
            const lyrics = await source.method(title, artist);
            if (lyrics && lyrics.length > 100) {
                console.log(`Found lyrics from ${source.name}`);
                return lyrics;
            }
        }
        
        return null;
    }
}

// Express server for communication with Python GUI
const app = express();
app.use(cors());
app.use(express.json());

let scraper = null;

app.post('/init', async (req, res) => {
    try {
        if (!scraper) {
            scraper = new LyricsScraper();
            await scraper.init();
        }
        res.json({ status: 'initialized' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/scrape', async (req, res) => {
    try {
        const { title, artist } = req.body;
        if (!scraper) {
            scraper = new LyricsScraper();
            await scraper.init();
        }

        // Check if browser is still alive
        if (!scraper.browser || !scraper.browser.isConnected()) {
            console.log('Browser disconnected, reinitializing...');
            await scraper.close();
            scraper = new LyricsScraper();
            await scraper.init();
        }

        const lyrics = await scraper.scrapeLyrics(title, artist);
        res.json({ lyrics: lyrics || null });
    } catch (error) {
        console.log('Scraping error:', error.message);

        // If browser crashed, try to reinitialize
        if (error.message.includes('Target closed') || error.message.includes('Connection closed')) {
            try {
                console.log('Browser crashed, reinitializing...');
                await scraper.close();
                scraper = new LyricsScraper();
                await scraper.init();
                res.json({ lyrics: null, error: 'Browser restarted, try again' });
            } catch (reinitError) {
                res.status(500).json({ error: 'Browser restart failed: ' + reinitError.message });
            }
        } else {
            res.status(500).json({ error: error.message });
        }
    }
});

app.post('/close', async (req, res) => {
    try {
        if (scraper) {
            await scraper.close();
            scraper = null;
        }
        res.json({ status: 'closed' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Puppeteer scraper server running on http://localhost:${PORT}`);
});

// Cleanup on exit
process.on('SIGINT', async () => {
    if (scraper) {
        await scraper.close();
    }
    process.exit();
});