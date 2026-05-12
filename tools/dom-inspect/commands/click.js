'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('click <selector>')
    .description('Click an element matching the selector')
    .action(async (selector) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);
        await page.click(selector);
        await browser.disconnect();
        console.log(`Clicked: ${selector}`);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
