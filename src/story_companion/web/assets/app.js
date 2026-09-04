"use strict";

const query = new URLSearchParams(window.location.search);
if (query.get("capture") === "results") {
  document.documentElement.classList.add("capture-results");
}

const state = {
  book: null,
  chapters: [],
  selectedChapter: 1,
  isDemo: false,
  aiEnabled: false,
  busy: false,
};

const elements = {
  runtimePill: document.querySelector("#runtime-pill"),
  runtimeLabel: document.querySelector("#runtime-label"),
  fileInput: document.querySelector("#book-file"),
  dropZone: document.querySelector("#drop-zone"),
  demoButton: document.querySelector("#demo-button"),
  heroDemoButton: document.querySelector("#hero-demo-button"),
  boundaryStep: document.querySelector("#boundary-step"),
  analysisStep: document.querySelector("#analysis-step"),
  bookSummary: document.querySelector("#book-summary"),
  boundaryLabel: document.querySelector("#boundary-label"),
  chapterRange: document.querySelector("#chapter-range"),
  chapterTrail: document.querySelector("#chapter-trail"),
  analysisHelp: document.querySelector("#analysis-help"),
  analyzeButton: document.querySelector("#analyze-button"),
  statusMessage: document.querySelector("#status-message"),
  resultsEmpty: document.querySelector("#results-empty"),
  resultsContent: document.querySelector("#results-content"),
  resultsKicker: document.querySelector("#results-kicker"),
  resultsHeading: document.querySelector("#results-heading"),
  sampleBadge: document.querySelector("#sample-badge"),
  resultStats: document.querySelector("#result-stats"),
  characterGrid: document.querySelector("#character-grid"),
};

function setRuntime(status, label) {
  elements.runtimePill.dataset.status = status;
  elements.runtimeLabel.textContent = label;
}

function setStatus(message, kind = "info") {
  elements.statusMessage.textContent = message;
  elements.statusMessage.dataset.kind = kind;
}

function setBusy(isBusy, label = "Working…") {
  state.busy = isBusy;
  elements.fileInput.disabled = isBusy;
  elements.demoButton.disabled = isBusy;
  elements.heroDemoButton.disabled = isBusy;
  elements.chapterRange.disabled = isBusy || !state.book;
  elements.analyzeButton.disabled = isBusy || !state.book;
  elements.analyzeButton.textContent = isBusy
    ? label
    : state.isDemo
      ? "Preview evidence-grounded result"
      : "Build my companion";
}

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Request failed with status ${response.status}`);
  }
  return payload;
}

async function loadRuntimeConfig() {
  try {
    const response = await fetch("/config", { headers: { Accept: "application/json" } });
    const config = await parseResponse(response);
    state.aiEnabled = config.ai_enabled;
    if (state.aiEnabled) {
      setRuntime("ready", "AI extraction ready");
    } else {
      setRuntime("preview", "Sample preview available");
    }
  } catch (_error) {
    setRuntime("error", "API unavailable");
  }
}

async function uploadBook(file, isDemo = false) {
  if (!file || !file.name.toLowerCase().endsWith(".txt")) {
    setStatus("Choose a UTF-8 .txt file.", "error");
    return false;
  }

  setBusy(true, "Reading chapters…");
  setStatus(`Reading ${file.name}…`);
  const formData = new FormData();
  formData.append("book_file", file);

  try {
    const response = await fetch("/books", { method: "POST", body: formData });
    const payload = await parseResponse(response);
    state.book = payload.book;
    state.chapters = payload.chapters;
    state.isDemo = isDemo;
    state.selectedChapter = isDemo ? Math.min(2, state.chapters.length) : 1;
    showBookSetup();
    resetResults();
    setStatus(
      `${state.chapters.length} ${state.chapters.length === 1 ? "chapter" : "chapters"} detected. Choose your reading horizon.`,
      "success",
    );
    return true;
  } catch (error) {
    setStatus(error.message, "error");
    return false;
  } finally {
    setBusy(false);
  }
}

function showBookSetup() {
  elements.boundaryStep.classList.remove("is-disabled");
  elements.analysisStep.classList.remove("is-disabled");
  elements.bookSummary.textContent = `${state.book.title} · ${state.chapters.length} detected chapters`;
  elements.chapterRange.min = "1";
  elements.chapterRange.max = String(state.chapters.length);
  elements.chapterRange.value = String(state.selectedChapter);
  elements.chapterRange.disabled = false;
  elements.analyzeButton.disabled = false;
  elements.analysisHelp.textContent = state.isDemo
    ? "This sample is precomputed and makes no model call. Its citations still pass the same provenance validator."
    : state.aiEnabled
      ? "Only the selected chapters will be sent to the configured extraction provider."
      : "Add OPENAI_API_KEY to .env for live extraction, or use the sample story for an offline preview.";
  updateBoundaryUI();
  setBusy(false);
}

function updateBoundaryUI() {
  const selected = state.chapters[state.selectedChapter - 1];
  elements.boundaryLabel.textContent = selected
    ? `Chapter ${selected.number}: ${cleanChapterTitle(selected.title)}`
    : `Chapter ${state.selectedChapter}`;

  renderChapterTrail();
}

function renderChapterTrail() {
  elements.chapterTrail.replaceChildren();
  state.chapters.forEach((chapter) => {
    const item = document.createElement("li");
    item.className = chapter.number <= state.selectedChapter ? "is-readable" : "is-locked";
    item.textContent = cleanChapterTitle(chapter.title);
    elements.chapterTrail.append(item);
  });
}

function cleanChapterTitle(title) {
  return title.replace(/^chapter\s+[\divxlcdm]+\s*[:.\-—]?\s*/i, "") || title;
}

async function loadDemo(showResults = false) {
  setBusy(true, "Opening sample…");
  setStatus("Opening the sample story…");
  try {
    const response = await fetch("/demo/the-lantern-at-brambleford.txt");
    if (!response.ok) {
      throw new Error("The sample story could not be loaded.");
    }
    const text = await response.text();
    const file = new File([text], "the-lantern-at-brambleford.txt", {
      type: "text/plain",
    });
    const uploaded = await uploadBook(file, true);
    if (!uploaded) {
      return;
    }
    document.querySelector("#workspace").scrollIntoView({ behavior: "smooth", block: "start" });
    if (showResults && state.book) {
      await runAnalysis();
    }
  } catch (error) {
    setStatus(error.message, "error");
    setBusy(false);
  }
}

async function runAnalysis() {
  if (!state.book || state.busy) {
    return;
  }

  setBusy(true, state.isDemo ? "Opening sample…" : "Finding characters…");
  setStatus(
    state.isDemo
      ? "Loading the precomputed, validator-checked sample…"
      : `Locking the book through Chapter ${state.selectedChapter}…`,
  );

  try {
    const boundaryResponse = await fetch(`/books/${state.book.id}/spoiler-boundary`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chapter_number: state.selectedChapter }),
    });
    await parseResponse(boundaryResponse);

    let result;
    if (state.isDemo) {
      const sampleResponse = await fetch("/demo/example-result.json");
      result = await parseResponse(sampleResponse);
    } else {
      if (!state.aiEnabled) {
        throw new Error(
          "Live extraction is not configured. Add OPENAI_API_KEY to .env or open the sample story.",
        );
      }
      const extractionResponse = await fetch(`/books/${state.book.id}/characters`, {
        method: "POST",
        headers: { Accept: "application/json" },
      });
      result = await parseResponse(extractionResponse);
    }

    renderResults(result, state.isDemo);
    setStatus(
      `${result.characters.length} character profiles built through Chapter ${state.selectedChapter}.`,
      "success",
    );
    elements.resultsContent.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function resetResults() {
  elements.resultsEmpty.hidden = false;
  elements.resultsContent.hidden = true;
  elements.characterGrid.replaceChildren();
  elements.resultStats.replaceChildren();
}

function renderResults(result, isSample) {
  elements.resultsEmpty.hidden = true;
  elements.resultsContent.hidden = false;
  elements.sampleBadge.hidden = !isSample;
  elements.resultsKicker.textContent = `Safe through Chapter ${state.selectedChapter}`;
  elements.resultsHeading.textContent = `${state.book.title}: the cast so far`;

  const claims = result.characters.flatMap((character) => character.claims);
  const evidenceCount = claims.reduce((total, claim) => total + claim.evidence.length, 0);
  elements.resultStats.replaceChildren(
    createStat(result.characters.length, "Characters"),
    createStat(claims.length, "Grounded claims"),
    createStat(evidenceCount, "Source passages"),
  );

  elements.characterGrid.replaceChildren();
  result.characters.forEach((character) => {
    elements.characterGrid.append(createCharacterCard(character));
  });
}

function createStat(value, label) {
  const stat = document.createElement("div");
  stat.className = "result-stat";
  const strong = document.createElement("strong");
  strong.textContent = String(value);
  const span = document.createElement("span");
  span.textContent = label;
  stat.append(strong, span);
  return stat;
}

function createCharacterCard(character) {
  const card = document.createElement("article");
  card.className = "character-card";

  const header = document.createElement("div");
  header.className = "character-header";
  const avatar = document.createElement("div");
  avatar.className = "character-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = initials(character.display_name);
  const identity = document.createElement("div");
  const name = document.createElement("h4");
  name.textContent = character.display_name;
  const aliases = document.createElement("p");
  aliases.className = "character-aliases";
  aliases.textContent = character.aliases.length
    ? `Also: ${character.aliases.join(", ")}`
    : `${character.claims.length} ${character.claims.length === 1 ? "note" : "notes"}`;
  identity.append(name, aliases);
  header.append(avatar, identity);

  const claimList = document.createElement("ul");
  claimList.className = "claim-list";
  character.claims.forEach((claim) => claimList.append(createClaim(claim)));
  card.append(header, claimList);
  return card;
}

function createClaim(claim) {
  const item = document.createElement("li");
  item.className = "claim-item";
  const tag = document.createElement("span");
  tag.className = `claim-tag ${categoryClass(claim.category)}`;
  tag.title = categoryLabel(claim.category);
  const attribute = document.createElement("span");
  attribute.className = "claim-attribute";
  attribute.textContent = claim.attribute.replaceAll("_", " ");
  const value = document.createElement("p");
  value.className = "claim-value";
  value.textContent = claim.value;
  item.append(tag, attribute, value);

  if (claim.evidence.length) {
    const details = document.createElement("details");
    details.className = "evidence-details";
    const summary = document.createElement("summary");
    summary.textContent = `${claim.evidence.length} source ${claim.evidence.length === 1 ? "passage" : "passages"}`;
    details.append(summary);
    claim.evidence.forEach((evidence) => {
      const quote = document.createElement("blockquote");
      quote.className = "evidence-quote";
      quote.textContent = `“${evidence.excerpt.trim()}”`;
      const chapter = document.createElement("span");
      chapter.className = "evidence-chapter";
      chapter.textContent = `Chapter ${evidence.chapter_number}`;
      quote.append(chapter);
      details.append(quote);
    });
    item.append(details);
  }

  return item;
}

function initials(name) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function categoryClass(category) {
  if (category === "model_inference") return "inference";
  if (category === "creative_choice") return "creative";
  return "fact";
}

function categoryLabel(category) {
  if (category === "model_inference") return "Model inference";
  if (category === "creative_choice") return "Creative choice";
  return "Book fact";
}

elements.fileInput.addEventListener("change", () => {
  const [file] = elements.fileInput.files;
  uploadBook(file, false);
});

for (const eventName of ["dragenter", "dragover"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("is-dragging");
  });
}

elements.dropZone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  uploadBook(file, false);
});

elements.chapterRange.addEventListener("input", () => {
  state.selectedChapter = Number(elements.chapterRange.value);
  updateBoundaryUI();
});

elements.demoButton.addEventListener("click", () => loadDemo(false));
elements.heroDemoButton.addEventListener("click", () => loadDemo(true));
elements.analyzeButton.addEventListener("click", runAnalysis);

loadRuntimeConfig();

if (query.get("demo") === "results") {
  window.addEventListener("load", () => loadDemo(true), { once: true });
}
