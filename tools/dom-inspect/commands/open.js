'use strict';

const fs = require('fs');
const http = require('http');
const net = require('net');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');
const { SESSION_FILE, writeSession } = require('../session');
const { loadConfigFile } = require('../config');

function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on('error', reject);
  });
}

function waitForCDP(port, timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    function attempt() {
      http.get(`http://127.0.0.1:${port}/json/version`, (res) => {
        res.resume();
        resolve();
      }).on('error', () => {
        if (Date.now() < deadline) {
          setTimeout(attempt, 300);
        } else {
          reject(new Error(`CDP not ready at port ${port} after ${timeoutMs}ms`));
        }
      });
    }
    attempt();
  });
}

module.exports = function (program) {
  program
    .command('open')
    .description('Launch a new browser instance')
    .option('--state <file>', 'Restore storage state from file (Playwright storageState format)')
    .option('--config <file>', 'Sanitizer config JSON file (stored in session)')
    .option('--headless', 'Run browser in headless mode')
    .action(async (options) => {
      try {
        const sanitizerConfig = loadConfigFile(options.config || null);
        const port = await findFreePort();
        const userDataDir = path.join(os.tmpdir(), `dom-inspect-${port}`);

        // Resolve the Chromium executable bundled with this package's playwright
        const execPath = chromium.executablePath();

        const args = [
          `--remote-debugging-port=${port}`,
          `--user-data-dir=${userDataDir}`,
          '--window-size=1280,800',   // explicit viewport so getBoundingClientRect() works in headless
          '--no-first-run',
          '--no-default-browser-check',
        ];
        if (options.headless) {
          args.push('--headless=new');
        }

        // Detached spawn so the browser survives this Node.js process exiting (works on Windows)
        const child = spawn(execPath, args, {
          detached: true,
          stdio: 'ignore',
        });
        child.unref();

        // Wait for CDP server to become available
        await waitForCDP(port);

        const cdpEndpoint = `http://127.0.0.1:${port}`;
        let currentUrl = 'about:blank';

        // Restore auth state if requested
        if (options.state) {
          if (!fs.existsSync(options.state)) {
            process.stderr.write(`Warning: state file not found: ${options.state}\n`);
          } else {
            const browser = await chromium.connectOverCDP(cdpEndpoint);
            const contexts = browser.contexts();
            const context = contexts.length > 0 ? contexts[0] : await browser.newContext();
            const pages = context.pages();
            const page = pages.length > 0 ? pages[0] : await context.newPage();

            const stateData = JSON.parse(fs.readFileSync(options.state, 'utf8'));

            if (stateData.cookies && stateData.cookies.length > 0) {
              await context.addCookies(stateData.cookies);
            }
            if (stateData.origins) {
              for (const origin of stateData.origins) {
                if (origin.localStorage && origin.localStorage.length > 0) {
                  await page.goto(origin.origin, { waitUntil: 'domcontentloaded' });
                  await page.evaluate((items) => {
                    for (const { name, value } of items) {
                      localStorage.setItem(name, value);
                    }
                  }, origin.localStorage);
                }
              }
            }
            currentUrl = page.url();
            await browser.close();
          }
        }

        writeSession({ wsEndpoint: cdpEndpoint, ownsBrowser: true, currentUrl, sanitizerConfig });

        console.log(`Browser launched.`);
        console.log(`CDP endpoint: ${cdpEndpoint}`);
        console.log(`Session saved: ${SESSION_FILE}`);

        process.exit(0);
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
