'use strict';

const { readSession, writeSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('goto <url>')
    .description('Navigate to a URL (waits for networkidle)')
    .action(async (url) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);
        await page.goto(url, { waitUntil: 'networkidle' });
        const currentUrl = page.url();
        await browser.disconnect();

        writeSession({ ...session, currentUrl });
        console.log(`Navigated to: ${currentUrl}`);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
