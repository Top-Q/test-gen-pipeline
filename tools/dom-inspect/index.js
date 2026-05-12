#!/usr/bin/env node
'use strict';

const { Command } = require('commander');
const program = new Command();

program
  .name('dom-inspect')
  .description('DOM inspection CLI for Playwright-based test generation')
  .version('1.0.0');

require('./commands/open')(program);
require('./commands/connect')(program);
require('./commands/goto')(program);
require('./commands/snapshot')(program);
require('./commands/aria')(program);
require('./commands/locate')(program);
require('./commands/click')(program);
require('./commands/fill')(program);
require('./commands/save-state')(program);
require('./commands/clear-context')(program);
require('./commands/close')(program);

program.parse(process.argv);
