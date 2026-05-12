'use strict';

const { chromium } = require('playwright');
const { readSession, deleteSession } = require('../session');

module.exports = function (program) {
  program
    .command('close')
    .description('Close the browser (or disconnect if not owned) and remove the session file')
    .action(async () => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session.\n');
        process.exit(0);
      }
      try {
        const browser = await chromium.connectOverCDP(session.wsEndpoint);
        // browser.close() over CDP sends Browser.close which terminates the Chromium process
        await browser.close();
        console.log('Browser closed.');
      } catch (err) {
        // Browser may already be gone — still clean up the session
        process.stderr.write(`Warning: could not connect to browser: ${err.message}\n`);
      }
      deleteSession();
      console.log('Session removed.');
    });
};
