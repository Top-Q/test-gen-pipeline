'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('wait [ms]')
    .description('Wait for a selector to appear, or for N milliseconds (default: 1000ms)')
    .option('--selector <css>', 'Wait until this selector is visible (up to 10s)')
    .action(async (ms, options) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);

        if (options.selector) {
          await page.locator(options.selector).first().waitFor({ state: 'visible', timeout: 10000 });
          console.log(`Visible: ${options.selector}`);
        } else {
          const delay = ms ? parseInt(ms, 10) : 1000;
          await page.waitForTimeout(delay);
          console.log(`Waited ${delay}ms`);
        }

        await browser.close();
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
