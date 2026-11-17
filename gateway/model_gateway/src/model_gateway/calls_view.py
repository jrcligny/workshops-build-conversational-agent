"""The « Appels au modèle » page, served by the proxy at `/calls`: one self-contained HTML page
(no external resource) that reads `/calls/conversations` and shows each call turn by turn."""

PAGE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Appels au modèle</title>
<style>
  :root {
    --bg: #f6f7f9; --panel: #fff; --line: #dde1e6; --text: #1f2328; --muted: #656d76;
    --accent: #2f6feb; --add: #e6f6ea; --add-line: #8fd19e; --del: #fdecec; --del-line: #f0a3a3;
    --system: #f3eefe; --user: #e8f1ff; --assistant: #eefaf3; --tool: #fff6e5;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--text); background: var(--bg); }
  header { display: flex; align-items: center; gap: 16px; padding: 10px 18px; background: var(--panel); border-bottom: 1px solid var(--line); }
  header h1 { font-size: 20px; margin: 0; }
  header .folder { color: var(--muted); font-size: 12px; font-family: ui-monospace, Consolas, monospace; }
  header label { margin-left: auto; color: var(--muted); font-size: 13px; }
  main { display: grid; grid-template-columns: 300px 1fr; height: calc(100vh - 49px); }
  nav { overflow: auto; border-right: 1px solid var(--line); background: var(--panel); }
  nav .conv { padding: 10px 14px; border-bottom: 1px solid var(--line); cursor: pointer; }
  nav .conv:hover { background: #f0f3f6; }
  nav .conv.selected { background: #e1ecff; }
  nav .conv.selected .first { font-weight: 600; }
  nav .conv .id { font-family: ui-monospace, Consolas, monospace; font-size: 12px; color: var(--muted); }
  nav .conv .first { margin: 2px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  nav .conv .meta { font-size: 12px; color: var(--muted); }
  section#detail { overflow: auto; padding: 16px 22px 60px; }
  .empty { color: var(--muted); padding: 30px; }
  .turn { margin-bottom: 26px; }
  .turn > h2 { font-size: 17px; margin: 0 0 8px; padding-bottom: 4px; border-bottom: 2px solid var(--line); }
  .turn > h2 .quote { font-weight: normal; color: var(--muted); }
  .call { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; margin: 10px 0; }
  .call > .head { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--line); }
  .call > .head b { font-size: 14px; }
  .chip { display: inline-block; font-size: 12px; padding: 1px 8px; border-radius: 10px; background: #eef1f4; color: var(--muted); }
  .chip.add { background: var(--add); color: #1a7f37; }
  .chip.del { background: var(--del); color: #cf222e; }
  .chip.warn { background: #fff1d6; color: #9a6700; }
  .chip.err { background: #cf222e; color: #fff; }
  .cols { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); }
  .cols > div { padding: 10px 12px; min-width: 0; }
  .cols > div + div { border-left: 1px solid var(--line); }
  h3 { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); margin: 4px 0 8px; }
  .msg { border: 1px solid var(--line); border-radius: 6px; margin: 6px 0; overflow: hidden; }
  .msg .role { font-size: 12px; font-weight: 600; padding: 3px 8px; display: flex; gap: 8px; }
  .msg .role span { font-weight: normal; color: var(--muted); font-family: ui-monospace, Consolas, monospace; }
  .msg.system .role { background: var(--system); } .msg.user .role { background: var(--user); }
  .msg.assistant .role { background: var(--assistant); } .msg.tool .role { background: var(--tool); }
  .msg.added { border-color: var(--add-line); box-shadow: inset 3px 0 0 var(--add-line); }
  .msg.removed { border-color: var(--del-line); box-shadow: inset 3px 0 0 var(--del-line); opacity: .8; }
  pre { margin: 0; padding: 6px 8px; white-space: pre-wrap; word-break: break-word; font: 12.5px/1.45 ui-monospace, Consolas, monospace; max-height: 340px; overflow: auto; }
  details { margin: 6px 0; }
  details > summary { cursor: pointer; color: var(--muted); font-size: 13px; }
  details.kept > summary, details.removed > summary { padding: 4px 8px; border-radius: 6px; }
  details.kept > summary { background: #f0f3f6; }
  details.removed > summary { background: var(--del); color: #cf222e; }
  .kv { font-size: 13px; color: var(--muted); margin: 4px 0; }
  .kv code { color: var(--text); }
  a { color: var(--accent); }
</style>
</head>
<body>
<header>
  <h1>Appels au modèle</h1>
  <span class="folder" id="folder"></span>
  <label><input type="checkbox" id="live" checked> Actualiser automatiquement</label>
</header>
<main>
  <nav id="conversations"><div class="empty">Chargement…</div></nav>
  <section id="detail"><div class="empty">Choisissez une conversation.</div></section>
</main>
<script>
"use strict";
const state = { selected: null, calls: [], last: 0 };

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") node.className = v; else if (k.startsWith("on")) node.addEventListener(k.slice(2), v); else node.setAttribute(k, v);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}
const text = (value) => typeof value === "string" ? value : JSON.stringify(value, null, 2);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const toolName = (t) => (t && (t.function || t).name) || "?";
const time = (iso) => iso ? new Date(iso).toLocaleTimeString("fr-FR") : "";

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(response.status);
  return response.json();
}

async function loadConversations() {
  const data = await getJson("calls/conversations");
  document.getElementById("folder").textContent = data.folder;
  const nav = document.getElementById("conversations");
  nav.replaceChildren();
  if (!data.conversations.length) nav.append(el("div", { class: "empty" }, "Aucun appel enregistré pour l’instant. Envoyez un message dans le chat."));
  for (const c of data.conversations) {
    nav.append(el("div", { class: "conv" + (c.id === state.selected ? " selected" : ""), onclick: () => select(c.id) },
      el("div", { class: "first" }, c.first_message || "(sans message utilisateur)"),
      el("div", { class: "id" }, c.id),
      el("div", { class: "meta" }, `${c.calls} appel${c.calls > 1 ? "s" : ""}` + (c.turns ? ` · ${c.turns} tour${c.turns > 1 ? "s" : ""}` : "") + ` · ${time(c.recorded_at)}`)));
  }
  if (!state.selected && data.conversations.length) select(data.conversations[0].id);
}

async function select(id) {
  if (id !== state.selected) { state.selected = id; state.calls = []; state.last = 0; }
  document.querySelectorAll("nav .conv").forEach((n) => n.classList.toggle("selected", n.querySelector(".id").textContent === id));
  await loadCalls(true);
}

async function loadCalls(force) {
  const id = state.selected;
  if (!id) return;
  const data = await getJson(`calls/conversations/${encodeURIComponent(id)}?since=${state.last}`);
  if (id !== state.selected) return;
  // Two loads can overlap (selection + periodic refresh): only keep calls not already shown.
  const fresh = data.calls.filter((c) => c.call > state.last);
  if (!fresh.length && !force) return;
  state.calls.push(...fresh);
  if (state.calls.length) state.last = state.calls[state.calls.length - 1].call;
  render();
}

// The previous call of the same "flow": same system prompt (the agent's calls apart from, say, compaction calls).
function previousOf(index) {
  const call = state.calls[index];
  for (let i = index - 1; i >= 0; i--) if (state.calls[i].system_sha256 === call.system_sha256) return state.calls[i];
  return null;
}

function diff(previous, current) {
  const before = (previous && previous.request.messages) || [];
  const after = current.request.messages || [];
  let prefix = 0;
  while (prefix < before.length && prefix < after.length && same(before[prefix], after[prefix])) prefix++;
  return { kept: after.slice(0, prefix), removed: before.slice(prefix), added: after.slice(prefix) };
}

function message(m, extra) {
  const role = m.role || "?";
  const label = [m.name, m.tool_call_id].filter(Boolean).join(" · ");
  const body = [];
  if (m.content !== undefined && m.content !== null && m.content !== "") body.push(el("pre", {}, text(m.content)));
  for (const call of m.tool_calls || []) {
    const f = call.function || call;
    let args = f.arguments;
    try { args = JSON.stringify(JSON.parse(args), null, 2); } catch (_) { args = text(args); }
    body.push(el("pre", {}, `→ ${f.name}(${args})${call.id ? `   [${call.id}]` : ""}`));
  }
  if (!body.length) body.push(el("pre", {}, "(vide)"));
  return el("div", { class: `msg ${role} ${extra || ""}` }, el("div", { class: "role" }, role, label && el("span", {}, label)), body);
}

function callCard(call, index) {
  const previous = previousOf(index);
  const d = diff(previous, call);
  const response = call.response || {};
  const usage = response.usage || {};
  const tools = call.request.tools || [];
  const names = tools.map(toolName);
  const previousNames = previous ? (previous.request.tools || []).map(toolName) : [];
  const toolsAdded = previous ? names.filter((n) => !previousNames.includes(n)) : [];
  const toolsRemoved = previous ? previousNames.filter((n) => !names.includes(n)) : [];
  const flow = state.calls[0] && call.system_sha256 !== state.calls[0].system_sha256;

  const chips = [];
  if (call.error) chips.push(el("span", { class: "chip err" }, `erreur ${call.status}`));
  if (flow) chips.push(el("span", { class: "chip warn" }, "autre prompt système (compaction ?)"));
  if (previous) {
    if (d.added.length) chips.push(el("span", { class: "chip add" }, `+${d.added.length} message${d.added.length > 1 ? "s" : ""}`));
    if (d.removed.length) chips.push(el("span", { class: "chip del" }, `−${d.removed.length} message${d.removed.length > 1 ? "s" : ""}`));
    if (toolsAdded.length) chips.push(el("span", { class: "chip add" }, `outils +${toolsAdded.join(", +")}`));
    if (toolsRemoved.length) chips.push(el("span", { class: "chip del" }, `outils −${toolsRemoved.join(", −")}`));
  } else {
    chips.push(el("span", { class: "chip" }, "premier appel"));
  }

  const input = [el("h3", {}, `Entrée envoyée au modèle — ${(call.request.messages || []).length} messages`)];
  if (previous && d.kept.length) {
    input.push(el("details", { class: "kept" }, el("summary", {}, `${d.kept.length} message${d.kept.length > 1 ? "s" : ""} identique${d.kept.length > 1 ? "s" : ""} à l’appel #${previous.call}`), d.kept.map((m) => message(m))));
  }
  if (d.removed.length) {
    input.push(el("details", { class: "removed" }, el("summary", {}, `${d.removed.length} message${d.removed.length > 1 ? "s" : ""} de l’appel #${previous.call} absent${d.removed.length > 1 ? "s" : ""} ici`), d.removed.map((m) => message(m, "removed"))));
  }
  input.push(...(previous ? d.added : call.request.messages || []).map((m) => message(m, previous ? "added" : "")));
  input.push(el("details", {}, el("summary", {}, `Outils proposés (${tools.length})` + (names.length ? ` : ${names.join(", ")}` : "")), el("pre", {}, text(tools))));
  const params = { model: call.request.model, temperature: call.request.temperature, stream: call.request.stream };
  input.push(el("div", { class: "kv" }, "Paramètres : ", el("code", {}, JSON.stringify(params))));

  const output = [el("h3", {}, "Réponse du modèle")];
  if (call.error) output.push(el("pre", {}, text(call.error)));
  else output.push(message(response.message || { role: "assistant", content: response.content, tool_calls: response.tool_calls }));
  output.push(el("div", { class: "kv" }, "Fin : ", el("code", {}, String(response.finish_reason ?? "—")), " · modèle : ", el("code", {}, String(response.model ?? "—"))));
  output.push(el("div", { class: "kv" }, "Jetons : ", el("code", {}, `${usage.prompt_tokens ?? "?"} en entrée, ${usage.completion_tokens ?? "?"} en sortie, ${usage.total_tokens ?? "?"} au total`)));
  output.push(el("details", {}, el("summary", {}, `JSON brut (${call.file || ""})`), el("pre", {}, JSON.stringify(call, null, 2))));

  return el("div", { class: "call", id: `call-${call.call}` },
    el("div", { class: "head" }, el("b", {}, `Appel #${call.call}`), el("span", { class: "chip" }, call.mode), el("span", { class: "chip" }, `${call.duration_ms} ms`),
      el("span", { class: "chip" }, `${usage.total_tokens ?? 0} jetons`), chips, el("span", { class: "chip" }, time(call.recorded_at))),
    el("div", { class: "cols" }, el("div", {}, input), el("div", {}, output)));
}

function render() {
  const detail = document.getElementById("detail");
  const atBottom = detail.scrollTop + detail.clientHeight >= detail.scrollHeight - 40;
  detail.replaceChildren();
  if (!state.calls.length) { detail.append(el("div", { class: "empty" }, "Aucun appel dans cette conversation.")); return; }
  let group = null, current;
  state.calls.forEach((call, index) => {
    if (!group || call.turn !== current) {
      current = call.turn;
      const user = [...(call.request.messages || [])].reverse().find((m) => m.role === "user");
      group = el("div", { class: "turn" }, el("h2", {}, call.turn ? `Tour ${call.turn} ` : "Hors tour ", user && el("span", { class: "quote" }, `« ${text(user.content).slice(0, 160)} »`)));
      detail.append(group);
    }
    group.append(callCard(call, index));
  });
  if (atBottom) detail.scrollTop = detail.scrollHeight;
}

async function refresh() {
  try { await loadConversations(); await loadCalls(false); } catch (error) { console.warn(error); }
}
refresh();
setInterval(() => { if (document.getElementById("live").checked) refresh(); }, 3000);
</script>
</body>
</html>
"""
