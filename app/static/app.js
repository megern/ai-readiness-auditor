import {
  getRevision,
  assessmentFromExport,
  isStale,
  assertCurrent,
  $,
  el,
  replace,
  table,
  bars,
  metrics,
  api,
  action,
  status,
  format,
  newReport,
  setupExports,
  invalidate,
  readFile,
} from "./common.js";
const dimensions = [
  [
    "strategy",
    "Strategy",
    20,
    "Are AI use cases measurable, prioritized and owned?",
    "Named sponsor, outcome baseline, use-case backlog.",
  ],
  [
    "data",
    "Data",
    25,
    "Is relevant data usable, governed and accessible?",
    "Quality checks, access approvals, data catalog.",
  ],
  [
    "governance",
    "Governance",
    20,
    "Are privacy, risk and approval controls exercised?",
    "Risk assessments, review records, incident procedure.",
  ],
  [
    "people",
    "People",
    15,
    "Can named people deliver and maintain AI systems?",
    "Role ownership, training records, support coverage.",
  ],
  [
    "infrastructure",
    "Infrastructure",
    20,
    "Can the team reproduce, deploy and monitor a system?",
    "Deployment procedure, versioned artifacts, monitoring.",
  ],
];
const levels = [
  "0 · Not established",
  "1 · Informal / ad hoc",
  "2 · Documented",
  "3 · Implemented",
  "4 · Measured and reviewed",
  "5 · Repeatedly improved",
];
let synthetic = false,
  report = null,
  baseline = null;
for (const [key, name, weight, question, examples] of dimensions) {
  const field = el("fieldset"),
    legend = el("legend", `${name} · ${weight}% weight`),
    q = el("p", question),
    label = el("label", "Current maturity"),
    select = el("select");
  select.id = "score-" + key;
  label.htmlFor = select.id;
  levels.forEach((text, i) => {
    const o = el("option", text);
    o.value = i;
    select.append(o);
  });
  const evidence = el("textarea");
  evidence.id = "evidence-" + key;
  evidence.maxLength = 12000;
  evidence.placeholder = examples;
  const l = el("label", "Evidence descriptions (one per line)");
  l.htmlFor = evidence.id;
  field.append(
    legend,
    q,
    label,
    select,
    l,
    evidence,
    el("p", examples, "hint"),
  );
  $("questions").append(field);
}
function payload() {
  return {
    dimensions: Object.fromEntries(
      dimensions.map(([key]) => [
        key,
        {
          score: Number($("score-" + key).value),
          evidence: $("evidence-" + key)
            .value.split("\n")
            .map((x) => x.trim())
            .filter(Boolean),
        },
      ]),
    ),
  };
}
function dirty() {
  synthetic = false;
  report = null;
  $("data-origin").textContent = "Your input · changed";
  $("technical").textContent = "Inputs changed. Run again.";
  invalidate();
}
$("questions").addEventListener("input", dirty);
function load(data) {
  if (!data.dimensions || dimensions.some(([key]) => !data.dimensions[key]))
    throw new Error("Configuration must include all five dimensions.");
  for (const [key] of dimensions) {
    const d = data.dimensions[key];
    if (
      !Number.isInteger(d.score) ||
      d.score < 0 ||
      d.score > 5 ||
      !Array.isArray(d.evidence) ||
      d.evidence.length > 20 ||
      d.evidence.some((v) => typeof v !== "string")
    )
      throw new Error(
        "Use maturity levels 0–5 and at most 20 text evidence descriptions per dimension.",
      );
  }
  const importedBaseline = data.baseline
    ? assessmentFromExport(data.baseline)
    : null;
  for (const [key] of dimensions) {
    $("score-" + key).value = data.dimensions[key].score;
    $("evidence-" + key).value = data.dimensions[key].evidence.join("\n");
  }
  baseline = importedBaseline;
  $("baseline-status").textContent = baseline
    ? "Baseline restored. Run analysis to compare."
    : "No baseline loaded.";
  dirty();
}
$("example").onclick = () => {
  load({
    dimensions: Object.fromEntries(
      dimensions.map(([key], i) => [
        key,
        {
          score: [4, 3, 2, 4, 3][i],
          evidence: ["Synthetic example: documented " + key + " control"],
        },
      ]),
    ),
  });
  synthetic = true;
  $("data-origin").textContent =
    "Synthetic example · not real organizational evidence";
  status(
    "Synthetic questionnaire loaded. Replace the evidence descriptions with your own references for a real assessment.",
  );
};
const configLabel = el("label", "Import a saved questionnaire"),
  configFile = el("input");
configFile.type = "file";
configFile.accept = ".json,application/json";
configFile.id = "config-file";
configLabel.htmlFor = configFile.id;
$("questions").after(configLabel, configFile);
configFile.onchange = async () => {
  try {
    dirty();
    const generation = getRevision();
    const text = await readFile(configFile);
    assertCurrent(generation);
    if (text !== null) load(JSON.parse(text));
  } catch (e) {
    if (isStale(e)) return;
    dirty();
    status("Cannot import questionnaire: " + e.message, true);
  }
};
$("baseline-file").onchange = async () => {
  try {
    dirty();
    const generation = getRevision();
    const text = await readFile($("baseline-file"));
    assertCurrent(generation);
    if (text === null) return;
    const imported = assessmentFromExport(JSON.parse(text));
    baseline = imported;
    dirty();
    $("baseline-status").textContent =
      "Baseline loaded from assessment input. Stored totals are ignored; both scores are recomputed.";
    status(
      "Baseline imported. Run analysis to see dimension and evidence changes.",
    );
  } catch (error) {
    if (isStale(error)) return;
    status("Cannot import baseline: " + error.message, true);
  }
};
$("clear-baseline").onclick = () => {
  baseline = null;
  dirty();
  $("baseline-status").textContent = "No baseline loaded.";
};
function configuration() {
  return { ...payload(), ...(baseline ? { baseline } : {}) };
}
$("run").onclick = () =>
  action(async () => {
    report = null;
    const input = configuration(),
      generation = getRevision(),
      result = await api(
        baseline ? "/compare" : "/analyze",
        baseline ? { current: payload(), baseline } : payload(),
      );
    assertCurrent(generation);
    report = newReport("AI Readiness Auditor", input, result, synthetic);
    const results = $("results");
    replace(
      results,
      metrics([["Readiness / 100", result.score_out_of_100]]),
      el(
        "p",
        result.band.charAt(0).toUpperCase() +
          result.band.slice(1) +
          " · heuristic score band",
        "pill",
      ),
      el("h3", "Effective maturity by dimension"),
      bars(
        result.dimensions.map((d) => [d.dimension, d.effective_score]),
        5,
      ),
      el("p", result.method, "notice"),
      el("h3", "Evidence and adjusted scores"),
      table(
        ["Dimension", "Reported / 5", "Effective / 5", "Evidence"],
        result.dimensions.map((d) => [
          d.dimension,
          d.reported_score,
          d.effective_score,
          d.evidence_present ? "Description supplied" : "Missing · capped at 1",
        ]),
      ),
    );
    if (result.comparison) {
      const comparison = result.comparison;
      results.append(
        el("h3", "Change from baseline"),
        metrics([
          ["Baseline / 100", comparison.baseline_score],
          ["Score delta", comparison.total_delta],
        ]),
        table(
          [
            "Dimension",
            "Before → current effective / 5",
            "Weighted points delta",
            "Evidence added",
            "Evidence removed",
          ],
          comparison.dimensions.map((d) => [
            d.dimension,
            `${d.baseline_effective_score} → ${d.current_effective_score}`,
            d.weighted_score_delta,
            d.evidence_added.join("; ") || "None",
            d.evidence_removed.join("; ") || "None",
          ]),
        ),
        el("p", comparison.method, "notice"),
      );
    }
    results.append(el("h3", "Prioritized next actions"));
    if (!result.prioritized_actions.length)
      results.append(
        el(
          "p",
          "All dimensions scored 5. Verify your evidence independently and periodically reassess.",
        ),
      );
    else
      for (const d of result.prioritized_actions) {
        const card = el("div", "", "step");
        card.append(
          el("strong", d.dimension + " · weighted gap " + format(d.priority)),
          el("p", d.action),
          el(
            "p",
            "Suggested follow-up: name an owner, record a due date, and define the evidence that would close this gap.",
            "hint",
          ),
        );
        results.append(card);
      }
    results.append(
      el(
        "p",
        "Self-reported readiness is not a certification, compliance determination or investment decision.",
        "notice",
      ),
    );
    $("technical").textContent = JSON.stringify(result, null, 2);
    $("export-report").disabled = false;
    $("print").disabled = false;
  });
setupExports("readiness", () => report, configuration);
