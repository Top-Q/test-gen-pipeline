'use strict';

const { readSession, getPageFromSession } = require('../session');
const { loadConfigFile, mergeConfig } = require('../config');
const { snapshot } = require('../sanitizer');

const DEFAULT_MAX_LINES = 150;

module.exports = function (program) {
  program
    .command('snapshot')
    .description('Capture a DOM attribute tree of the current page')
    .option('--config <file>', 'Per-command sanitizer config override (not saved to session)')
    .option('--selector <css>', 'Scope snapshot to a specific element (e.g. \'[role="dialog"]\')')
    .option('--max-lines <n>', `Limit output lines (default: ${DEFAULT_MAX_LINES}; 0 = unlimited)`, String(DEFAULT_MAX_LINES))
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
        // Wait for any pending async loads (turbo-frames, SPA routing) before reading the DOM
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        const raw = await snapshot(page, config, options.selector || null);
        await browser.close();

        const maxLines = parseInt(options.maxLines, 10);
        if (maxLines > 0 && raw && !raw.startsWith('[snapshot:')) {
          const lines = raw.split('\n');
          if (lines.length > maxLines) {
            const truncated = lines.slice(0, maxLines).join('\n');
            console.log(truncated);
            console.log(`\n[Snapshot truncated: showing ${maxLines} of ${lines.length} lines]`);
            console.log(`[Use --selector '<css>' to scope, or --max-lines 0 for full output]`);
          } else {
            console.log(raw);
            console.log(`\n[Snapshot: ${lines.length} lines]`);
          }
        } else {
          console.log(raw);
        }
      } catch (err) {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
      }
    });
};
