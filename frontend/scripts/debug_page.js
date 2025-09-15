const { chromium } = require('playwright');

(async () => {
  const url = process.argv[2] || 'http://localhost:5173/';
  const browser = await chromium.launch();
  const page = await browser.newPage();
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 15000 });
    const title = await page.title();
    console.log('title:', title);
    const content = await page.content();
    console.log('\n--- HTML snippet (first 2000 chars) ---\n');
    console.log(content.slice(0, 2000));
  } catch (err) {
    console.error('error navigating:', err);
    process.exitCode = 2;
  } finally {
    await browser.close();
  }
})();
