'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('fill <selector> <value>')
    .description('Fill an input element with a value')
    .action(async (selector, value) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);
        await page.fill(selector, value);
        await browser.disconnect();
        console.log(`Filled: ${selector}`);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
