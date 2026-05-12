'use strict';

const { chromium } = require('playwright');
const { SESSION_FILE, writeSession } = require('../session');
const { loadConfigFile } = require('../config');

module.exports = function (program) {
  program
    .command('connect <wsEndpoint>')
    .description('Attach to an existing browser via CDP WebSocket endpoint (ownsBrowser=false)')
    .option('--config <file>', 'Sanitizer config JSON file (stored in session)')
    .action(async (wsEndpoint, options) => {
      try {
        const sanitizerConfig = loadConfigFile(options.config || null);

        const browser = await chromium.connectOverCDP(wsEndpoint);
        const contexts = browser.contexts();
        const context = contexts.length > 0 ? contexts[0] : await browser.newContext();
        const pages = context.pages();
        const page = pages.length > 0 ? pages[0] : await context.newPage();
        const currentUrl = page.url();
        await browser.disconnect();

        writeSession({ wsEndpoint, ownsBrowser: false, currentUrl, sanitizerConfig });

        console.log(`Connected to browser at ${wsEndpoint}`);
        console.log(`Session saved: ${SESSION_FILE}`);
        console.log(`ownsBrowser=false — 'close' will disconnect only, not terminate.`);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
