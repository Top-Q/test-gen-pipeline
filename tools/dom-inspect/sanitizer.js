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
async function snapshot(page, config, rootSelector = null) {
  return page.evaluate(({ cfg, rootSel }) => {
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
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
      // offsetWidth/offsetHeight measure layout dimensions regardless of scroll position
      // or viewport clipping — reliable for elements below the fold or in scroll containers.
      return el.offsetWidth > 0 || el.offsetHeight > 0;
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

      // Emit this element if relevant and (visible or show_hidden requested)
      if (isRelevant(el) && (visible || show_hidden)) {
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

      // Always walk children unless the element is truly display:none or excluded —
      // a container with zero layout dimensions may still have visible children
      // (e.g. turbo-frames while loading, scroll containers below the fold).
      const style = window.getComputedStyle(el);
      if (style.display === 'none') return;

      for (const child of el.children) {
        walk(child, depth + 1);
      }
    }

    const root = rootSel ? document.querySelector(rootSel) : document.body;
    if (!root) {
      return `[snapshot: no element matched selector "${rootSel}"]`;
    }
    walk(root, 0);
    return lines.join('\n');
  }, { cfg: config, rootSel: rootSelector });
}

module.exports = { snapshot };
