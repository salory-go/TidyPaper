const PAPER_FOLDER = "Papers";

const ACADEMIC_DOMAINS = [
  "arxiv.org",
  "openreview.net",
  "aclanthology.org",
  "proceedings.mlr.press",
  "papers.nips.cc",
  "proceedings.neurips.cc",
  "dl.acm.org",
  "ieeexplore.ieee.org",
  "link.springer.com",
  "springer.com",
  "springernature.com",
  "sciencedirect.com",
  "nature.com"
];

const PAPER_FILENAME_PATTERNS = [
  /^\d+_\d{4}_Article_\d+\.pdf$/i,
  /^\d+\.\d+(v\d+)?\.pdf$/i
];

const WINDOWS_RESERVED_NAMES = new Set([
  "con",
  "prn",
  "aux",
  "nul",
  "com1",
  "com2",
  "com3",
  "com4",
  "com5",
  "com6",
  "com7",
  "com8",
  "com9",
  "lpt1",
  "lpt2",
  "lpt3",
  "lpt4",
  "lpt5",
  "lpt6",
  "lpt7",
  "lpt8",
  "lpt9"
]);

chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
  const candidateUrls = getCandidateUrls(downloadItem);
  const rawFilename =
    getBasename(downloadItem.filename) ||
    getBasenameFromUrls(candidateUrls) ||
    "";

  if (!shouldRouteToPaperFolder(downloadItem, candidateUrls, rawFilename)) {
    suggest();
    return;
  }

  const suggestedFilename = buildSuggestedFilename(rawFilename, downloadItem.id);
  suggest({
    filename: `${PAPER_FOLDER}/${suggestedFilename}`
  });
});

function shouldRouteToPaperFolder(downloadItem, candidateUrls, rawFilename) {
  return isPdfLike(downloadItem, candidateUrls, rawFilename) && isPaperLikeSource(candidateUrls, rawFilename);
}

function isPdfLike(downloadItem, candidateUrls, rawFilename) {
  const mime = typeof downloadItem.mime === "string" ? downloadItem.mime.toLowerCase() : "";
  if (mime === "application/pdf") {
    return true;
  }

  if (rawFilename.toLowerCase().endsWith(".pdf")) {
    return true;
  }

  return candidateUrls.some((url) => getPathname(url).toLowerCase().endsWith(".pdf"));
}

function isPaperLikeSource(candidateUrls, rawFilename) {
  return isAcademicDownload(candidateUrls) || matchesPaperFilenamePattern(rawFilename);
}

function isAcademicDownload(candidateUrls) {
  return candidateUrls.some((url) => {
    const hostname = getHostname(url);
    if (!hostname) {
      return false;
    }

    return ACADEMIC_DOMAINS.some((domain) => hostname === domain || hostname.endsWith(`.${domain}`));
  });
}

function matchesPaperFilenamePattern(rawFilename) {
  if (!rawFilename) {
    return false;
  }

  return PAPER_FILENAME_PATTERNS.some((pattern) => pattern.test(rawFilename));
}

function buildSuggestedFilename(rawFilename, downloadId) {
  return ensurePdfExtension(sanitizeFilename(rawFilename), downloadId);
}

function sanitizeFilename(value) {
  const basename = getBasename(value);
  const sanitized = basename
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[. ]+$/g, "");

  if (!sanitized) {
    return "";
  }

  const stem = sanitized.replace(/\.[^.]+$/u, "").toLowerCase();
  if (WINDOWS_RESERVED_NAMES.has(stem)) {
    return `paper-${sanitized}`;
  }

  return sanitized;
}

function ensurePdfExtension(filename, downloadId) {
  const fallbackBase = `paper-${downloadId}`;
  const normalized = filename || fallbackBase;
  const stem = normalized.replace(/\.pdf$/i, "").replace(/\.[^.]+$/u, "").replace(/[. ]+$/g, "");

  return `${stem || fallbackBase}.pdf`;
}

function getCandidateUrls(downloadItem) {
  const urls = [downloadItem.finalUrl, downloadItem.url, downloadItem.referrer];
  return urls.filter((value, index) => typeof value === "string" && value && urls.indexOf(value) === index);
}

function getBasenameFromUrls(urls) {
  for (const url of urls) {
    const basename = getBasename(getPathname(url));
    if (basename) {
      return basename;
    }
  }

  return "";
}

function getPathname(urlString) {
  if (!urlString) {
    return "";
  }

  try {
    return new URL(urlString).pathname || "";
  } catch {
    return "";
  }
}

function getHostname(urlString) {
  if (!urlString) {
    return "";
  }

  try {
    return new URL(urlString).hostname.toLowerCase();
  } catch {
    return "";
  }
}

function getBasename(value) {
  if (typeof value !== "string" || !value) {
    return "";
  }

  const normalized = value.replace(/\\/g, "/");
  const parts = normalized.split("/");
  return parts[parts.length - 1] || "";
}
