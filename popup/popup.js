"use strict";

const pickButton = document.getElementById("pick-button");
const changeButton = document.getElementById("change-button");
const selectedBox = document.getElementById("selected-box");
const selectedName = document.getElementById("selected-name");
const selectedType = document.getElementById("selected-type");
const formatSelect = document.getElementById("format");
const qualityField = document.getElementById("quality-field");
const qualitySelect = document.getElementById("quality");
const convertButton = document.getElementById("convert-button");
const statusText = document.getElementById("status");

const STORAGE_KEY = "selectedConversionFile";

const QUALITY_FORMATS = new Set([
  "mp3", "m4a", "aac", "ogg", "opus", "ac3", "wma",
  "mp4", "mkv", "webm", "mov", "avi", "mpeg", "wmv", "flv", "gif_video",
  "jpg", "webp", "avif"
]);

const FORMAT_LABELS = {
  mp3: "MP3 (áudio)",
  m4a: "M4A (áudio AAC)",
  aac: "AAC (áudio)",
  ogg: "OGG (áudio)",
  opus: "OPUS (áudio)",
  wav: "WAV (áudio sem perda)",
  flac: "FLAC (áudio sem perda)",
  ac3: "AC3 (áudio)",
  aiff: "AIFF (áudio sem perda)",
  wma: "WMA (áudio)",
  mp4: "MP4 (vídeo)",
  mkv: "MKV (vídeo)",
  webm: "WEBM (vídeo)",
  mov: "MOV (vídeo)",
  avi: "AVI (vídeo)",
  mpeg: "MPEG (vídeo)",
  wmv: "WMV (vídeo)",
  flv: "FLV (vídeo)",
  gif_video: "GIF animado",
  jpg: "JPG (imagem)",
  png: "PNG (imagem)",
  webp: "WEBP (imagem)",
  bmp: "BMP (imagem)",
  tiff: "TIFF (imagem)",
  gif: "GIF (imagem)",
  avif: "AVIF (imagem)",
  ico: "ICO (ícone)",
  ocr_txt: "TXT por OCR",
  pdf: "PDF",
  docx: "DOCX (Word)",
  doc: "DOC (Word antigo)",
  odt: "ODT (Writer)",
  rtf: "RTF",
  txt: "TXT (texto)",
  html: "HTML",
  epub: "EPUB",
  xlsx: "XLSX (Excel)",
  xls: "XLS (Excel antigo)",
  ods: "ODS (Calc)",
  csv: "CSV",
  pptx: "PPTX (PowerPoint)",
  ppt: "PPT (PowerPoint antigo)",
  odp: "ODP (Impress)"
};

let selectionToken = null;
let availableOutputs = [];
let busy = false;

function showStatus(message, type = "") {
  statusText.textContent = message;
  statusText.className = type ? `status ${type}` : "status";
}

function setPlaceholder(text) {
  formatSelect.replaceChildren();
  const option = document.createElement("option");
  option.value = "";
  option.textContent = text;
  formatSelect.appendChild(option);
}

function updateInterface() {
  const hasFile = typeof selectionToken === "string" && selectionToken.length > 0;
  const selectedFormat = formatSelect.value;
  const validFormat = availableOutputs.includes(selectedFormat);

  pickButton.disabled = busy;
  changeButton.disabled = busy;
  formatSelect.disabled = busy || !hasFile || availableOutputs.length === 0;
  qualityField.hidden = !validFormat || !QUALITY_FORMATS.has(selectedFormat);
  qualitySelect.disabled = busy || qualityField.hidden;
  convertButton.disabled = busy || !hasFile || !validFormat;
}

function fillFormats(formats) {
  availableOutputs = Array.isArray(formats)
    ? [...new Set(formats.filter((item) => typeof item === "string" && item.length > 0))]
    : [];

  formatSelect.replaceChildren();

  if (availableOutputs.length === 0) {
    setPlaceholder("Nenhuma conversão disponível");
    updateInterface();
    return;
  }

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Escolha o formato";
  formatSelect.appendChild(placeholder);

  for (const outputFormat of availableOutputs) {
    const option = document.createElement("option");
    option.value = outputFormat;
    option.textContent = FORMAT_LABELS[outputFormat] || outputFormat.toUpperCase();
    formatSelect.appendChild(option);
  }

  formatSelect.value = "";
  updateInterface();
}

function showSelectedFile(selection) {
  selectionToken = selection.selection;
  selectedName.textContent = selection.name || "arquivo";
  selectedType.textContent = `Tipo detectado: ${selection.label || "Arquivo"}`;
  selectedBox.hidden = false;
  fillFormats(selection.outputs);
  showStatus("Arquivo carregado. Escolha o formato de saída.", "success");
}

function clearInterface() {
  selectionToken = null;
  availableOutputs = [];
  selectedBox.hidden = true;
  selectedName.textContent = "";
  selectedType.textContent = "";
  setPlaceholder("Escolha o arquivo primeiro");
  updateInterface();
}

async function restoreSelection() {
  try {
    const response = await chrome.runtime.sendMessage({ action: "get-selection" });

    if (response && response.success === true && response.selected === true) {
      showSelectedFile(response);
      return;
    }

    clearInterface();
    showStatus("Escolha um arquivo para começar.");
  } catch (error) {
    clearInterface();
    showStatus("Não foi possível recuperar o arquivo selecionado.", "error");
  }
}

async function chooseFile() {
  if (busy) return;

  busy = true;
  updateInterface();
  showStatus("Escolha o arquivo na janela que abriu...");

  try {
    const response = await chrome.runtime.sendMessage({ action: "pick-file" });

    if (response && response.cancelled) {
      showStatus(selectionToken ? "Seleção mantida." : "Nenhum arquivo selecionado.");
      return;
    }

    if (!response || response.success !== true) {
      throw new Error(response?.error || "Não foi possível selecionar o arquivo.");
    }

    showSelectedFile(response);
  } catch (error) {
    showStatus(error?.message || "Erro inesperado ao selecionar o arquivo.", "error");
  } finally {
    busy = false;
    updateInterface();
  }
}

async function changeFile() {
  if (busy) return;

  try {
    await chrome.runtime.sendMessage({ action: "clear-selection" });
  } catch {
    // Se a limpeza falhar, ainda tentamos trocar o arquivo.
  }

  clearInterface();
  await chooseFile();
}

async function convertFile() {
  if (busy || !selectionToken) return;

  const selectedFormat = formatSelect.value;

  if (!availableOutputs.includes(selectedFormat)) {
    showStatus("Escolha primeiro o formato de saída.", "error");
    return;
  }

  busy = true;
  updateInterface();
  showStatus("Escolha a pasta de destino...");

  try {
    const response = await chrome.runtime.sendMessage({
      action: "convert-file",
      format: selectedFormat,
      quality: qualityField.hidden ? "media" : qualitySelect.value
    });

    if (response && response.cancelled) {
      showStatus("Conversão cancelada. O arquivo continua selecionado.");
      return;
    }

    if (!response || response.success !== true) {
      throw new Error(response?.error || "Não foi possível converter o arquivo.");
    }

    const outputName = response.output || "arquivo convertido";
    clearInterface();
    showStatus(`Conversão concluída: ${outputName}`, "success");
  } catch (error) {
    showStatus(error?.message || "Erro inesperado durante a conversão.", "error");
  } finally {
    busy = false;
    updateInterface();
  }
}

pickButton.addEventListener("click", chooseFile);
changeButton.addEventListener("click", changeFile);
formatSelect.addEventListener("change", updateInterface);
qualitySelect.addEventListener("change", updateInterface);
convertButton.addEventListener("click", convertFile);

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "local" || !changes[STORAGE_KEY] || busy) return;

  const newSelection = changes[STORAGE_KEY].newValue;

  if (newSelection && newSelection.selection) {
    showSelectedFile(newSelection);
  } else {
    clearInterface();
  }
});

setPlaceholder("Carregando...");
updateInterface();
restoreSelection();
