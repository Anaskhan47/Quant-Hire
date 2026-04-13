// ===== CONFIG =====
const API_BASE_URL = window.API_BASE_URL || "http://127.0.0.1:8000";

// ===== LOADING STAGES =====
const LOADING_STAGES = [
  "Parsing resume structure...",
  "Running NLP skill extraction...",
  "Computing TF-IDF vectors...",
  "Generating semantic embeddings...",
  "Calculating feature scores...",
  "Running ML scoring engine...",
  "Prompting AI recruiter...",
  "Compiling analysis report..."
];

let stageInterval;

function startLoadingStages() {
  let i = 0;
  document.getElementById('loading-stage').textContent = LOADING_STAGES[0];
  stageInterval = setInterval(() => {
    i = (i + 1) % LOADING_STAGES.length;
    document.getElementById('loading-stage').textContent = LOADING_STAGES[i];
  }, 1800);
}

function stopLoadingStages() {
  clearInterval(stageInterval);
}

// ===== ANIMATIONS =====
function animateValue(el, target, suffix = '') {
  let current = 0;
  const t = Math.round(target);
  const step = Math.ceil(t / 40) || 1;
  const timer = setInterval(() => {
    current = Math.min(current + step, t);
    el.textContent = current + suffix;
    if (current >= t) clearInterval(timer);
  }, 25);
}

function animateBar(barId, pct) {
  setTimeout(() => {
    document.getElementById(barId).style.width = Math.min(100, Math.max(0, pct)) + '%';
  }, 200);
}

// ===== MAIN ANALYSIS FUNCTION =====
async function runAnalysis() {
  const jd = document.getElementById('jd-input').value.trim();
  const fileInput = document.getElementById('resume-file');
  const selectedFile = fileInput?.files && fileInput.files[0] ? fileInput.files[0] : null;

  let resume = document.getElementById('resume-input').value.trim();

  if (!jd) {
    alert('Please paste the job description.');
    return;
  }
  if (!resume && !selectedFile) {
    alert('Please provide a resume (paste or upload).');
    return;
  }

  const btn = document.getElementById('analyze-btn');
  btn.disabled = true;
  document.getElementById('error-card').classList.remove('visible');
  document.getElementById('loading').classList.add('active');
  startLoadingStages();

  try {
    const response = await fetch(`${API_BASE_URL}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume, job_description: jd })
    });

    const data = await response.json();
    stopLoadingStages();
    document.getElementById('loading').classList.remove('active');

    if (!response.ok) {
      const msg = data?.detail?.message || data?.detail || data?.message || "API error";
      throw new Error(msg);
    }

    renderResults(data);
    showView('results');

  } catch (err) {
    stopLoadingStages();
    document.getElementById('loading').classList.remove('active');
    btn.disabled = false;
    const errEl = document.getElementById('error-card');
    errEl.textContent = '⚠️ Analysis failed: ' + err.message;
    errEl.classList.add('visible');
  }
}

// ===== VIEW MANAGEMENT =====
function showView(viewId) {
  // Deactivate all views
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  // Activate target view
  const target = document.getElementById(viewId);
  if (target) {
    target.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function showInputView() {
  showView('input-view');
}

function resetAll() {
  // Clear any existing errors
  document.getElementById('error-card').classList.remove('visible');
  
  // Reset buttons
  const btn = document.getElementById('analyze-btn');
  if (btn) btn.disabled = false;
  
  // Return to landing
  showView('landing-view');

  // Clear inputs for fresh start
  document.getElementById('resume-input').value = '';
  document.getElementById('jd-input').value = '';
  document.getElementById('resume-file').value = '';
  document.getElementById('jd-file').value = '';
}

// ===== FILE UPLOADING & EXTRACTION =====
async function handleFileUpload(fileId, targetId) {
  const input = document.getElementById(fileId);
  const file = input.files && input.files[0];
  if (!file) return;

  const target = document.getElementById(targetId);
  target.placeholder = "⚡ Extracting text from document... please wait.";
  target.value = "";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE_URL}/extract`, {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Extraction failed.");

    target.value = data.text;
    target.scrollTop = 0;
  } catch (err) {
    alert("⚠️ Failed to parse file: " + err.message);
    target.placeholder = "Paste content here instead...";
  }
}

// ===== RENDER RESULTS =====
function renderResults(d) {
  console.log("Analysis Integrated Output:", d);

  // 🚨 FIX: Mapping Production Backend Keys to Orange UI
  const shortlist_prob = d.shortlist_probability || 0;
  const match_score = d.shortlist_probability || 0; // Sync match score to prob for UI consistency
  const skill_match = d.skill_match || 0;
  const match_label = d.required_match || 0;

  const missing = d.missing_skills || [];
  const matched = d.matched_skills || [];

  // Verdict Rendering
  const icon = shortlist_prob >= 75 ? '🚀' : shortlist_prob >= 60 ? '🎯' : shortlist_prob >= 40 ? '⚡' : '⚠️';
  document.getElementById('verdict-icon').textContent = icon;
  document.getElementById('verdict-text').textContent = d.verdict || 'Match Evaluated';

  // Core Scores
  animateValue(document.getElementById('score-match'), shortlist_prob, '%');
  animateValue(document.getElementById('score-skill'), skill_match, '%');
  animateValue(document.getElementById('score-shortlist'), shortlist_prob, '%');

  animateBar('bar-match', shortlist_prob);
  animateBar('bar-skill', skill_match);
  animateBar('bar-shortlist', shortlist_prob);

  document.getElementById('score-match-sub').textContent = shortlist_prob >= 75 ? 'Strong Fit' : shortlist_prob >= 40 ? 'Qualified' : 'Weak Fit';

  // Tags Visualization
  const matchedEl = document.getElementById('matched-skills');
  matchedEl.innerHTML = matched.map(s => `<span class="tag positive">${s.toUpperCase()}</span>`).join('') || '<span class="tag neutral">None</span>';

  const missingEl = document.getElementById('missing-skills');
  missingEl.innerHTML = missing.map(s => `<span class="tag negative">${s.toUpperCase()}</span>`).join('') || '<span class="tag positive">All Requirements Met</span>';

  // Feature Breakdown Mapping
  const fbEl = document.getElementById('feature-breakdown');
  const feats = d.feature_trace || {};
  fbEl.innerHTML = '<h4 style="font-size: 11px; opacity: 0.4; letter-spacing: 2px; margin-bottom: 20px;">FEATURE TRACE</h4>';
  
  const featDefs = [
    { key: 'keyword_alignment', label: 'Keyword Alignment', cls: 'f1' },
    { key: 'semantic_match', label: 'Semantic Match', cls: 'f2' },
    { key: 'experience_fit', label: 'Experience Fit', cls: 'f3' }
  ];

  featDefs.forEach(f => {
    const val = feats[f.key] || 0;
    fbEl.innerHTML += `
      <div class="feature-row">
        <div class="feature-label-row">
          <span class="feature-name">${f.label}</span>
          <span class="feature-pct">${val}%</span>
        </div>
        <div class="feat-bar"><div class="feat-bar-fill ${f.cls}" style="width:${val}%"></div></div>
      </div>`;
  });

  // AI Narrative
  const baseAnalysis = (d.llm_insights || 'N/A').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
  const roadmap = (d.improvement_plan || '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
  document.getElementById('llm-analysis').innerHTML = `
    <div class="analysis-section">${baseAnalysis}</div>
    <div class="roadmap-section" style="margin-top:20px; padding-top:20px; border-top:1px solid rgba(255,255,255,0.1)">
      <h4 style="color:var(--teal); margin-bottom:10px">🚀 EVOLUTION ROADMAP</h4>
      ${roadmap}
    </div>
  `;

  document.getElementById('experience-assessment').innerHTML = `
    <span style="font-family:var(--font-mono); font-size:11px; opacity:0.6; display:block; margin-bottom:4px">TRACE_ID</span>
    <span style="font-family:var(--font-heading); font-weight:700; color:var(--accent)">${(d.request_id || "PROD-GEN-000").substring(0,12)}</span>
  `;

  const btn = document.getElementById('analyze-btn');
  btn.disabled = false;
}
