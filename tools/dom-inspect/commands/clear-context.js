'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('clear-context')
    .description('Clear cookies, localStorage, and sessionStorage')
    .action(async () => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, context, page } = await getPageFromSession(session);
        await context.clearCookies();
        await page.evaluate(() => {
          localStorage.clear();
          sessionStorage.clear();
        });
        await browser.disconnect();
        console.log('Context cleared: cookies, localStorage, sessionStorage.');
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
