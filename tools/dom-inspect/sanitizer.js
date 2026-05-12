'use strict';

/**
 * Walk the DOM via page.evaluate() and return a depth-indented attribute tree.
 * The entire walk runs inside the browser — no per-element Playwright round-trips.
 *
 * Output per line:
 *   {indent}{tag}[{attr}="{val}"]... "{text}" (visible|hidden)
 *
 * Only elements that match at least one focus_selector OR have at least one
 * include_attribute are emitted. Hidden elements are skipped unless show_hidden=true.
 */
async function snapshot(page, config) {
  return page.evaluate((cfg) => {
    const {
      include_attributes,
      focus_selectors,
      exclude_selectors,
      max_depth,
      truncate_text,
      show_hidden
    } = cfg;

    function matchesAny(el, selectors) {
      for (const sel of selectors) {
        try { if (el.matches(sel)) return true; } catch (e) { /* ignore */ }
      }
      return false;
    }

    function isVisible(el) {
      const style = window.getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') return false;
      const rect = el.getBoundingClientRect();
      return rect.width > 0 || rect.height > 0;
    }

    function getIncludedAttrs(el) {
      const parts = [];
      for (const attr of el.attributes) {
        if (include_attributes.includes(attr.name)) {
          parts.push(`[${attr.name}="${attr.value}"]`);
        }
      }
      return parts.join('');
    }

    function hasIncludedAttr(el) {
      for (const attr of el.attributes) {
        if (include_attributes.includes(attr.name)) return true;
      }
      return false;
    }

    function isRelevant(el) {
      return matchesAny(el, focus_selectors) || hasIncludedAttr(el);
    }

    function truncateText(text, max) {
      if (!text) return '';
      const norm = text.trim().replace(/\s+/g, ' ');
      return norm.length > max ? norm.slice(0, max) + '...' : norm;
    }

    const lines = [];

    function walk(el, depth) {
      if (depth > max_depth) return;
      if (matchesAny(el, exclude_selectors)) return;

      const visible = isVisible(el);
      if (!show_hidden && !visible) return;

      if (isRelevant(el)) {
        const indent = '  '.repeat(depth);
        const tag = el.tagName.toLowerCase();
        const attrStr = getIncludedAttrs(el);
        // Use own text only (direct text node children), not descendant text
        const ownText = Array.from(el.childNodes)
          .filter(n => n.nodeType === 3 /* TEXT_NODE */)
          .map(n => n.textContent)
          .join('');
        const text = truncateText(ownText, truncate_text);
        const vis = visible ? 'visible' : 'hidden';
        const textPart = text ? ` "${text}"` : '';
        lines.push(`${indent}${tag}${attrStr}${textPart} (${vis})`);
      }

      for (const child of el.children) {
        walk(child, depth + 1);
      }
    }

    if (document.body) {
      walk(document.body, 0);
    }
    return lines.join('\n');
  }, config);
}

module.exports = { snapshot };
