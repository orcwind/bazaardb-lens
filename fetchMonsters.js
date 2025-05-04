const puppeteer = require('puppeteer');
const fs = require('fs');

// 重试函数
async function retry(fn, retries = 3, delay = 5000) {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === retries - 1) throw error;
      console.log(`尝试失败，${delay/1000}秒后重试...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// 检查文件是否存在
function fileExists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.F_OK);
    return true;
  } catch (err) {
    return false;
  }
}

(async () => {
  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null
  });
  const page = await browser.newPage();
  let monsters = [];
  
  try {
    console.log('开始执行...');
    
    // 设置更长的超时时间
    page.setDefaultTimeout(120000);
    page.setDefaultNavigationTimeout(120000);
    
    // 如果monsters.json存在，直接读取
    if (fileExists('monsters.json')) {
      console.log('从monsters.json读取怪物列表...');
      monsters = JSON.parse(fs.readFileSync('monsters.json', 'utf8'));
      console.log(`读取到 ${monsters.length} 个怪物信息`);
    } else {
      console.log('正在访问怪物列表页面...');
      await retry(async () => {
        await page.goto('https://bazaardb.gg/search?c=monsters', {
          waitUntil: 'networkidle0',
          timeout: 120000
        });
      });
      console.log('访问页面成功');

      // 等待页面加载完成
      console.log('等待页面加载...');
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      // 调试：保存页面内容
      const pageContent = await page.content();
      fs.writeFileSync('debug.html', pageContent);
      console.log('已保存页面内容到 debug.html');
      
      // 获取所有怪物基本信息
      console.log('正在获取怪物基本信息...');
      monsters = await page.$$eval('a[href*="/card/"]', cards => {
        return cards.map(card => {
          const nameEl = card.querySelector('h3');
          const name = nameEl?.innerText.trim() || '';
          
          return {
            name,
            link: card.href || ''
          };
        }).filter(monster => monster.name && monster.link); // 过滤掉无效数据
      });

      console.log(`找到 ${monsters.length} 个怪物`);
      
      // 保存所有怪物基本信息
      fs.writeFileSync('monsters.json', JSON.stringify(monsters, null, 2));
      console.log('已保存所有怪物基本信息到 monsters.json');
    }
    
    // 只获取前5个怪物的详细信息
    const monstersToProcess = monsters.slice(0, 5);
    console.log(`准备获取前 ${monstersToProcess.length} 个怪物的详细信息`);

    for (let i = 0; i < monstersToProcess.length; i++) {
      const monster = monstersToProcess[i];
      const fileName = `monster_detail_${i + 1}_${monster.name.replace(/[^a-zA-Z0-9]/g, '_')}.html`;
      
      // 如果文件已存在，跳过
      if (fileExists(fileName)) {
        console.log(`\n[${i + 1}/5] ${monster.name} 的详细信息已存在，跳过`);
        continue;
      }
      
      console.log(`\n[${i + 1}/5] 正在处理 ${monster.name}`);
      console.log(`正在访问 ${monster.name} 的详情页面: ${monster.link}`);
      
      try {
        await retry(async () => {
          console.log('开始导航到详情页面...');
          await page.goto(monster.link, {
            waitUntil: 'networkidle0',
            timeout: 120000
          });
          console.log('导航完成');
        });
        
        // 等待页面加载完成
        console.log('等待页面渲染...');
        await new Promise(resolve => setTimeout(resolve, 5000));
        console.log('页面渲染完成');
        
        // 保存页面内容以供分析
        console.log('正在获取页面内容...');
        const html = await page.content();
        console.log(`获取到页面内容，长度: ${html.length} 字符`);
        
        // 保存HTML文件
        console.log(`正在保存到文件: ${fileName}`);
        fs.writeFileSync(fileName, html);
        console.log('已保存详情页面HTML');
        
      } catch (error) {
        console.error(`获取 ${monster.name} 的详细信息时出错:`, error);
      }

      // 在请求之间添加随机延迟(3-7秒)以避免请求过快
      if (i < monstersToProcess.length - 1) {
        const delay = 3000 + Math.random() * 4000;
        console.log(`等待 ${Math.round(delay/1000)} 秒后继续下一个怪物...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    console.log('\n全部完成!');

  } catch (error) {
    console.error('发生错误:', error);
  } finally {
    await browser.close();
  }
})();
