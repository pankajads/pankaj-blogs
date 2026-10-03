// Copy helpers: rich HTML (for Medium / Docs / email), Markdown (for Reddit / GitHub), link,
// plus the ?kit share panel and the reading-progress bar. No dependencies.
(function () {
  "use strict";

  var toastEl = document.querySelector(".toast");
  var toastTimer;
  function toast(msg) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("is-on"); }, 1800);
  }

  function flash(btn, label) {
    var original = btn.textContent;
    btn.textContent = label;
    btn.classList.add("is-done");
    setTimeout(function () { btn.textContent = original; btn.classList.remove("is-done"); }, 1500);
  }

  function title() {
    var h = document.querySelector(".post-title");
    return h ? h.textContent.trim() : document.title;
  }

  // A clean copy of the article: no ids/classes/styles, no footnote back-arrows, no UI.
  function cleanArticle() {
    var src = document.getElementById("article");
    if (!src) return null;
    var node = src.cloneNode(true);
    node.querySelectorAll("[data-nocopy], .reversefootnote, script, style").forEach(function (el) { el.remove(); });
    node.querySelectorAll("*").forEach(function (el) {
      ["id", "class", "style", "role", "aria-hidden"].forEach(function (a) { el.removeAttribute(a); });
    });
    // Footnote markers link to anchors on this page; keep the number, drop the link.
    node.querySelectorAll("sup a").forEach(function (a) { a.replaceWith(document.createTextNode(a.textContent)); });
    node.querySelectorAll("a[href]").forEach(function (a) { a.setAttribute("href", a.href); });
    node.querySelectorAll("img[src]").forEach(function (img) { img.setAttribute("src", img.src); });
    return node;
  }

  // ---- HTML -> Markdown (covers what kramdown emits for prose posts) ----
  function inline(node) {
    var out = "";
    node.childNodes.forEach(function (n) {
      if (n.nodeType === 3) { out += n.nodeValue.replace(/\s+/g, " "); return; }
      if (n.nodeType !== 1) return;
      var tag = n.tagName.toLowerCase();
      var inner = inline(n);
      if (tag === "strong" || tag === "b") out += "**" + inner.trim() + "**";
      else if (tag === "em" || tag === "i") out += "*" + inner.trim() + "*";
      else if (tag === "code") out += "`" + n.textContent + "`";
      else if (tag === "a") out += n.closest("sup") ? inner : "[" + inner.trim() + "](" + n.getAttribute("href") + ")";
      else if (tag === "sup") out += "[" + inner.trim() + "]";
      else if (tag === "br") out += "  \n";
      else if (tag === "img") out += "![" + (n.getAttribute("alt") || "") + "](" + n.getAttribute("src") + ")";
      else out += inner;
    });
    return out;
  }

  function block(node, depth) {
    var parts = [];
    node.childNodes.forEach(function (n) {
      if (n.nodeType === 3) { if (n.nodeValue.trim()) parts.push(n.nodeValue.trim()); return; }
      if (n.nodeType !== 1) return;
      var tag = n.tagName.toLowerCase();
      var m = /^h([1-6])$/.exec(tag);
      if (m) parts.push("#".repeat(Number(m[1])) + " " + inline(n).trim());
      else if (tag === "p") parts.push(inline(n).trim());
      else if (tag === "blockquote") parts.push(block(n, depth).split("\n").map(function (l) { return l ? "> " + l : ">"; }).join("\n"));
      else if (tag === "pre") parts.push("```\n" + n.textContent.replace(/\n$/, "") + "\n```");
      else if (tag === "hr") parts.push("---");
      else if (tag === "ul" || tag === "ol") {
        var i = 0;
        parts.push(Array.prototype.filter.call(n.children, function (li) { return li.tagName === "LI"; }).map(function (li) {
          i += 1;
          var bullet = tag === "ol" ? i + ". " : "- ";
          var pad = "  ".repeat(depth);
          var nested = "";
          var clone = li.cloneNode(true);
          clone.querySelectorAll("ul, ol").forEach(function (sub) { nested += "\n" + block({ childNodes: [sub] }, depth + 1); sub.remove(); });
          var text = clone.querySelector("p") ? block(clone, depth).replace(/\n\n/g, " ") : inline(clone).trim();
          return pad + bullet + text + nested;
        }).join("\n"));
      }
      else if (tag === "table") {
        var rows = Array.prototype.map.call(n.querySelectorAll("tr"), function (tr) {
          return "| " + Array.prototype.map.call(tr.children, function (c) { return inline(c).trim(); }).join(" | ") + " |";
        });
        if (rows.length) rows.splice(1, 0, rows[0].replace(/[^|]+/g, " --- "));
        parts.push(rows.join("\n"));
      }
      else if (tag === "img") parts.push(inline({ childNodes: [n] }));
      else if (tag === "div" || tag === "section" || tag === "figure") parts.push(block(n, depth));
      else parts.push(inline(n).trim());
    });
    return parts.filter(Boolean).join("\n\n");
  }

  function toMarkdown(article) { return "# " + title() + "\n\n" + block(article, 0).replace(/\n{3,}/g, "\n\n").trim() + "\n"; }

  // ---- clipboard ----
  function writeText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return legacyCopy(function (ta) { ta.value = text; });
  }

  function writeRich(html, text) {
    if (navigator.clipboard && window.ClipboardItem && window.isSecureContext) {
      return navigator.clipboard.write([new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" })
      })]);
    }
    // Fallback: select a hidden rendered copy so the browser copies it as rich text.
    return new Promise(function (resolve, reject) {
      var holder = document.createElement("div");
      holder.innerHTML = html;
      holder.style.cssText = "position:fixed;left:-9999px;top:0;";
      document.body.appendChild(holder);
      var range = document.createRange();
      range.selectNodeContents(holder);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      var ok = document.execCommand("copy");
      sel.removeAllRanges();
      holder.remove();
      ok ? resolve() : reject(new Error("copy failed"));
    });
  }

  function legacyCopy(fill) {
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      fill(ta);
      ta.setAttribute("readonly", "");
      ta.style.cssText = "position:fixed;left:-9999px;top:0;";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      ta.remove();
      ok ? resolve() : reject(new Error("copy failed"));
    });
  }

  function canonicalUrl() {
    var link = document.querySelector('link[rel="canonical"]');
    return link ? link.href : location.href.split(/[?#]/)[0];
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-copy], [data-copy-text]");
    if (!btn) return;
    var job;
    var kind = btn.getAttribute("data-copy");
    if (btn.hasAttribute("data-copy-text")) {
      var target = document.querySelector(btn.getAttribute("data-copy-text"));
      job = writeText(target ? target.textContent.trim() : "");
    } else if (kind === "link") {
      job = writeText(canonicalUrl());
    } else {
      var article = cleanArticle();
      if (!article) return;
      if (kind === "markdown") {
        job = writeText(toMarkdown(article));
      } else {
        var html = "<h1>" + title().replace(/</g, "&lt;") + "</h1>" + article.innerHTML;
        job = writeRich(html, title() + "\n\n" + article.innerText.trim());
      }
    }
    job.then(function () { flash(btn, "Copied ✓"); toast("Copied to clipboard"); })
       .catch(function () { toast("Couldn't copy — select the text and use Ctrl/⌘+C"); });
  });

  // ?kit reveals the share panel (Reddit title/body) without showing it to regular readers.
  if (/[?&]kit\b/.test(location.search)) {
    var kit = document.getElementById("kit");
    if (kit) { kit.hidden = false; kit.scrollIntoView({ block: "start" }); }
  }

  // Reading progress.
  var bar = document.querySelector(".progress span");
  var article = document.getElementById("article");
  if (bar && article) {
    var ticking = false;
    var update = function () {
      var rect = article.getBoundingClientRect();
      var total = rect.height - window.innerHeight;
      var done = total > 0 ? Math.min(1, Math.max(0, -rect.top / total)) : 1;
      bar.style.width = (done * 100).toFixed(1) + "%";
      ticking = false;
    };
    window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    update();
  }
})();
