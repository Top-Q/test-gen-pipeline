'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('click <selector>')
    .description('Click an element matching the selector')
    .option('--force', 'Bypass visibility/actionability checks (force click)')
    .action(async (selector, options) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);
        const loc = page.locator(selector).first();
        if (options.force) {
          await loc.click({ force: true });
        } else {
          await loc.scrollIntoViewIfNeeded();
          await loc.click();
        }
        await browser.close();
        console.log(`Clicked: ${selector}`);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
