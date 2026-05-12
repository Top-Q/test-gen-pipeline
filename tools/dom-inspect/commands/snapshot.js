'use strict';

const { readSession, getPageFromSession } = require('../session');
const { loadConfigFile, mergeConfig } = require('../config');
const { snapshot } = require('../sanitizer');

module.exports = function (program) {
  program
    .command('snapshot')
    .description('Capture a DOM attribute tree of the current page')
    .option('--config <file>', 'Per-command sanitizer config override (not saved to session)')
    .action(async (options) => {
      const session = readSession();
      if (!session) {
        process.stderr.write('No active session. Run `dom-inspect open` first.\n');
        process.exit(1);
      }
      try {
        const overrideConfig = loadConfigFile(options.config || null);
        const config = mergeConfig(session.sanitizerConfig, overrideConfig);

        const { browser, page } = await getPageFromSession(session);
        const output = await snapshot(page, config);
        await browser.disconnect();

        console.log(output);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
