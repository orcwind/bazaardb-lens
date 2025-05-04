一， 爬虫
2. 怪物.  在https://bazaardb.gg/search?c=monsters获取怪物名称及链接，
需要注意不要将怪物下的skill和item当作怪物保存了。
通过怪物超链接，获得怪物的skill和items信息，只需要获得图标，名称及描述。

限制一下获取信息内容，1 获取所有怪物， 怪物只需要名字，图标，超链接； 
2. 获取前五个怪物超链接对应的skill及item 
只需要名字，图标，描述，其中描述可为多条。
以刚刚获得的第一个怪物举例，只需要获得如下信息，其中也包含所有的图标。

名称: Banannabal

技能:
Overheal Haste 
效果: 每场战斗第一次过量治疗时,为物品提供2-4秒的加速效果

物品:
Med Kit 
效果: 出售时,最左边的治疗物品获得 5/10/20/40 治疗量

Bluenanas
效果: 治疗 10/20/40/80
出售时永久获得 20/60/120/200 最大生命值

Duct Tape
效果: 减速1个目标 1/2/3 秒
使用左边的物品时,获得 5/10/15 护盾

二 游戏工具
制作一个游戏the bazaar的游戏助手，在游戏中运行，实现的效果是当鼠标放置于游戏中的怪物上时，
按alt键到抬起，执行一次识别，其中识别区域为整个游戏窗口，根据识别的结果确认对应怪物，
然后显示此怪物的技能和道具信息，也即之前爬虫获得那些信息。

三 event
通过爬虫@https://bazaardb.gg/search?c=events 获取所有event名称，在每个event下获取所有
的option里的图标和描述。图标均为96x96. 在程序中类似怪物，在event图标上按alt，
显示对应的options

// 添加数据版本控制
constructor(options = {}) {
    this.version = "1.0.0";
    this.dataSchema = {
        version: this.version,
        lastUpdate: new Date().toISOString(),
        events: []
    };
}

async downloadImage(url, filename) {
    // 添加SVG处理
    if (url.startsWith('data:image/svg+xml')) {
        const svgContent = Buffer.from(url.split(',')[1], 'base64').toString();
        const filePath = path.join(this.iconsDir, `${filename}.svg`);
        fs.writeFileSync(filePath, svgContent);
        return filePath;
    }
    // ... 现有代码 ...
}

async parseEventDetails() {
    return await this.page.evaluate(() => {
        const details = {};
        // 基本信息
        details.name = document.querySelector('h1')?.textContent?.trim();
        details.description = document.querySelector('.description')?.textContent?.trim();
        
        // 选项信息
        details.options = Array.from(document.querySelectorAll('.option-card')).map(option => ({
            title: option.querySelector('.title')?.textContent?.trim(),
            description: option.querySelector('.description')?.textContent?.trim(),
            effects: Array.from(option.querySelectorAll('.effect')).map(effect => 
                effect.textContent?.trim()
            ).filter(Boolean)
        }));
        
        // 统计信息
        details.stats = {
            rarity: document.querySelector('.rarity')?.textContent?.trim(),
            type: document.querySelector('.type')?.textContent?.trim()
        };
        
        return details;
    });
}

async crawl() {
    const progressFile = path.join(this.outputDir, 'progress.json');
    let progress = {lastIndex: -1};
    
    if (fs.existsSync(progressFile)) {
        progress = JSON.parse(fs.readFileSync(progressFile, 'utf8'));
    }
    
    for (let i = progress.lastIndex + 1; i < this.events.length; i++) {
        try {
            await this.fetchEventDetails(this.events[i], i, this.events.length);
            progress.lastIndex = i;
            fs.writeFileSync(progressFile, JSON.stringify(progress));
        } catch (error) {
            console.error(`处理事件 ${this.events[i].name} 时出错:`, error);
            // 保存进度并等待一段时间后继续
            await new Promise(resolve => setTimeout(resolve, 30000));
        }
    }
}

validateEventData(event) {
    const requiredFields = ['name', 'url', 'iconUrl'];
    const missingFields = requiredFields.filter(field => !event[field]);
    if (missingFields.length > 0) {
        throw new Error(`事件数据缺少必要字段: ${missingFields.join(', ')}`);
    }
}

async crawlWithConcurrency(concurrency = 3) {
    const chunks = [];
    for (let i = 0; i < this.events.length; i += concurrency) {
        chunks.push(this.events.slice(i, i + concurrency));
    }
    
    for (const chunk of chunks) {
        await Promise.all(chunk.map((event, index) => 
            this.fetchEventDetails(event, index, this.events.length)
        ));
        // 添加延迟避免请求过快
        await new Promise(resolve => setTimeout(resolve, 5000));
    }
}

module.exports = {
    baseUrl: 'https://bazaardb.gg',
    outputDir: 'data/events',
    retryAttempts: 3,
    retryDelay: 5000,
    concurrency: 3,
    timeout: 120000,
    userAgent: 'Mozilla/5.0 ...'
};

const transformEventData = (rawData) => {
    return {
        id: generateEventId(rawData.name),
        name: rawData.name,
        type: rawData.type,
        rarity: rawData.rarity,
        description: rawData.description,
        options: rawData.options.map(transformOption),
        iconPath: rawData.iconPath,
        updatedAt: new Date().toISOString()
    };
};
