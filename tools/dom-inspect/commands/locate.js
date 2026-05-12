'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('locate <selector>')
    .description('Count elements matching a selector and show tag/text/visible/enabled per match')
    .action(async (selector) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);
        const locator = page.locator(selector);
        const count = await locator.count();

        console.log(`${selector}: ${count} match(es)`);

        if (count === 0) {
          await browser.disconnect();
          process.exit(1);
        }

        for (let i = 0; i < count; i++) {
          const el = locator.nth(i);
          const tag = await el.evaluate(n => n.tagName.toLowerCase());
          const rawText = await el.textContent();
          const text = (rawText || '').trim().replace(/\s+/g, ' ').slice(0, 60);
          const visible = await el.isVisible();
          const enabled = await el.isEnabled();
          console.log(`  [${i}] tag=${tag}, text="${text}", visible=${visible}, enabled=${enabled}`);
        }

        await browser.disconnect();
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
