/* global RAG_CONFIG */

const elements = {
  askButton: document.getElementById("askButton"),
  questionInput: document.getElementById("questionInput"),
  equipmentFilter: document.getElementById("equipmentFilter"),
  documentTypeFilter: document.getElementById("documentTypeFilter"),
  topKInput: document.getElementById("topKInput"),
  answerOutput: document.getElementById("answerOutput"),
  citationOutput: document.getElementById("citationOutput")
};

elements.askButton.addEventListener("click", askQuestion);

async function askQuestion() {
  requireConfig();

  const filters = {};
  if (elements.equipmentFilter.value.trim()) {
    filters.equipment_id = elements.equipmentFilter.value.trim();
  }
  if (elements.documentTypeFilter.value) {
    filters.document_type = elements.documentTypeFilter.value;
  }

  elements.askButton.disabled = true;
  elements.answerOutput.textContent = "Searching maintenance knowledge...";
  elements.citationOutput.innerHTML = "";

  try {
    const response = await fetch(RAG_CONFIG.apiEndpoint, {
      method: "POST",
      body: JSON.stringify({
        question: elements.questionInput.value,
        filters,
        top_k: Number(elements.topKInput.value || 5)
      })
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "query returned HTTP " + response.status);
    }

    elements.answerOutput.textContent = payload.answer;
    renderCitations(payload.citations || []);
  } catch (error) {
    elements.answerOutput.textContent = "Query failed: " + error.message;
  } finally {
    elements.askButton.disabled = false;
  }
}

function renderCitations(citations) {
  if (!citations.length) {
    elements.citationOutput.textContent = "No citations returned.";
    return;
  }
  elements.citationOutput.innerHTML = citations.map((citation) => `
    <div class="citation-item">
      <strong>${escapeHtml(citation.citation_id)} · ${escapeHtml(citation.title || "Untitled")}</strong>
      <span>${escapeHtml(citation.equipment_id || "unknown")} · ${escapeHtml(citation.document_type || "unknown")}</span>
      <small>${escapeHtml(citation.source_uri || "")}</small>
    </div>
  `).join("");
}

function requireConfig() {
  const missing = ["apiEndpoint"].filter((key) => !RAG_CONFIG[key]);
  if (missing.length) {
    throw new Error("missing runtime config: " + missing.join(", "));
  }
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
