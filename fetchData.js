const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs').promises;

const BASE_URL = 'https://bazaardb.gg';

// 获取所有怪物的链接
async function fetchMonsterList() {
    const url = `${BASE_URL}/search?c=monsters`;
    const { data } = await axios.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    const $ = cheerio.load(data);
    const monsterLinks = [];
    $('a.card-link').each((i, el) => {
        const href = $(el).attr('href');
        const name = $(el).find('.card-title').text().trim();
        if (href && name) {
            monsterLinks.push({ name, href: BASE_URL + href });
        }
    });
    return monsterLinks;
}

// 获取单个怪物的技能和掉落物品
async function fetchMonsterDetail(monster) {
    const { href, name } = monster;
    const { data } = await axios.get(href, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    const $ = cheerio.load(data);

    // 技能
    const skills = [];
    // 找到“Skills”标题后面的卡片
    $('h2:contains("Skills")').next().find('.card').each((i, el) => {
        const icon = $(el).find('img').attr('src');
        const skillName = $(el).find('.card-title').text().trim();
        const desc = $(el).find('.card-description').text().trim();
        skills.push({
            icon: icon ? (icon.startsWith('http') ? icon : BASE_URL + icon) : '',
            name: skillName,
            description: desc
        });
    });

    // 掉落物品
    const items = [];
    // 找到“Items”标题后面的卡片
    $('h2:contains("Items")').next().find('.card').each((i, el) => {
        const icon = $(el).find('img').attr('src');
        const itemName = $(el).find('.card-title').text().trim();
        const desc = $(el).find('.card-description').text().trim();
        items.push({
            icon: icon ? (icon.startsWith('http') ? icon : BASE_URL + icon) : '',
            name: itemName,
            description: desc
        });
    });

    return {
        name,
        url: href,
        skills,
        items
    };
}

async function main() {
    const monsters = await fetchMonsterList();
    const result = [];
    for (let i = 0; i < monsters.length; i++) {
        console.log(`正在抓取: ${monsters[i].name} (${i + 1}/${monsters.length})`);
        try {
            const detail = await fetchMonsterDetail(monsters[i]);
            result.push(detail);
        } catch (e) {
            console.log(`抓取失败: ${monsters[i].name}`, e.message);
        }
    }
    await fs.writeFile('monsters.json', JSON.stringify(result, null, 2), 'utf-8');
    console.log('全部完成，已保存到 monsters.json');
}

main();