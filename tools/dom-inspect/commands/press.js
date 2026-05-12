'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('press <selector> <key>')
    .description('Focus an element and press a keyboard key (e.g., Return, Tab, Escape)')
    .action(async (selector, key) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);
        await page.locator(selector).first().press(key);
        await browser.close();
        console.log(`Pressed ${key} on: ${selector}`);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
