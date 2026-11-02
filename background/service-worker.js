"use strict";

const NATIVE_HOST_NAME = "com.mediadownloader.converter";
const PAGE_URL = chrome.runtime.getURL("popup/popup.html");
const STORAGE_KEY = "selectedConversionFile";
const WINDOW_KEY = "converterWindowId";

const ALLOWED_OUTPUT_FORMATS = new Set([
  "mp3", "m4a", "aac", "ogg", "opus", "wav", "flac", "ac3", "aiff", "wma",
  "mp4", "mkv", "webm", "mov", "avi", "mpeg", "wmv", "flv", "gif_video",
  "jpg", "png", "webp", "bmp", "tiff", "gif", "avif", "ico", "ocr_txt",
  "pdf", "docx", "doc", "odt", "rtf", "txt", "html", "epub",
  "xlsx", "xls", "ods", "csv", "pptx", "ppt", "odp"
]);

const ALLOWED_QUALITIES = new Set(["baixa", "media", "alta"]);

chrome.action.onClicked.addListener(async () => {
  const stored = await chrome.storage.session.get(WINDOW_KEY);
  const oldWindowId = stored[WINDOW_KEY];

  if (typeof oldWindowId === "number") {
    try {
      await chrome.windows.update(oldWindowId, { focused: true });
      return;
    } catch {
      await chrome.storage.session.remove(WINDOW_KEY);
    }
  }

  const createdWindow = await chrome.windows.create({
    url: PAGE_URL,
    type: "popup",
    width: 420,
    height: 660,
    focused: true
  });

  if (typeof createdWindow.id === "number") {
    await chrome.storage.session.set({ [WINDOW_KEY]: createdWindow.id });
  }
});

chrome.windows.onRemoved.addListener(async (windowId) => {
  const stored = await chrome.storage.session.get(WINDOW_KEY);
  if (stored[WINDOW_KEY] === windowId) {
    await chrome.storage.session.remove(WINDOW_KEY);
  }
});

function messageCameFromPage(sender) {
  return Boolean(
    sender &&
    sender.id === chrome.runtime.id &&
    typeof sender.url === "string" &&
    sender.url.startsWith(PAGE_URL)
  );
}

function isValidSelectionToken(token) {
  return typeof token === "string" && /^[a-f0-9]{32}$/.test(token);
}

function hasExactKeys(message, expectedKeys) {
  const actual = Object.keys(message).sort();
  const expected = [...expectedKeys].sort();
  return actual.length === expected.length &&
    actual.every((key, index) => key === expected[index]);
}

function isValidMessage(message) {
  if (!message || typeof message !== "object" || Array.isArray(message)) {
    return false;
  }

  if (["pick-file", "get-selection", "clear-selection"].includes(message.action)) {
    return hasExactKeys(message, ["action"]);
  }

  if (message.action === "convert-file") {
    return hasExactKeys(message, ["action", "format", "quality"]) &&
      typeof message.format === "string" &&
      ALLOWED_OUTPUT_FORMATS.has(message.format) &&
      typeof message.quality === "string" &&
      ALLOWED_QUALITIES.has(message.quality);
  }

  return false;
}

function friendlyNativeError(value) {
  const text = String(value || "");
  if (text.includes("Specified native messaging host not found")) {
    return "Conversor local não encontrado. Verifique o Native Messaging.";
  }
  if (text.includes("forbidden")) {
    return "Esta extensão não está autorizada a usar o conversor local.";
  }
  if (text.includes("Native host has exited")) {
    return "O conversor local foi encerrado inesperadamente.";
  }
  if (text.includes("communicating with the native messaging host")) {
    return "Falha na comunicação com o conversor local.";
  }
  return text || "Não foi possível acessar o conversor local.";
}

function callNativeHost(payload) {
  return new Promise((resolve) => {
    let port = null;
    let finished = false;

    function finish(response) {
      if (finished) return;
      finished = true;
      resolve(response);
      try {
        port?.disconnect();
      } catch {
        // conexão já encerrada
      }
    }

    try {
      port = chrome.runtime.connectNative(NATIVE_HOST_NAME);
    } catch (error) {
      finish({ success: false, error: friendlyNativeError(error?.message) });
      return;
    }

    port.onMessage.addListener(finish);
    port.onDisconnect.addListener(() => {
      if (!finished) {
        finish({
          success: false,
          error: friendlyNativeError(chrome.runtime.lastError?.message)
        });
      }
    });

    try {
      port.postMessage(payload);
    } catch (error) {
      finish({ success: false, error: friendlyNativeError(error?.message) });
    }
  });
}

async function saveSelection(selectionData) {
  await chrome.storage.local.set({ [STORAGE_KEY]: selectionData });
}

async function getSavedSelection() {
  const result = await chrome.storage.local.get(STORAGE_KEY);
  const selection = result[STORAGE_KEY];

  if (!selection ||
      !isValidSelectionToken(selection.selection) ||
      typeof selection.name !== "string" ||
      !Array.isArray(selection.outputs)) {
    return null;
  }

  return selection;
}

async function clearSavedSelection() {
  await chrome.storage.local.remove(STORAGE_KEY);
}

function sanitizeSelection(response) {
  if (!response || response.success !== true ||
      !isValidSelectionToken(response.selection)) {
    return null;
  }

  const outputs = Array.isArray(response.outputs)
    ? response.outputs.filter((format) =>
        typeof format === "string" && ALLOWED_OUTPUT_FORMATS.has(format))
    : [];

  if (outputs.length === 0) return null;

  return {
    selection: response.selection,
    name: String(response.name || "arquivo").slice(0, 255),
    label: String(response.label || "Arquivo").slice(0, 50),
    extension: String(response.extension || "").slice(0, 20),
    outputs,
    savedAt: Date.now()
  };
}

async function pickFile() {
  const nativeResponse = await callNativeHost({ action: "pick-file" });

  if (nativeResponse?.cancelled) {
    return { success: false, cancelled: true };
  }

  if (!nativeResponse || nativeResponse.success !== true) {
    return {
      success: false,
      error: String(nativeResponse?.error ||
        "Não foi possível selecionar o arquivo.").slice(0, 500)
    };
  }

  const selectionData = sanitizeSelection(nativeResponse);
  if (!selectionData) {
    return { success: false, error: "O conversor retornou dados inválidos." };
  }

  await saveSelection(selectionData);
  return { success: true, ...selectionData };
}

async function getSelection() {
  const selection = await getSavedSelection();
  return selection
    ? { success: true, selected: true, ...selection }
    : { success: true, selected: false };
}

async function convertFile(message) {
  const selection = await getSavedSelection();

  if (!selection) {
    return { success: false, error: "Nenhum arquivo está selecionado." };
  }

  if (!selection.outputs.includes(message.format)) {
    return { success: false, error: "Formato incompatível com o arquivo selecionado." };
  }

  const nativeResponse = await callNativeHost({
    action: "convert-file",
    selection: selection.selection,
    format: message.format,
    quality: message.quality
  });

  if (nativeResponse?.cancelled) {
    return { success: false, cancelled: true };
  }

  if (!nativeResponse || nativeResponse.success !== true) {
    const errorText = String(nativeResponse?.error ||
      "Não foi possível converter o arquivo.").slice(0, 500);

    if (errorText.includes("expirada")) {
      await clearSavedSelection();
    }

    return { success: false, error: errorText };
  }

  const outputName = String(nativeResponse.output ||
    "arquivo convertido").slice(0, 255);

  await clearSavedSelection();
  return { success: true, output: outputName };
}

async function processRequest(message) {
  if (message.action === "pick-file") return pickFile();
  if (message.action === "get-selection") return getSelection();
  if (message.action === "clear-selection") {
    await clearSavedSelection();
    return { success: true };
  }
  if (message.action === "convert-file") return convertFile(message);
  return { success: false, error: "Ação inválida." };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!messageCameFromPage(sender)) return false;

  if (!isValidMessage(message)) {
    sendResponse({ success: false, error: "Pedido inválido." });
    return false;
  }

  processRequest(message)
    .then(sendResponse)
    .catch((error) => {
      sendResponse({
        success: false,
        error: error?.message || "Erro inesperado."
      });
    });

  return true;
});
