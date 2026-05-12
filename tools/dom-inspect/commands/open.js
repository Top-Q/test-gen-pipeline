'use strict';

const { chromium } = require('playwright');
const { SESSION_FILE, writeSession } = require('../session');
const { loadConfigFile } = require('../config');

module.exports = function (program) {
  program
    .command('open')
    .description('Launch a new browser instance')
    .option('--state <file>', 'Restore storage state from file (Playwright format)')
    .option('--config <file>', 'Sanitizer config JSON file (stored in session)')
    .action(async (options) => {
      try {
        const sanitizerConfig = loadConfigFile(options.config || null);

        // launchServer() starts a standalone browser process.
        // After unref()-ing its subprocess, the browser survives this Node.js process exiting.
        const server = await chromium.launchServer({ headless: false });
        const wsEndpoint = server.wsEndpoint();

        // Create initial context (with optional auth state restore) and a first page.
        const browser = await chromium.connectOverCDP(wsEndpoint);
        const contextOptions = options.state ? { storageState: options.state } : {};
        const context = await browser.newContext(contextOptions);
        const page = await context.newPage();
        const currentUrl = page.url();
        await browser.disconnect();

        // Detach the browser server subprocess so it keeps running after we exit.
        server.process().unref();

        writeSession({ wsEndpoint, ownsBrowser: true, currentUrl, sanitizerConfig });

        console.log(`Browser launched.`);
        console.log(`WS endpoint: ${wsEndpoint}`);
        console.log(`Session saved: ${SESSION_FILE}`);

        process.exit(0);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
