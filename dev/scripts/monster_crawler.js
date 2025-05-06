const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const https = require('https');

class MonsterCrawler {
    constructor(options = {}) {
        this.baseUrl = 'https://bazaardb.gg';
        this.outputDir = options.outputDir || 'dev/html/monsters';
        this.iconsDir = path.join(process.cwd(), 'icons');
        this.browser = null;
        this.page = null;
        this.monsters = [];
        this.processedCount = 0;
        this.totalCount = 0;
        this.maxConcurrent = options.maxConcurrent || 3;
        this.activeTasks = 0;
        
        this.ensureDirectories();
        this.logFile = path.join(this.outputDir, 'crawler.log');
        this.logStream = fs.createWriteStream(this.logFile, { flags: 'a' });
    }

    ensureDirectories() {
        const dirs = [this.outputDir, this.iconsDir];
        for (const dir of dirs) {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
                this.log(`创建目录: ${dir}`);
            }
        }
    }

    log(message) {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] ${message}\n`;
        console.log(message);
        this.logStream.write(logMessage);
    }

    async retry(fn, retries = 3, delay = 5000) {
        for (let i = 0; i < retries; i++) {
            try {
                return await fn();
            } catch (error) {
                if (i === retries - 1) throw error;
                this.log(`尝试失败，${delay/1000}秒后重试...错误: ${error.message}`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    fileExists(filePath) {
        try {
            fs.accessSync(filePath, fs.constants.F_OK);
            return true;
        } catch (err) {
            return false;
        }
    }

    async init() {
        this.log('初始化爬虫...');
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

    async fetchMonsterList() {
        this.log('开始获取怪物列表...');
        const listFile = path.join(this.outputDir, 'monsters.json');
        
        if (this.fileExists(listFile)) {
            this.log('从monsters.json读取怪物列表...');
            this.monsters = JSON.parse(fs.readFileSync(listFile, 'utf8'));
            this.log(`读取到 ${this.monsters.length} 个怪物信息`);
        } else {
            const monstersUrl = `${this.baseUrl}/search?c=monsters`;
            this.log(`正在访问怪物列表页面: ${monstersUrl}`);
            
            try {
                await this.retry(async () => {
                    const response = await this.page.goto(monstersUrl, {
                        waitUntil: ['networkidle0', 'domcontentloaded'],
                        timeout: 120000
                    });
                    
                    if (!response || !response.ok()) {
                        throw new Error(`页面加载失败: ${response ? response.status() : 'No response'}`);
                    }
                });
                
                this.log('页面加载成功，等待渲染...');
                await new Promise(resolve => setTimeout(resolve, 5000));
                
                // 调试：保存页面内容
                const pageContent = await this.page.content();
                const debugFile = path.join(this.outputDir, 'debug.html');
                fs.writeFileSync(debugFile, pageContent);
                this.log(`已保存页面内容到 ${debugFile}`);
                
                // 获取所有怪物链接
                this.log('正在获取怪物基本信息...');
                this.monsters = await this.page.evaluate(() => {
                    const cards = Array.from(document.querySelectorAll('a[href*="/card/"]'));
                    return cards.map(card => {
                        const nameEl = card.querySelector('h3');
                        const name = nameEl ? nameEl.textContent.trim() : '';
                        const href = card.getAttribute('href');
                        const link = href.startsWith('http') ? href : 'https://bazaardb.gg' + href;
                        return { name, link };
                    }).filter(monster => monster.name && monster.link);
                });

                this.totalCount = this.monsters.length;
                this.log(`找到 ${this.totalCount} 个怪物`);
                
                // 输出找到的怪物信息
                this.monsters.forEach((monster, index) => {
                    this.log(`${index + 1}. ${monster.name}: ${monster.link}`);
                });
                
                fs.writeFileSync(listFile, JSON.stringify(this.monsters, null, 2));
                this.log('已保存所有怪物基本信息到 monsters.json');
            } catch (error) {
                this.log('获取怪物列表失败:', error);
                throw error;
            }
        }
    }

    async downloadImage(url, filename) {
        if (!url) return null;
        
        // 移除URL中的查询参数
        const cleanUrl = url.split('?')[0];
        const ext = path.extname(cleanUrl) || '.png';
        const safeFilename = filename.replace(/[^a-zA-Z0-9]/g, '_') + ext;
        const filePath = path.join(this.iconsDir, safeFilename);
        
        if (fs.existsSync(filePath)) {
            return filePath;
        }

        return new Promise((resolve, reject) => {
            const req = https.get(cleanUrl, (response) => {
                if (response.statusCode !== 200) {
                    reject(new Error(`下载图片失败: ${response.statusCode}`));
                    return;
                }

                const fileStream = fs.createWriteStream(filePath);
                response.pipe(fileStream);
                fileStream.on('finish', () => {
                    fileStream.close();
                    resolve(filePath);
                });
            });

            req.setTimeout(15000, () => { // 15秒超时
                req.abort();
                console.log(`下载图标超时: ${cleanUrl}`);
                resolve(null);
            });
            req.on('error', (err) => {
                this.log(`下载图片失败: ${err.message}`);
                resolve(null); // 返回null而不是reject，让程序继续执行
            });
        });
    }

    async fetchCardDescription(cardUrl) {
        try {
            await this.retry(async () => {
                await this.page.goto(cardUrl, {
                    waitUntil: 'networkidle0'
                });
            });

            await new Promise(resolve => setTimeout(resolve, 2000));

            return await this.page.evaluate(() => {
                const description = document.querySelector('div[style*="color:rgb(181, 169, 156)"]');
                return description ? description.textContent.trim() : '';
            });
        } catch (error) {
            this.log(`获取卡牌描述失败: ${error.message}`);
            return '';
        }
    }

    async processCard(card) {
        if (!card.name || !card.icon) return card;

        try {
            // 下载图标
            const iconExt = path.extname(card.icon) || '.png';
            const iconFilename = `${card.name.replace(/[^a-zA-Z0-9]/g, '_')}${iconExt}`;
            const iconPath = await this.downloadImage(card.icon, iconFilename);
            
            // 获取描述
            const description = await this.fetchCardDescription(card.url);
            
            return {
                ...card,
                iconPath,
                description
            };
        } catch (error) {
            this.log(`处理卡牌 ${card.name} 失败: ${error.message}`);
            return card;
        }
    }

    async fetchMonsterDetails(monster, index, total) {
        const fileName = `monster_detail_${index + 1}_${monster.name.replace(/[^a-zA-Z0-9]/g, '_')}.html`;
        const filePath = path.join(this.outputDir, fileName);
        
        if (this.fileExists(filePath)) {
            this.log(`\n[${index + 1}/${total}] ${monster.name} 的详细信息已存在，跳过`);
            return;
        }
        
        this.log(`\n[${index + 1}/${total}] 正在处理 ${monster.name}`);
        this.log(`正在访问详情页面: ${monster.link}`);
        
        try {
            await this.retry(async () => {
                const response = await this.page.goto(monster.link, {
                    waitUntil: ['networkidle0', 'domcontentloaded'],
                    timeout: 120000
                });
                
                if (!response || !response.ok()) {
                    throw new Error(`页面加载失败: ${response ? response.status() : 'No response'}`);
                }
            });
            
            this.log('等待页面渲染...');
            await new Promise(resolve => setTimeout(resolve, 5000));
            
            // 获取怪物图片信息
            const monsterData = await this.page.evaluate(() => {
                // 获取主背景图
                let bgUrl = '';
                const bgDiv = document.querySelector('div._at');
                if (bgDiv && bgDiv.style.backgroundImage) {
                    const match = bgDiv.style.backgroundImage.match(/url\(["']?(.*?)["']?\)/);
                    if (match) {
                        bgUrl = match[1];
                    }
                }
                // 获取角色形象图
                let charUrl = '';
                const charImg = document.querySelector('img._au');
                if (charImg && charImg.src) {
                    charUrl = charImg.src;
                }
                return {
                    bgUrl,
                    charUrl,
                    html: document.documentElement.outerHTML
                };
            });
            
            // 下载主背景图
            if (monsterData.bgUrl) {
                this.log(`找到怪物主背景图URL: ${monsterData.bgUrl}`);
                const safeName = monster.name.replace(/[^a-zA-Z0-9]/g, '_');
                const imagePath = await this.downloadImage(monsterData.bgUrl, `monster_bg_${safeName}`);
                this.log(`已下载怪物主背景图: ${imagePath}`);
            } else {
                this.log(`警告: 未找到怪物 ${monster.name} 的主背景图`);
            }
            // 下载角色形象图
            if (monsterData.charUrl) {
                this.log(`找到怪物角色图URL: ${monsterData.charUrl}`);
                const safeName = monster.name.replace(/[^a-zA-Z0-9]/g, '_');
                const imagePath = await this.downloadImage(monsterData.charUrl, `monster_char_${safeName}`);
                this.log(`已下载怪物角色图: ${imagePath}`);
            } else {
                this.log(`警告: 未找到怪物 ${monster.name} 的角色图`);
            }
            
            // 保存页面HTML
            fs.writeFileSync(filePath, monsterData.html);
            this.log(`已保存到文件: ${fileName}`);
            
        } catch (error) {
            this.log(`获取 ${monster.name} 的详细信息时出错:`, error);
        }
    }

    async processMonster(monster) {
        while (this.activeTasks >= this.maxConcurrent) {
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        this.activeTasks++;
        try {
            await this.fetchMonsterDetails(monster, this.processedCount, this.totalCount);
            this.processedCount++;
            this.log(`进度: ${this.processedCount}/${this.totalCount} (${Math.round(this.processedCount/this.totalCount*100)}%)`);
        } finally {
            this.activeTasks--;
        }
    }

    async crawl() {
        try {
            await this.init();
            await this.fetchMonsterList();

            const monstersToProcess = this.monsters;
            this.log(`\n准备获取所有 ${monstersToProcess.length} 个怪物的详细信息`);

            for (let i = 0; i < monstersToProcess.length; i++) {
                await this.processMonster(monstersToProcess[i]);

                // 在请求之间添加随机延迟(3-7秒)
                if (i < monstersToProcess.length - 1) {
                    const delay = 3000 + Math.random() * 4000;
                    this.log(`等待 ${Math.round(delay/1000)} 秒后继续下一个怪物...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
            
            this.log('\n全部完成!');
        } catch (error) {
            this.log(`发生错误: ${error.message}`);
        } finally {
            if (this.browser) {
                await this.browser.close();
            }
            this.logStream.end();
        }
    }
}

// 使用示例
const crawler = new MonsterCrawler({
    outputDir: 'dev/html/monsters'
});
crawler.crawl(); 