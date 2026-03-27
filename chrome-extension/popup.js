// Wait for DOM before doing anything
document.addEventListener("DOMContentLoaded", init);

function init() {
  const analyzeBtn = document.getElementById("analyzeBtn");
  const statusBadge = document.getElementById("statusBadge");
  const statusText = statusBadge ? statusBadge.querySelector(".status-text") : null;
  const resultsDiv = document.getElementById("results");
  const bestPickDiv = document.getElementById("bestPick");
  const cardsDiv = document.getElementById("cards");
  const errorBox = document.getElementById("errorBox");
  const drawer = document.getElementById("drawer");
  const drawerContent = document.getElementById("drawerContent");
  const drawerTitle = document.getElementById("drawerTitle");
  const drawerClose = document.getElementById("drawerClose");
  const overlay = document.getElementById("overlay");
  const readinessAlert = document.getElementById("readinessAlert");
  const retryBtn = document.getElementById("retryBtn");

  let analysisData = null;
  let apiUrl = "http://localhost:8000";
  let isReady = false;
  let cardIdx = 0;

  // ---- Config ----
  function loadConfig() {
    return new Promise((resolve) => {
      chrome.storage.sync.get({ apiUrl: "http://localhost:8000" }, (data) => {
        apiUrl = data.apiUrl;
        resolve();
      });
    });
  }

  // ---- Drawer ----
  function openDrawer(data) {
    if (!drawerTitle || !drawerContent || !drawer || !overlay) return;
    drawerTitle.textContent = data.filename;
    drawerContent.innerHTML = buildDrawerHTML(data);
    drawer.classList.add("open");
    overlay.classList.add("open");
    setTimeout(() => {
      drawerContent.querySelectorAll(".bar-fill").forEach(el => {
        el.style.width = el.dataset.width;
      });
    }, 50);
  }
  function closeDrawer() {
    if (drawer) drawer.classList.remove("open");
    if (overlay) overlay.classList.remove("open");
  }
  if (drawerClose) drawerClose.addEventListener("click", closeDrawer);
  if (overlay) overlay.addEventListener("click", closeDrawer);

  // ---- Readiness ----
  async function checkReadiness() {
    if (statusText) statusText.textContent = "Connecting...";
    if (statusBadge) statusBadge.className = "status-pill";
    if (retryBtn) retryBtn.disabled = true;

    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 4000);
      const res = await fetch(apiUrl + "/health", { signal: ctrl.signal });
      clearTimeout(t);
      if (!res.ok) throw new Error("bad");
      const data = await res.json();

      isReady = true;
      if (statusText) statusText.textContent = data.resumes_loaded + " resume" + (data.resumes_loaded !== 1 ? "s" : "") + " loaded";
      if (statusBadge) statusBadge.className = "status-pill connected";
      if (analyzeBtn) analyzeBtn.disabled = false;

      if (readinessAlert) {
        readinessAlert.className = "readiness-alert connected";
        readinessAlert.style.display = "flex";
        readinessAlert.querySelector(".alert-icon").textContent = "✅";
        readinessAlert.querySelector(".alert-title").textContent = "Backend Connected";
        readinessAlert.querySelector(".alert-msg").innerHTML = "Ready to analyze. <strong>" + data.resumes_loaded + "</strong> resume" + (data.resumes_loaded !== 1 ? "s" : "") + " indexed.";
        if (retryBtn) retryBtn.style.display = "none";
        setTimeout(function() { readinessAlert.style.display = "none"; }, 3000);
      }
    } catch (e) {
      isReady = false;
      if (statusText) statusText.textContent = "Offline";
      if (statusBadge) statusBadge.className = "status-pill error";
      if (analyzeBtn) analyzeBtn.disabled = true;

      if (readinessAlert) {
        readinessAlert.className = "readiness-alert";
        readinessAlert.style.display = "flex";
        readinessAlert.querySelector(".alert-icon").textContent = "⚠️";
        readinessAlert.querySelector(".alert-title").textContent = "Backend Not Reachable";
        readinessAlert.querySelector(".alert-msg").innerHTML = "Cannot connect to <code>" + apiUrl + "</code>.<br>Start the server: <code>cd backend && python main.py</code>";
        if (retryBtn) { retryBtn.style.display = ""; retryBtn.disabled = false; }
      }
    }
  }

  if (retryBtn) retryBtn.addEventListener("click", checkReadiness);

  // Start
  loadConfig().then(function() { checkReadiness(); });

  // Re-check on config change
  chrome.storage.onChanged.addListener(function(changes) {
    if (changes.apiUrl) { apiUrl = changes.apiUrl.newValue; checkReadiness(); }
  });

  // ---- Smart JD extraction (runs inside the active tab) ----
  function injectedExtractor() {
    var url = window.location.href.toLowerCase();
    var body = document.body.innerText || "";

    // ═══════════════════════════════════════════════
    // LINKEDIN
    // ═══════════════════════════════════════════════
    if (url.includes("linkedin.com")) {

      // Strategy 1: CSS selectors for the JD container
      var liSelectors = [
        ".jobs-description__content",
        ".jobs-description-content__text",
        ".jobs-box__html-content",
        ".jobs-description",
        'article[class*="jobs-description"]',
        '[class*="description__text"]',
        '#job-details',
      ];
      for (var i = 0; i < liSelectors.length; i++) {
        var el = document.querySelector(liSelectors[i]);
        if (el && el.innerText && el.innerText.trim().length > 100) {
          return el.innerText.trim();
        }
      }

      // Strategy 2: Text-based extraction — find "About the job" marker
      var aboutIdx = body.indexOf("About the job");
      if (aboutIdx === -1) aboutIdx = body.indexOf("About this job");
      if (aboutIdx !== -1) {
        var jd = body.substring(aboutIdx + "About the job".length);

        // Cut at known end markers
        var endMarkers = [
          "See how you compare",
          "Applicants for this job",
          "About the company",
          "Similar jobs",
          "People also viewed",
          "People you can reach out",
          "Show more Premium",
          "Exclusive Job Seeker",
          "Powered by Bing",
        ];
        for (var m = 0; m < endMarkers.length; m++) {
          var endIdx = jd.indexOf(endMarkers[m]);
          if (endIdx > 50) {
            jd = jd.substring(0, endIdx);
            break;
          }
        }

        // Also try to grab the job title from the page
        var titleEl = document.querySelector(
          'h1, .job-details-jobs-unified-top-card__job-title, ' +
          '.jobs-unified-top-card__job-title, ' +
          '[class*="top-card__title"]'
        );
        var title = titleEl ? titleEl.innerText.trim() : "";
        if (title && jd.trim().length > 100) {
          return title + "\n\n" + jd.trim();
        }
        if (jd.trim().length > 100) return jd.trim();
      }

      // Strategy 3: grab the right panel content (job detail pane)
      var rightPanel = document.querySelector(
        '.jobs-search__job-details, ' +
        '.job-view-layout, ' +
        '[class*="job-details"]'
      );
      if (rightPanel && rightPanel.innerText.trim().length > 200) {
        return rightPanel.innerText.trim();
      }
    }

    // ═══════════════════════════════════════════════
    // INDEED
    // ═══════════════════════════════════════════════
    if (url.includes("indeed.com")) {
      var indeedSel = ["#jobDescriptionText", ".jobsearch-jobDescriptionText"];
      for (var j = 0; j < indeedSel.length; j++) {
        var iel = document.querySelector(indeedSel[j]);
        if (iel && iel.innerText.trim().length > 100) return iel.innerText.trim();
      }
    }

    // ═══════════════════════════════════════════════
    // GLASSDOOR
    // ═══════════════════════════════════════════════
    if (url.includes("glassdoor.com")) {
      var gdSel = ['[class*="jobDescription"]', ".desc"];
      for (var g = 0; g < gdSel.length; g++) {
        var gel = document.querySelector(gdSel[g]);
        if (gel && gel.innerText.trim().length > 100) return gel.innerText.trim();
      }
    }

    // ═══════════════════════════════════════════════
    // NAUKRI
    // ═══════════════════════════════════════════════
    if (url.includes("naukri.com")) {
      var nkSel = [".styles_JDC__dang-inner-html__h0K4t", ".job-desc", ".dang-inner-html"];
      for (var n = 0; n < nkSel.length; n++) {
        var nel = document.querySelector(nkSel[n]);
        if (nel && nel.innerText.trim().length > 100) return nel.innerText.trim();
      }
    }

    // ═══════════════════════════════════════════════
    // LEVER / GREENHOUSE / WORKDAY
    // ═══════════════════════════════════════════════
    if (url.includes("lever.co")) {
      var lel = document.querySelector('[class*="posting-"]');
      if (lel && lel.innerText.trim().length > 100) return lel.innerText.trim();
    }
    if (url.includes("greenhouse.io")) {
      var ghel = document.querySelector("#content");
      if (ghel && ghel.innerText.trim().length > 100) return ghel.innerText.trim();
    }
    if (url.includes("myworkdayjobs.com") || url.includes("workday.com")) {
      var wdel = document.querySelector('[data-automation-id="jobPostingDescription"]');
      if (wdel && wdel.innerText.trim().length > 100) return wdel.innerText.trim();
    }

    // ═══════════════════════════════════════════════
    // GENERIC FALLBACK
    // ═══════════════════════════════════════════════
    var genericSel = [
      '[class*="job-description"]', '[class*="jobDescription"]',
      '[id*="job-description"]', '[id*="jobDescription"]',
      "article", "main", '[role="main"]',
    ];
    for (var k = 0; k < genericSel.length; k++) {
      var kel = document.querySelector(genericSel[k]);
      if (kel && kel.innerText.trim().length > 100) return kel.innerText.trim();
    }

    return body;
  }

  async function extractPageText() {
    var tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    var tab = tabs[0];
    var results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: injectedExtractor,
    });
    return results[0].result;
  }

  // ---- Helpers ----
  function sc(pct) { return pct >= 65 ? "high" : pct >= 40 ? "mid" : "low"; }
  function vc(v) {
    if (v.indexOf("STRONG") !== -1) return "strong-apply";
    if (v.indexOf("SKIP") !== -1) return "skip";
    if (v.indexOf("MAYBE") !== -1) return "maybe";
    return "apply";
  }

  function scoreBar(label, value, max) {
    max = max || 100;
    var pct = max === 15 ? Math.round(value / 15 * 100) : Math.round(value);
    var display = max === 15 ? value + "/15" : Math.round(value) + "%";
    var cls = sc(pct);
    return '<div class="score-bar">' +
      '<span class="bar-label">' + label + '</span>' +
      '<div class="bar-track"><div class="bar-fill ' + cls + '" style="width:0" data-width="' + pct + '%"></div></div>' +
      '<span class="bar-val ' + cls + '">' + display + '</span></div>';
  }

  // ---- Drawer HTML builder ----
  function buildDrawerHTML(r) {
    var vcls = vc(r.verdict);
    var h = "";

    h += '<div class="verdict-box vb-' + vcls + '">' +
      '<div class="verdict-label ' + vcls + '">' + r.verdict + '</div>' +
      '<div class="verdict-reason">' + r.verdict_reasoning + '</div></div>';

    h += '<div class="d-section"><div class="d-section-title"><span class="icon">📊</span> Score Breakdown</div>' +
      scoreBar("Overall", r.combined_score) +
      scoreBar("ATS Score", r.ats_score) +
      scoreBar("Keywords", r.keyword_score) +
      scoreBar("Placement", r.contextual_placement_score) +
      scoreBar("Skill Clusters", r.cluster_score) +
      scoreBar("Categories", r.category_score) +
      scoreBar("Quantification", r.quantification_score, 15) +
      scoreBar("Semantic Fit", r.semantic_score) + '</div>';

    h += '<div class="d-section"><div class="d-section-title"><span class="icon">⚖️</span> Why Apply / Why Not</div><div class="reasoning">';
    (r.strengths || []).forEach(function(s) { h += '<div class="item strength">' + s + '</div>'; });
    (r.gaps || []).forEach(function(g) { h += '<div class="item gap">' + g + '</div>'; });
    h += '</div></div>';

    if (r.skill_clusters && Object.keys(r.skill_clusters).length > 0) {
      h += '<div class="d-section"><div class="d-section-title"><span class="icon">🧩</span> Skill Clusters</div>';
      Object.entries(r.skill_clusters).forEach(function(entry) {
        var name = entry[0], data = entry[1];
        var cov = data.coverage || 0;
        var hits = (data.matched_terms || []).map(function(t) { return '<span class="chip hit">' + t + '</span>'; }).join("");
        var misses = (data.missing_terms || []).map(function(t) { return '<span class="chip miss">' + t + '</span>'; }).join("");
        h += '<div class="cluster-card"><div class="cluster-header"><span class="cluster-name">' + name + '</span><span class="cluster-pct ' + sc(cov) + '">' + cov + '%</span></div><div class="cluster-terms">' + hits + misses + '</div></div>';
      });
      h += '</div>';
    }

    if (r.skill_categories && Object.keys(r.skill_categories).length > 0) {
      h += '<div class="d-section"><div class="d-section-title"><span class="icon">📋</span> Skill Categories</div>';
      Object.entries(r.skill_categories).forEach(function(entry) {
        var cat = entry[0], info = entry[1];
        h += scoreBar(cat.replace(/_/g, " "), info.pct || 0);
        if (info.missing && info.missing.length > 0) {
          h += '<div style="font-size:10px;color:rgba(248,113,113,0.7);margin:-2px 0 6px 120px">Missing: ' + info.missing.join(", ") + '</div>';
        }
      });
      h += '</div>';
    }

    h += '<div class="d-section"><div class="d-section-title"><span class="icon">📈</span> Quantified Impact</div>' +
      '<div class="quant-grid"><div class="quant-stat"><div class="q-val">' + r.quantification_score + '</div><div class="q-lbl">Score / 15</div></div>' +
      '<div class="quant-stat"><div class="q-val">' + (r.result_verbs_count || 0) + '</div><div class="q-lbl">Action Verbs</div></div></div>';
    if (r.quantification_examples && r.quantification_examples.length > 0) {
      h += '<div class="quant-examples">' + r.quantification_examples.map(function(e) { return '<span class="q-chip">' + e + '</span>'; }).join("") + '</div>';
    } else {
      h += '<div style="margin-top:8px;font-size:11px;color:rgba(248,113,113,0.7)">No quantified metrics found.</div>';
    }
    h += '</div>';

    h += '<div class="d-section"><div class="d-section-title"><span class="icon">✅</span> Matched Keywords</div><div class="kw-pills">' +
      (r.matched_keywords_sample || []).slice(0, 20).map(function(k) { return '<span class="kw-pill matched">' + k + '</span>'; }).join("") + '</div></div>';
    h += '<div class="d-section"><div class="d-section-title"><span class="icon">❌</span> Missing Keywords</div><div class="kw-pills">' +
      (r.missing_keywords_sample || []).slice(0, 15).map(function(k) { return '<span class="kw-pill missing">' + k + '</span>'; }).join("") + '</div></div>';

    // Gap summary — why this resume doesn't fit
    if (r.gap_summary) {
      h += '<div class="d-section"><div class="d-section-title"><span class="icon">🔍</span> Why This Resume Doesn\'t Fit</div>' +
        '<div class="gap-summary-box">' + r.gap_summary + '</div></div>';
    }

    // Tailoring suggestions — shown for MAYBE / TAILOR verdicts
    if (r.tailoring_suggestions && r.tailoring_suggestions.length > 0) {
      h += '<div class="d-section tailoring-section">' +
        '<div class="d-section-title"><span class="icon">✏️</span> How to Tailor This Resume</div>' +
        '<div class="tailoring-box">';
      r.tailoring_suggestions.forEach(function(s, i) {
        h += '<div class="tailoring-item"><span class="tailoring-num">' + (i + 1) + '</span><span>' + s + '</span></div>';
      });
      h += '</div></div>';
    }

    h += '<div class="d-section"><div class="d-section-title"><span class="icon">🤖</span> AI Analysis</div><div class="ai-analysis">' + r.llm_analysis + '</div></div>';
    return h;
  }

  // ---- Render card ----
  function renderCard(r, isWinner) {
    var card = document.createElement("div");
    card.className = "resume-card" + (isWinner ? " winner" : "");
    var vcls = vc(r.verdict);
    var idx = cardIdx++;

    var reasoning = '<div class="reasoning">';
    (r.strengths || []).slice(0, 2).forEach(function(s) { reasoning += '<div class="item strength">' + s + '</div>'; });
    (r.gaps || []).slice(0, 2).forEach(function(g) { reasoning += '<div class="item gap">' + g + '</div>'; });
    reasoning += '</div>';

    // Tailoring hint on card for MAYBE verdicts
    var tailorHint = "";
    if (r.tailoring_suggestions && r.tailoring_suggestions.length > 0 && r.verdict.indexOf("MAYBE") !== -1) {
      tailorHint = '<div class="card-tailor-hint"><span class="icon">✏️</span> ' +
        r.tailoring_suggestions.length + ' tailoring suggestion' +
        (r.tailoring_suggestions.length > 1 ? 's' : '') +
        ' available — click View Full Analysis</div>';
    }

    // Gap summary hint on card for SKIP/low scores
    var gapHint = "";
    if (r.gap_summary && r.verdict.indexOf("SKIP") !== -1) {
      gapHint = '<div class="card-gap-hint"><span class="icon">🔍</span> ' + r.gap_summary.substring(0, 120) + '...</div>';
    }

    card.innerHTML =
      '<div class="card-header">' +
        '<span class="name"><span class="file-icon">📄</span>' + r.filename + '</span>' +
        '<div class="header-badges">' +
          (isWinner ? '<span class="best-tag">Best Match</span>' : '') +
          '<span class="verdict-badge ' + vcls + '">' + r.verdict + '</span>' +
        '</div></div>' +
      '<div class="score-grid">' +
        '<div class="score-cell combined"><div class="val">' + r.combined_score + '%</div><div class="lbl">Overall</div></div>' +
        '<div class="score-cell ats"><div class="val">' + r.ats_score + '%</div><div class="lbl">ATS</div></div>' +
        '<div class="score-cell kw"><div class="val">' + r.keyword_score + '%</div><div class="lbl">Keywords</div></div>' +
        '<div class="score-cell placement"><div class="val">' + r.contextual_placement_score + '%</div><div class="lbl">Placement</div></div>' +
        '<div class="score-cell cluster"><div class="val">' + r.cluster_score + '%</div><div class="lbl">Clusters</div></div>' +
        '<div class="score-cell sem"><div class="val">' + Math.round(r.semantic_score) + '</div><div class="lbl">Semantic</div></div>' +
      '</div>' +
      reasoning +
      tailorHint +
      gapHint +
      '<button class="detail-btn" data-idx="' + idx + '">View Full Analysis →</button>';

    card.querySelector(".detail-btn").addEventListener("click", function(e) {
      openDrawer(analysisData.resumes[parseInt(e.target.dataset.idx)]);
    });
    return card;
  }

  // ---- Analyze ----
  if (analyzeBtn) analyzeBtn.addEventListener("click", async function() {
    if (!isReady) { await checkReadiness(); if (!isReady) return; }

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "⏳ Analyzing...";
    cardIdx = 0;
    if (errorBox) errorBox.style.display = "none";
    if (resultsDiv) resultsDiv.style.display = "none";
    if (cardsDiv) cardsDiv.innerHTML = '<div class="loading"><div class="loading-spinner"></div>Extracting job description...</div>';
    if (resultsDiv) resultsDiv.style.display = "block";

    try {
      var pageText = await extractPageText();
      if (!pageText || pageText.trim().length < 50) {
        throw new Error("Could not extract enough text. Make sure you're on a job posting page and the description is visible.");
      }

      var jd = pageText.trim().substring(0, 5000);
      var jdLen = jd.length;
      if (cardsDiv) {
        var hint = jdLen < 200
          ? "⚠️ Only " + jdLen + " chars extracted — scroll down on the page first"
          : "📋 Extracted " + jdLen.toLocaleString() + " chars";
        cardsDiv.innerHTML = '<div class="loading"><div class="loading-spinner"></div>' + hint + '<br>Analyzing against your resumes...</div>';
      }

      var res = await fetch(apiUrl + "/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: jd }),
      });
      if (!res.ok) throw new Error("Server returned " + res.status);
      analysisData = await res.json();

      if (analysisData.best_resume && bestPickDiv) {
        var best = analysisData.resumes[0];
        var bvc = vc(best.verdict);
        bestPickDiv.innerHTML =
          '<div class="label">✅ Recommended Resume</div>' +
          '<div class="pick-name">' + analysisData.best_resume + ' <span class="verdict-badge ' + bvc + '" style="font-size:10px;vertical-align:middle">' + best.verdict + '</span></div>' +
          '<div class="pick-scores">Overall: <span>' + best.combined_score + '%</span> · ATS: <span>' + best.ats_score + '%</span> · Clusters: <span>' + best.cluster_score + '%</span> · Semantic: <span>' + Math.round(best.semantic_score) + '</span></div>';
      } else if (bestPickDiv) {
        bestPickDiv.innerHTML = '<div class="label">⚠️ No resumes loaded</div><div style="color:var(--text-secondary);font-size:12px">' + (analysisData.recommendation || "") + '</div>';
      }

      if (cardsDiv) {
        cardsDiv.innerHTML = "";
        analysisData.resumes.forEach(function(r, i) {
          cardsDiv.appendChild(renderCard(r, i === 0));
        });
      }
    } catch (err) {
      if (resultsDiv) resultsDiv.style.display = "none";
      if (errorBox) { errorBox.style.display = "block"; errorBox.textContent = err.message; }
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = "⚡ Analyze This Job Posting";
    }
  });

} // end init()
