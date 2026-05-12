'use strict';

const { readSession, writeSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('goto <url>')
    .description('Navigate to a URL and wait for content to load')
    .option('--wait-for <selector>', 'Also wait until this selector is visible (up to 15s)')
    .action(async (url, options) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);
        await page.goto(url, { waitUntil: 'networkidle' });

        // Second networkidle pass: catches turbo-frame / client-side async fetches that
        // start after the initial networkidle event (e.g. OpenProject work packages list).
        try {
          await page.waitForLoadState('networkidle', { timeout: 5000 });
        } catch { /* already settled — continue */ }

        if (options.waitFor) {
          await page.locator(options.waitFor).first().waitFor({ state: 'visible', timeout: 15000 });
        }

        const currentUrl = page.url();
        await browser.close();

        writeSession({ ...session, currentUrl });
        console.log(`Navigated to: ${currentUrl}`);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
