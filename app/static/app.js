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
  csvExport,
  download,
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
let planSynthetic = false;
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
  planSynthetic = false;
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

const planner = el("section", "", "panel");
planner.id = "roadmap-planner";
planner.append(
  el("h2", "Scenario roadmap planner"),
  el(
    "p",
    "Propose work, owners and evidence commitments. Projected scores assume delivery; this is a greedy scenario, not verification or ROI.",
  ),
);
const budgetLabel = el("label", "Effort budget (use consistent units)"),
  budgetInput = el("input");
budgetInput.id = "plan-budget";
budgetInput.type = "number";
budgetInput.min = 0;
budgetInput.max = 1000000;
budgetInput.value = 10;
budgetLabel.htmlFor = budgetInput.id;
const taskRows = el("div"),
  addTask = el("button", "Add proposed task"),
  sampleTasks = el("button", "Load synthetic task scenario"),
  runPlan = el("button", "Build roadmap");
addTask.id = "plan-add";
sampleTasks.id = "plan-example";
runPlan.id = "plan-run";
planner.append(
  budgetLabel,
  budgetInput,
  taskRows,
  addTask,
  sampleTasks,
  runPlan,
);
document.querySelector(".input-panel").append(planner);
let proposed = [];
function renderTasks() {
  replace(taskRows);
  proposed.forEach((task, index) => {
    const row = el("fieldset");
    row.append(el("legend", `Task ${index + 1}`));
    for (const [key, label, type] of [
      ["id", "Unique ID", "text"],
      ["dimension", "Dimension", "select"],
      ["target_score", "Target maturity / 5", "number"],
      ["evidence_commitment", "Evidence to deliver", "text"],
      ["effort", "Effort units", "number"],
      ["owner", "Accountable owner", "text"],
      ["prerequisites", "Prerequisite task IDs (comma-separated)", "text"],
    ]) {
      const l = el("label", label),
        c = el(type === "select" ? "select" : "input");
      c.id = `plan-${index}-${key}`;
      l.htmlFor = c.id;
      if (type === "select")
        dimensions.forEach(([k]) => {
          const o = el("option", k);
          o.value = k;
          c.append(o);
        });
      else c.type = type;
      if (type === "number") {
        c.min = key === "effort" ? 0.000001 : 0;
        c.max = key === "effort" ? 1000000 : 5;
        c.step = "any";
      }
      c.value = key === "prerequisites" ? task[key].join(", ") : task[key];
      c.oninput = () => {
        task[key] =
          key === "prerequisites"
            ? c.value
                .split(",")
                .map((v) => v.trim())
                .filter(Boolean)
            : type === "number"
              ? Number(c.value)
              : c.value;
        dirty();
      };
      row.append(l, c);
    }
    const remove = el("button", "Remove task");
    remove.onclick = () => {
      proposed.splice(index, 1);
      dirty();
      renderTasks();
    };
    row.append(remove);
    taskRows.append(row);
  });
}
addTask.onclick = () => {
  if (proposed.length >= 30) {
    status("Maximum 30 proposed tasks.", true);
    return;
  }
  proposed.push({
    id: `task-${proposed.length + 1}`,
    dimension: "data",
    target_score: 3,
    evidence_commitment: "",
    effort: 1,
    owner: "",
    prerequisites: [],
  });
  dirty();
  renderTasks();
};
sampleTasks.onclick = () => {
  dirty();
  proposed = [
    {
      id: "catalog",
      dimension: "data",
      target_score: 4,
      evidence_commitment:
        "Synthetic: approved catalog and data quality checks",
      effort: 4,
      owner: "Synthetic data lead",
      prerequisites: [],
    },
    {
      id: "review",
      dimension: "governance",
      target_score: 4,
      evidence_commitment: "Synthetic: risk review log",
      effort: 3,
      owner: "Synthetic risk lead",
      prerequisites: ["catalog"],
    },
    {
      id: "training",
      dimension: "people",
      target_score: 4,
      evidence_commitment: "Synthetic: assessed training",
      effort: 2,
      owner: "Synthetic team lead",
      prerequisites: [],
    },
  ];
  budgetInput.value = 7;
  planSynthetic = true;
  renderTasks();
  status(
    "Synthetic proposed tasks loaded. The questionnaire remains your current input; exported assessment provenance stays unchanged.",
  );
};
budgetInput.oninput = dirty;
runPlan.onclick = () =>
  action(async () => {
    report = null;
    const input = {
        assessment: payload(),
        tasks: proposed.map((t) => ({
          ...t,
          prerequisites: [...t.prerequisites],
        })),
        effort_budget: Number(budgetInput.value),
      },
      generation = getRevision(),
      result = await api("/plan", input);
    assertCurrent(generation);
    report = newReport(
      "AI Readiness Auditor roadmap",
      input,
      result,
      synthetic && planSynthetic,
    );
    replace(
      $("results"),
      metrics([
        ["Baseline / 100", result.baseline_score],
        ["Projected / 100", result.projected_score],
        ["Weighted gain", result.score_delta],
        ["Effort used", result.effort_used],
      ]),
      el("p", result.method, "notice"),
      el("h3", "Selected tasks in execution order"),
      table(
        [
          "Order",
          "ID",
          "Owner",
          "Dimension",
          "Before → target",
          "Effort",
          "Marginal points",
          "Points / effort",
        ],
        result.selected.map((t) => [
          t.selection_order,
          t.id,
          t.owner,
          t.dimension,
          `${t.effective_before} → ${t.effective_after}`,
          t.effort,
          t.marginal_weighted_gain,
          t.gain_per_effort,
        ]),
      ),
      el("h3", "Unscheduled work"),
      table(
        ["Task", "Reason", "Unselected prerequisites"],
        result.unscheduled.map((t) => [
          t.id,
          t.reason,
          t.unselected_prerequisites.join(", "),
        ]),
      ),
    );
    const save = el("button", "Export plan CSV"),
      configuration = el("button", "Export scenario JSON");
    save.onclick = () =>
      download(
        "readiness-roadmap.csv",
        csvExport(
          [
            "selection_order",
            "id",
            "owner",
            "dimension",
            "target_score",
            "evidence_commitment",
            "effort",
            "marginal_weighted_gain",
            "gain_per_effort",
          ],
          result.selected,
        ),
        "text/csv",
      );
    configuration.onclick = () => download("readiness-scenario.json", input);
    $("results").append(save, configuration);
    $("technical").textContent = JSON.stringify(result, null, 2);
    $("export-report").disabled = false;
    $("print").disabled = false;
  });
