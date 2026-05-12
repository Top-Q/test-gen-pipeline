'use strict';

const fs = require('fs');

const DEFAULTS = {
  include_attributes: [
    'id', 'data-qa-selector', 'data-testid', 'role',
    'aria-label', 'name', 'type', 'href', 'placeholder'
  ],
  focus_selectors: [
    '[data-qa-selector]', '[id]', 'button',
    'input', 'a[href]', 'select', 'textarea'
  ],
  exclude_selectors: [
    'script', 'style', 'svg', 'noscript', 'head'
  ],
  max_depth: 20,
  truncate_text: 60,
  show_hidden: false
};

/**
 * Load a config file from disk. Returns {} if path is null/missing/invalid.
 */
function loadConfigFile(filePath) {
  if (!filePath) return {};
  if (!fs.existsSync(filePath)) {
    process.stderr.write(`Warning: config file not found: ${filePath}\n`);
    return {};
  }
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (e) {
    process.stderr.write(`Warning: failed to parse config ${filePath}: ${e.message}\n`);
    return {};
  }
}

/**
 * Merge config layers: defaults < sessionConfig < overrideConfig.
 * Arrays replace (not concat) — later wins.
 */
function mergeConfig(sessionConfig, overrideConfig) {
  return Object.assign({}, DEFAULTS, sessionConfig || {}, overrideConfig || {});
}

module.exports = { DEFAULTS, loadConfigFile, mergeConfig };
