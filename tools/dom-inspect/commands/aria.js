'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('aria')
    .description('Capture the ARIA accessibility tree of the current page')
    .action(async () => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);

        let output;
        try {
          // Playwright 1.46+ ariaSnapshot() on the body locator
          output = await page.locator('body').ariaSnapshot();
        } catch (e) {
          // Fallback: legacy accessibility API
          const snap = await page.accessibility.snapshot();
          output = JSON.stringify(snap, null, 2);
        }

        await browser.disconnect();
        console.log(output);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
