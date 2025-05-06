const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const https = require('https');

class EventCrawler {
    constructor(options = {}) {
        this.baseUrl = 'https://bazaardb.gg';
        this.outputDir = options.outputDir || 'dev/html/events';
        this.iconsDir = path.join(process.cwd(), 'icons');
        this.browser = null;
        this.page = null;
        this.events = [];
        this.version = "1.0.0";
        this.dataSchema = {
            version: this.version,
            lastUpdate: new Date().toISOString(),
            events: []
        };
        
        // 确保输出目录存在
        this.ensureDirectories();
    }

    ensureDirectories() {
        const dirs = [this.outputDir, this.iconsDir];
        for (const dir of dirs) {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
                console.log(`创建目录: ${dir}`);
            }
        }
    }

    async downloadImage(url, filename) {
        if (!url) return null;
        
        try {
            // 处理SVG格式的图片
            if (url.startsWith('data:image/svg+xml')) {
                const svgContent = decodeURIComponent(url.split(',')[1]);
                const safeFilename = filename.replace(/[^a-zA-Z0-9]/g, '_') + '.svg';
                const filePath = path.join(this.iconsDir, safeFilename);
                
                if (fs.existsSync(filePath)) {
                    console.log(`SVG图标已存在: ${safeFilename}`);
                    return filePath;
                }
                
                fs.writeFileSync(filePath, svgContent);
                console.log(`已保存SVG图标: ${safeFilename}`);
                return filePath;
            }
            
            // 处理普通图片URL
            const cleanUrl = decodeURIComponent(url.split('?')[0]);
            const ext = path.extname(cleanUrl) || '.png';
            const safeFilename = filename.replace(/[^a-zA-Z0-9]/g, '_') + ext;
            const filePath = path.join(this.iconsDir, safeFilename);
            
            if (fs.existsSync(filePath)) {
                console.log(`图标已存在: ${safeFilename}`);
                return filePath;
            }

            console.log(`下载图标: ${cleanUrl}`);
            return new Promise((resolve, reject) => {
                https.get(cleanUrl, (response) => {
                    if (response.statusCode !== 200) {
                        console.log(`下载图标失败: ${response.statusCode}`);
                        resolve(null);
                        return;
                    }

                    const fileStream = fs.createWriteStream(filePath);
                    response.pipe(fileStream);
                    fileStream.on('finish', () => {
                        fileStream.close();
                        console.log(`图标已保存: ${safeFilename}`);
                        resolve(filePath);
                    });
                }).on('error', (err) => {
                    console.log(`下载图标失败: ${err.message}`);
                    resolve(null);
                });
            });
        } catch (error) {
            console.log(`处理图标URL时出错: ${error.message}`);
            return null;
        }
    }

    async retry(fn, retries = 3, delay = 5000) {
        for (let i = 0; i < retries; i++) {
            try {
                return await fn();
            } catch (error) {
                if (i === retries - 1) throw error;
                console.log(`尝试失败，${delay/1000}秒后重试...错误: ${error.message}`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    async init() {
        console.log('初始化爬虫...');
        this.browser = await puppeteer.launch({
            headless: false,
            defaultViewport: null,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080'],
            ignoreHTTPSErrors: true
        });
        this.page = await this.browser.newPage();
        
        // 设置更长的超时时间
        this.page.setDefaultTimeout(120000);
        this.page.setDefaultNavigationTimeout(120000);
        
        // 设置视窗大小
        await this.page.setViewport({
            width: 1920,
            height: 1080
        });

        // 监听console事件
        this.page.on('console', msg => console.log('浏览器控制台:', msg.text()));
        
        // 监听错误事件
        this.page.on('error', err => console.error('页面错误:', err));
        this.page.on('pageerror', err => console.error('页面JS错误:', err));
    }

    async fetchEventList() {
        console.log('开始获取事件列表...');
        const listFile = path.join(this.outputDir, 'events.json');
        
        if (fs.existsSync(listFile)) {
            console.log('从events.json读取事件列表...');
            this.events = JSON.parse(fs.readFileSync(listFile, 'utf8'));
            console.log(`读取到 ${this.events.length} 个事件`);
            
            // 输出前5个事件的信息用于验证
            this.events.slice(0, 5).forEach((event, index) => {
                console.log(`${index + 1}. ${event.name}: ${event.url}`);
            });
            return;
        }

        const eventsUrl = `${this.baseUrl}/search?c=events`;
        console.log(`正在访问事件列表页面: ${eventsUrl}`);
        
        try {
            await this.retry(async () => {
                const response = await this.page.goto(eventsUrl, {
                    waitUntil: ['networkidle0', 'domcontentloaded'],
                    timeout: 120000
                });
                
                if (!response || !response.ok()) {
                    throw new Error(`页面加载失败: ${response ? response.status() : 'No response'}`);
                }
            });
            
            console.log('页面加载成功，等待渲染...');
            await new Promise(resolve => setTimeout(resolve, 5000));

            // 自动滚动到底部，确保所有事件都加载出来
            await this.page.evaluate(async () => {
                let lastHeight = 0;
                let reachedEnd = false;
                while (!reachedEnd) {
                    window.scrollBy(0, 1000);
                    await new Promise(resolve => setTimeout(resolve, 500));
                    let newHeight = document.body.scrollHeight;
                    if (newHeight === lastHeight) {
                        reachedEnd = true;
                    }
                    lastHeight = newHeight;
                }
            });

            // 获取所有事件链接和图标
            console.log('正在获取事件基本信息...');
            this.events = await this.page.evaluate(() => {
                const cards = Array.from(document.querySelectorAll('a[href*="/card/"]'));
                return cards.map(card => {
                    const nameEl = card.querySelector('h3');
                    const name = nameEl ? nameEl.textContent.trim() : '';
                    const href = card.getAttribute('href');
                    const link = href.startsWith('http') ? href : 'https://bazaardb.gg' + href;
                    
                    // 获取图标URL
                    const imgEl = card.querySelector('img');
                    const iconUrl = imgEl ? imgEl.src : '';
                    
                    return { name, url: link, iconUrl };
                }).filter(event => event.name && event.url);
            });

            console.log(`找到 ${this.events.length} 个事件`);
            
            // 保存事件信息
            fs.writeFileSync(listFile, JSON.stringify(this.events, null, 2));
            console.log('已保存所有事件基本信息到 events.json');
            
        } catch (error) {
            console.error('获取事件列表失败:', error);
            throw error;
        }
    }

    async fetchEventDetails(event, index, total) {
        const fileName = `event_detail_${index + 1}_${event.name.replace(/[^a-zA-Z0-9]/g, '_')}.html`;
        const filePath = path.join(this.outputDir, fileName);
        
        if (fs.existsSync(filePath)) {
            console.log(`\n[${index + 1}/${total}] ${event.name} 的详细信息已存在，跳过`);
            return;
        }
        
        console.log(`\n[${index + 1}/${total}] 正在处理 ${event.name}`);
        console.log(`正在访问详情页面: ${event.url}`);
        
        try {
            await this.retry(async () => {
                const response = await this.page.goto(event.url, {
                    waitUntil: ['networkidle0', 'domcontentloaded'],
                    timeout: 120000
                });
                
                if (!response || !response.ok()) {
                    throw new Error(`页面加载失败: ${response ? response.status() : 'No response'}`);
                }
            });
            
            console.log('等待页面渲染...');
            await new Promise(resolve => setTimeout(resolve, 5000));
            
            // 获取事件选项信息
            const eventData = await this.page.evaluate(() => {
                const options = Array.from(document.querySelectorAll('[alt]')).map(img => ({
                    text: img.alt,
                    imageUrl: img.src
                })).filter(opt => opt.text && opt.imageUrl);
                
                return {
                    options,
                    html: document.documentElement.outerHTML
                };
            });
            
            // 保存选项图片
            if (eventData.options && eventData.options.length > 0) {
                console.log(`找到 ${eventData.options.length} 个选项`);
                for (const option of eventData.options) {
                    // 用 text + imageUrl 的主要部分做唯一文件名
                    const urlPart = option.imageUrl.split('/').pop().split('@')[0].replace(/[^a-zA-Z0-9]/g, '_');
                    const optionFileName = `${event.name}_option_${option.text.replace(/[^a-zA-Z0-9]/g, '_')}_${urlPart}`;
                    option.imagePath = await this.downloadImage(option.imageUrl, optionFileName);
                }
            }
            
            // 保存页面HTML
            fs.writeFileSync(filePath, eventData.html);
            console.log(`已保存到文件: ${fileName}`);
            
        } catch (error) {
            console.error(`获取 ${event.name} 的详细信息时出错:`, error);
        }
    }

    validateEventData(event) {
        const requiredFields = ['name', 'url'];
        const missingFields = requiredFields.filter(field => !event[field]);
        if (missingFields.length > 0) {
            console.log(`事件数据缺少必要字段: ${missingFields.join(', ')}`);
            return false;
        }
        return true;
    }

    async checkDataIntegrity() {
        console.log('开始检查数据完整性...');
        const listFile = path.join(this.outputDir, 'events.json');
        
        if (!fs.existsSync(listFile)) {
            console.log('未找到events.json文件，需要重新抓取数据');
            return false;
        }

        const events = JSON.parse(fs.readFileSync(listFile, 'utf8'));
        console.log(`数据库中有 ${events.length} 个事件`);

        // 检查每个事件的数据完整性
        let missingData = 0;
        let missingIcons = 0;
        let missingDetails = 0;

        for (const event of events) {
            // 检查基本信息
            if (!this.validateEventData(event)) {
                missingData++;
            }

            // 检查图标文件
            const iconPath = path.join(this.iconsDir, `${event.name.replace(/[^a-zA-Z0-9]/g, '_')}.png`);
            if (!fs.existsSync(iconPath)) {
                missingIcons++;
            }

            // 检查详细信息
            const detailPath = path.join(this.outputDir, `event_detail_${event.name.replace(/[^a-zA-Z0-9]/g, '_')}.html`);
            if (!fs.existsSync(detailPath)) {
                missingDetails++;
            }
        }

        console.log('数据完整性检查结果:');
        console.log(`- 缺少基本数据的事件: ${missingData}`);
        console.log(`- 缺少图标的事件: ${missingIcons}`);
        console.log(`- 缺少详细信息的事件: ${missingDetails}`);

        return missingData === 0 && missingIcons === 0 && missingDetails === 0;
    }

    async crawl() {
        try {
            await this.init();
            
            // 检查数据完整性
            const isComplete = await this.checkDataIntegrity();
            if (!isComplete) {
                console.log('数据不完整，开始重新抓取...');
                await this.fetchEventList();
                
                // 获取所有事件的详细信息
                console.log(`\n准备获取 ${this.events.length} 个事件的详细信息`);
                for (let i = 0; i < this.events.length; i++) {
                    await this.fetchEventDetails(this.events[i], i, this.events.length);
                    
                    // 在请求之间添加随机延迟(3-7秒)
                    if (i < this.events.length - 1) {
                        const delay = 3000 + Math.random() * 4000;
                        console.log(`等待 ${Math.round(delay/1000)} 秒后继续下一个事件...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }
                }
            } else {
                console.log('数据完整，无需重新抓取');
            }
            
            console.log('\n全部完成!');
        } catch (error) {
            console.error('发生错误:', error);
        } finally {
            if (this.browser) {
                await this.browser.close();
            }
        }
    }
}

// 使用示例
const crawler = new EventCrawler({
    outputDir: 'dev/html/events'
});
crawler.crawl(); 