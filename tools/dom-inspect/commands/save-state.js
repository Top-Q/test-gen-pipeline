'use strict';

const { readSession, getPageFromSession } = require('../session');

module.exports = function (program) {
  program
    .command('save-state <file>')
    .description('Save browser auth/session state to a JSON file (Playwright storageState format)')
    .action(async (file) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const { browser, context } = await getPageFromSession(session);
        await context.storageState({ path: file });
        await browser.disconnect();
        console.log(`Auth state saved to: ${file}`);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
