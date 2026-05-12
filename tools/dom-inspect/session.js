'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require('playwright');

const SESSION_FILE = path.join(os.homedir(), '.dom-inspect-session.json');

function readSession() {
  if (!fs.existsSync(SESSION_FILE)) return null;
  try {
    return JSON.parse(fs.readFileSync(SESSION_FILE, 'utf8'));
  } catch {
    return null;
  }
}

function writeSession(data) {
  fs.writeFileSync(SESSION_FILE, JSON.stringify(data, null, 2), 'utf8');
}

function deleteSession() {
  if (fs.existsSync(SESSION_FILE)) {
    fs.unlinkSync(SESSION_FILE);
  }
}

/**
 * Connect to the browser in the session and return { browser, context, page }.
 * Caller is responsible for calling browser.disconnect() when done.
 */
async function getPageFromSession(session) {
  if (!session || !session.wsEndpoint) {
    throw new Error('No active session. Run `dom-inspect open` first.');
  }
  const browser = await chromium.connectOverCDP(session.wsEndpoint);
  const contexts = browser.contexts();
  const context = contexts.length > 0 ? contexts[0] : await browser.newContext();
  const pages = context.pages();
  const page = pages.length > 0 ? pages[0] : await context.newPage();
  return { browser, context, page };
}

module.exports = { SESSION_FILE, readSession, writeSession, deleteSession, getPageFromSession };
