/* ============================================================
   Policy Governance Intelligence — Dashboard logic
   ============================================================ */

const state = { report: null, staleness: [], policyScores: [], graph: null };

async function boot() {
  const [report, staleness, policyScores, graph] = await Promise.all([
    fetchJSON('/api/report'),
    fetchJSON('/api/staleness'),
    fetchJSON('/api/policy_scores'),
    fetchJSON('/api/graph'),
  ]);
  state.report = report;
  state.staleness = staleness || [];
  state.policyScores = policyScores || [];
  state.graph = graph;

  if (!report || report.error) {
    document.querySelector('main').innerHTML =
      '<div class="empty-state">No pipeline output yet. Run <span class="mono">python scripts/run_pipeline.py</span> then reload.</div>';
    return;
  }

  renderMasthead(report);
  renderStats(report);
  renderConflicts(report);
  renderRedundant(report);
  renderStaleness(state.staleness);
  renderHealth(state.policyScores);
  renderGraph(state.graph);
  wireTabs();
  wireSorting();
}

async function fetchJSON(url) {
  try {
    const res = await fetch(url);
    return await res.json();
  } catch (e) {
    console.error('fetch failed', url, e);
    return null;
  }
}

function renderMasthead(report) {
  const isLive = report.mode && report.mode.startsWith('live');
  document.getElementById('masthead-meta').innerHTML = `
    <div>mode: <span class="${isLive ? 'mode-live' : 'mode-offline'}">${escapeHtml(report.mode)}</span></div>
    <div>model: ${escapeHtml(report.model || '—')}</div>
    <div>as-of: ${escapeHtml(report.as_of_date || '—')}</div>
  `;
  if (!isLive) {
    const banner = document.getElementById('mode-banner');
    banner.classList.add('show');
    banner.innerHTML = `Running in <strong>offline heuristic mode</strong> — no ANTHROPIC_API_KEY / OPENAI_API_KEY detected. Extraction and classification are using deterministic rules instead of a live LLM. Set an API key and re-run the pipeline for full Option-A LLM reasoning.`;
  }
}

function renderStats(report) {
  const s = report.summary;
  const rel = s.relationships_deduped || s.relationships; // fall back for older report files
  const cells = [
    [s.policies_analyzed, 'Policies Analyzed', ''],
    [s.obligations_extracted, 'Obligations Extracted', ''],
    [rel.CONFLICT || 0, 'Conflicts', 'conflict'],
    [rel.REDUNDANT || 0, 'Redundancies', 'redundant'],
    [rel.COMPLEMENTARY || 0, 'Complementary', 'complementary'],
    [s.policies_stale_or_critical, 'Policies Stale / Critical', 'stale'],
  ];
  document.getElementById('stat-strip').innerHTML = cells.map(([val, label, cls]) => `
    <div class="stat">
      <div class="stat-value ${cls}">${val}</div>
      <div class="stat-label">${label}</div>
    </div>
  `).join('');

  // Tab badges reflect the ACTUAL number of cards rendered in each tab
  // (post-dedup), not the raw pre-dedup relationship count -- otherwise the
  // badge can show a number higher than what's visibly on screen.
  document.getElementById('count-conflicts').textContent = (report.top_conflicts || []).length;
  document.getElementById('count-redundant').textContent =
    (report.top_redundancies || []).length + (report.top_complementary || []).length;
  document.getElementById('count-staleness').textContent = s.policies_stale_or_critical;
}

/* ---------------- Redline / conflict thread cards ---------------- */
function threadCard(d) {
  const verdict = d.relationship;
  return `
    <div class="thread-card">
      <div class="clause">
        <div class="clause-tag"><b>${escapeHtml(d.policy_a)}</b> &middot; &sect;${escapeHtml(d.section_a)}</div>
        <div class="clause-text">&ldquo;${escapeHtml(d.text_a)}&rdquo;</div>
        <div class="clause-scope">obligation <span>${escapeHtml((d.pair_id||'').split('__')[0] || '')}</span></div>
      </div>
      <div class="thread-connector">
        ${connectorSvg(verdict)}
        <div class="stamp ${verdict}">${verdict}</div>
      </div>
      <div class="clause">
        <div class="clause-tag"><b>${escapeHtml(d.policy_b)}</b> &middot; &sect;${escapeHtml(d.section_b)}</div>
        <div class="clause-text">&ldquo;${escapeHtml(d.text_b)}&rdquo;</div>
        <div class="clause-scope">topic <span>${escapeHtml(d.topic)}</span></div>
      </div>
      <div class="thread-explanation">
        <div class="quill">&#10078;</div>
        <div style="flex:1">
          <div>${escapeHtml(d.explanation)}</div>
          <div class="controls">${(d.controls || []).map(c => `<span class="control-chip">${escapeHtml(c)}</span>`).join('')}</div>
        </div>
        <div class="confidence-tag">confidence ${Math.round((d.confidence || 0) * 100)}%</div>
      </div>
    </div>
  `;
}

function connectorSvg(verdict) {
  const color = verdict === 'CONFLICT' ? '#b3261e' : verdict === 'REDUNDANT' ? '#b8923f' : '#2f6f62';
  return `
    <svg viewBox="0 0 64 140" preserveAspectRatio="none" style="position:absolute;inset:0;">
      <line x1="0" y1="70" x2="64" y2="70" stroke="${color}" stroke-width="1.5" stroke-dasharray="5 4" opacity="0.65"/>
    </svg>
  `;
}

function renderConflicts(report) {
  const items = (report.top_conflicts && report.top_conflicts.length)
    ? report.top_conflicts
    : [];
  const el = document.getElementById('conflict-list');
  if (!items.length) {
    el.innerHTML = '<div class="empty-state">No unreconciled conflicts detected.</div>';
    return;
  }
  el.innerHTML = items.map(threadCard).join('');
}

function renderRedundant(report) {
  const redundant = report.top_redundancies || [];
  const complementary = report.top_complementary || [];
  const items = [...redundant, ...complementary].sort((a, b) => b.confidence - a.confidence);
  const el = document.getElementById('redundant-list');
  if (!items.length) {
    el.innerHTML = '<div class="empty-state">No redundant or complementary relationships detected.</div>';
    return;
  }
  el.innerHTML = items.map(threadCard).join('');
}

/* ---------------- Staleness table ---------------- */
function renderStaleness(rows) {
  const tbody = document.getElementById('staleness-tbody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No staleness data.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td class="policy-title-cell">${escapeHtml(r.policy_title)}<span class="team mono">${escapeHtml(r.policy_id)}</span></td>
      <td class="mono">${escapeHtml(r.last_reviewed)}</td>
      <td class="mono">${r.months_since_review}</td>
      <td><span class="badge ${r.review_status}">${r.review_status}</span></td>
      <td>${(r.deprecated_references || []).map(ref => `<span class="ref-chip" title="${escapeHtml(ref.reason)}">${escapeHtml(ref.reference)}</span>`).join('') || '<span class="mono">—</span>'}</td>
      <td class="mono">${r.staleness_score}</td>
    </tr>
  `).join('');
}

/* ---------------- Health table ---------------- */
function renderHealth(rows) {
  const tbody = document.getElementById('health-tbody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No health data.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const cls = r.health_score >= 70 ? 'health-good' : r.health_score >= 40 ? 'health-mid' : 'health-bad';
    return `
    <tr>
      <td class="policy-title-cell">${escapeHtml(r.title)}<span class="team mono">${escapeHtml(r.policy_id)}</span></td>
      <td class="mono">${escapeHtml(r.team || '—')}</td>
      <td class="mono">${r.conflict_count}</td>
      <td class="mono">${r.redundant_count}</td>
      <td><span class="badge ${r.review_status}">${r.review_status}</span></td>
      <td>
        <div style="display:flex;align-items:center;gap:10px;">
          <div class="bar-track"><div class="bar-fill ${cls}" style="width:${r.health_score}%"></div></div>
          <span class="mono">${r.health_score}</span>
        </div>
      </td>
    </tr>`;
  }).join('');
}

/* ---------------- Tabs ---------------- */
function wireTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.view;
      document.querySelectorAll('.view').forEach(v => v.hidden = true);
      document.getElementById('view-' + target).hidden = false;
      if (target === 'graph') setTimeout(resizeGraph, 30);
    });
  });
}

/* ---------------- Table sorting ---------------- */
function wireSorting() {
  document.querySelectorAll('.data-table th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const table = th.closest('table');
      const key = th.dataset.sort;
      const dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
      table.querySelectorAll('th').forEach(h => delete h.dataset.dir);
      th.dataset.dir = dir;

      const rows = table.id === 'staleness-table' ? state.staleness : state.policyScores;
      const sorted = [...rows].sort((a, b) => {
        let av = a[key], bv = b[key];
        if (typeof av === 'string') { av = av.toLowerCase(); bv = (bv || '').toLowerCase(); }
        if (av < bv) return dir === 'asc' ? -1 : 1;
        if (av > bv) return dir === 'asc' ? 1 : -1;
        return 0;
      });
      if (table.id === 'staleness-table') renderStaleness(sorted);
      else renderHealth(sorted);
    });
  });
}

/* ---------------- Graph (D3 force layout) ---------------- */
let simulation = null;

function renderGraph(graphData) {
  if (!graphData || !graphData.nodes || !graphData.nodes.length) {
    document.getElementById('graph-svg').outerHTML = '<div class="empty-state">No graph data.</div>';
    return;
  }
  const svg = d3.select('#graph-svg');
  const wrap = document.querySelector('.graph-wrap');
  const width = wrap.clientWidth, height = wrap.clientHeight;
  svg.attr('viewBox', [0, 0, width, height]);

  const nodes = graphData.nodes.map(d => ({ ...d }));
  const edgesRaw = graphData.edges || graphData.links || [];
  const links = edgesRaw.map(d => ({ ...d }));

  const color = { CONFLICT: '#e2645c', REDUNDANT: '#d8b567', COMPLEMENTARY: '#5fa393' };

  const g = svg.append('g');

  svg.call(d3.zoom().scaleExtent([0.3, 3]).on('zoom', (event) => {
    g.attr('transform', event.transform);
  }));

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(90).strength(0.5))
    .force('charge', d3.forceManyBody().strength(-140))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide(22));

  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', d => color[d.relationship] || '#666')
    .attr('stroke-width', d => 1 + (d.confidence || 0.5) * 2)
    .attr('stroke-opacity', 0.7);

  const tooltip = document.getElementById('graph-tooltip');

  link.on('mouseover', (event, d) => {
    tooltip.style.opacity = 1;
    tooltip.innerHTML = `<div class="t-tag">${d.relationship} &middot; ${Math.round((d.confidence||0)*100)}%</div>${escapeHtml(d.explanation || '')}`;
  }).on('mousemove', (event) => {
    positionTooltip(event, tooltip);
  }).on('mouseout', () => { tooltip.style.opacity = 0; });

  const topicColor = d3.scaleOrdinal(d3.schemeSet2);

  const node = g.append('g')
    .selectAll('circle')
    .data(nodes)
    .join('circle')
    .attr('r', 7)
    .attr('fill', d => topicColor(d.topic))
    .attr('stroke', '#12161d')
    .attr('stroke-width', 1.5)
    .call(drag(simulation));

  node.on('mouseover', (event, d) => {
    tooltip.style.opacity = 1;
    tooltip.innerHTML = `<div class="t-tag">${escapeHtml(d.policy_id)} &sect;${escapeHtml(d.section)} &middot; ${escapeHtml(d.topic)}</div>${escapeHtml(d.text)}`;
  }).on('mousemove', (event) => {
    positionTooltip(event, tooltip);
  }).on('mouseout', () => { tooltip.style.opacity = 0; });

  const label = g.append('g')
    .selectAll('text')
    .data(nodes)
    .join('text')
    .text(d => d.policy_id)
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-size', 8)
    .attr('fill', '#b9b09a')
    .attr('dx', 10)
    .attr('dy', 3);

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('cx', d => d.x).attr('cy', d => d.y);
    label.attr('x', d => d.x).attr('y', d => d.y);
  });
}

function positionTooltip(event, tooltip) {
  const wrap = document.querySelector('.graph-wrap').getBoundingClientRect();
  tooltip.style.left = (event.clientX - wrap.left + 14) + 'px';
  tooltip.style.top = (event.clientY - wrap.top + 14) + 'px';
}

function drag(sim) {
  function dragstarted(event, d) {
    if (!event.active) sim.alphaTarget(0.3).restart();
    d.fx = d.x; d.fy = d.y;
  }
  function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
  function dragended(event, d) {
    if (!event.active) sim.alphaTarget(0);
    d.fx = null; d.fy = null;
  }
  return d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended);
}

function resizeGraph() {
  if (state.graph) renderGraph(state.graph);
}

/* ---------------- Utils ---------------- */
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

boot();
