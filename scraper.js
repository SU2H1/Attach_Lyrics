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

    async scrapeGenius(title, artist) {
        const page = await this.browser.newPage();
        try {
            const cleanArtist = this.cleanText(artist).replace(/\s+/g, '-');
            const cleanTitle = this.cleanText(title).replace(/\s+/g, '-');
            const url = `https://genius.com/${cleanArtist}-${cleanTitle}-lyrics`;
            
            await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
            
            // Wait for lyrics container
            await page.waitForSelector('[data-lyrics-container="true"]', { timeout: 5000 });
            
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
            
            return lyrics;
        } catch (error) {
            console.log(`Genius scraping failed: ${error.message}`);
            return null;
        } finally {
            await page.close();
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
            
            return lyrics;
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
            
            return lyrics;
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
        const lyrics = await scraper.scrapeLyrics(title, artist);
        res.json({ lyrics: lyrics || null });
    } catch (error) {
        res.status(500).json({ error: error.message });
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