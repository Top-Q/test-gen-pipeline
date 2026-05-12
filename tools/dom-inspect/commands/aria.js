'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('aria')
    .description('Capture the ARIA accessibility tree of the current page')
    .option('--selector <css>', 'Scope ARIA snapshot to a specific element (e.g. \'[role="dialog"]\')')
    .action(async (options) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, page } = await getPageFromSession(session);
        // Wait for any pending async loads (turbo-frames, SPA routing) before reading the DOM
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        const root = options.selector ? page.locator(options.selector).first() : page.locator('body');

        let output;
        try {
          // Playwright 1.46+ ariaSnapshot() on a locator
          output = await root.ariaSnapshot();
        } catch (e) {
          // Fallback: legacy accessibility API (full page only)
          const snap = await page.accessibility.snapshot();
          output = JSON.stringify(snap, null, 2);
        }

        await browser.close();
        console.log(output);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
