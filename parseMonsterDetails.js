const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

// 获取所有存在的怪物详情文件
const monsterDir = path.join(__dirname, 'data/monsters');
const monsterFiles = fs.readdirSync(monsterDir)
    .filter(file => file.startsWith('monster_detail_') && file.endsWith('.html') && !file.includes('debug'))
    .map(file => {
        const name = file.replace('monster_detail_', '').replace('.html', '');
        const parts = name.split('_');
        const id = parseInt(parts[0]);
        const monsterName = parts.slice(1).join(' ');
        return {
            id,
            name: monsterName,
            file: path.join(monsterDir, file)
        };
    })
    .sort((a, b) => a.id - b.id); // 移除 slice(0, 5)，处理所有文件

console.log(`找到 ${monsterFiles.length} 个怪物详情文件`);

// 处理每个怪物
const detailedMonsters = monsterFiles.map(monsterFile => {
    console.log(`\n正在解析 ${monsterFile.name} 的详细信息...`);
    
    try {
        const html = fs.readFileSync(monsterFile.file, 'utf8');
        const $ = cheerio.load(html);
        
        // 提取技能信息
        const skills = [];
        $('h3:contains("Skills")').next().find('.█').each((i, elem) => {
            const skillName = $(elem).find('h3._aB').text().trim();
            const skillDescription = $(elem).find('._bq').text().trim();
            const skillIcon = $(elem).find('img').attr('src');
            if (skillName && skillDescription) {
                skills.push({
                    name: skillName,
                    description: skillDescription,
                    icon: skillIcon
                });
            }
        });

        // 提取物品信息
        const items = [];
        $('h3:contains("Items")').next().find('.█').each((i, elem) => {
            const itemName = $(elem).find('h3._aB').text().trim();
            const itemDescription = $(elem).find('._bq').text().trim();
            const itemIcon = $(elem).find('img').attr('src');
            const itemStyle = $(elem).find('img').attr('style') || '';
            
            // 尝试从style属性中提取尺寸信息
            let itemWidth = null;
            let itemHeight = null;
            const widthMatch = itemStyle.match(/width:\s*(\d+)px/);
            const heightMatch = itemStyle.match(/height:\s*(\d+)px/);
            if (widthMatch) itemWidth = parseInt(widthMatch[1]);
            if (heightMatch) itemHeight = parseInt(heightMatch[1]);
            
            let itemSize = null;
            if (itemWidth && itemHeight) {
                const ratio = itemWidth / itemHeight;
                if (Math.abs(ratio - 0.5) < 0.05) {
                    itemSize = 'small';
                } else if (Math.abs(ratio - 1) < 0.1) {
                    itemSize = 'medium';
                } else if (Math.abs(ratio - 1.5) < 0.1) {
                    itemSize = 'large';
                }
            }
            
            if (itemName && itemDescription) {
                items.push({
                    name: itemName,
                    description: itemDescription,
                    icon: itemIcon,
                    dimensions: {
                        width: itemWidth,
                        height: itemHeight,
                        aspectRatio: itemWidth && itemHeight ? itemWidth / itemHeight : null
                    },
                    size: itemSize
                });
            }
        });

        // 获取怪物链接和图标
        const link = $('meta[property="og:url"]').attr('content');
        const icon = $('meta[property="og:image"]').attr('content');

        return {
            id: monsterFile.id,
            name: monsterFile.name,
            link: link || '',
            icon: icon || '',
            skills,
            items
        };
    } catch (error) {
        console.error(`解析 ${monsterFile.name} 时出错:`, error);
        return null;
    }
});

// 过滤掉解析失败的怪物并保存结果
const validMonsters = detailedMonsters.filter(monster => monster !== null);
console.log('\n正在保存详细信息...');
const outputPath = path.join(monsterDir, 'monsters_detailed.json');
fs.writeFileSync(outputPath, JSON.stringify(validMonsters, null, 2));
console.log('详细信息已保存到 ' + outputPath); 