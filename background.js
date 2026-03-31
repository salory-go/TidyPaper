const PAPER_FOLDER = "Papers";
const UNSORTED_FOLDER = "Unsorted";
const STORAGE_KEY = "routingRules";

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

let routingRules = [];
let routingRulesReady = loadRoutingRules();

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "local" || !changes[STORAGE_KEY]) {
    return;
  }

  routingRules = normalizeRules(changes[STORAGE_KEY].newValue);
});

chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
  void routeDownload(downloadItem, suggest);
  return true;
});

async function routeDownload(downloadItem, suggest) {
  try {
    await routingRulesReady;

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
    const relativePath = buildRelativePath(candidateUrls, rawFilename, suggestedFilename);

    suggest({
      filename: relativePath
    });
  } catch (error) {
    console.error("TidyPaper failed to determine filename", error);
    suggest();
  }
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

function buildRelativePath(candidateUrls, rawFilename, suggestedFilename) {
  const matchedRule = findMatchingRule(routingRules, candidateUrls, rawFilename);
  if (!matchedRule) {
    return `${PAPER_FOLDER}/${suggestedFilename}`;
  }

  const category = sanitizePathSegment(matchedRule.category);
  const year = extractYear([rawFilename, ...candidateUrls]);
  if (!category || !year) {
    return `${PAPER_FOLDER}/${UNSORTED_FOLDER}/${suggestedFilename}`;
  }

  return `${PAPER_FOLDER}/${category}/${year}/${suggestedFilename}`;
}

function findMatchingRule(rules, candidateUrls, rawFilename) {
  const hosts = candidateUrls
    .map((url) => getHostname(url))
    .filter(Boolean);
  const searchText = [rawFilename, ...candidateUrls].join(" ").toLowerCase();

  for (const rule of rules) {
    if (!rule.enabled) {
      continue;
    }

    const domainMatch =
      rule.domains.length === 0 ||
      rule.domains.some((domain) => hosts.some((host) => isDomainMatch(host, domain)));
    const keywordMatch =
      rule.keywords.length === 0 ||
      rule.keywords.some((keyword) => searchText.includes(keyword));

    if (domainMatch && keywordMatch) {
      return rule;
    }
  }

  return null;
}

function isDomainMatch(hostname, domain) {
  return hostname === domain || hostname.endsWith(`.${domain}`);
}

async function loadRoutingRules() {
  try {
    const stored = await chrome.storage.local.get({
      [STORAGE_KEY]: []
    });
    routingRules = normalizeRules(stored[STORAGE_KEY]);
  } catch (error) {
    console.error("TidyPaper failed to load routing rules", error);
    routingRules = [];
  }
}

function normalizeRules(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((rule) => normalizeRule(rule))
    .filter(Boolean);
}

function normalizeRule(rule) {
  if (!rule || typeof rule !== "object") {
    return null;
  }

  const category = sanitizePathSegment(rule.category);
  const domains = normalizeDomainList(rule.domains);
  const keywords = normalizeKeywordList(rule.keywords);
  if (!category || (domains.length === 0 && keywords.length === 0)) {
    return null;
  }

  return {
    id: typeof rule.id === "string" && rule.id ? rule.id : createRuleId(),
    enabled: rule.enabled !== false,
    name: typeof rule.name === "string" ? rule.name.trim() : "",
    domains,
    keywords,
    category
  };
}

function normalizeDomainList(value) {
  return normalizeList(value).map((entry) => normalizeDomain(entry)).filter(Boolean);
}

function normalizeKeywordList(value) {
  return normalizeList(value).map((entry) => entry.toLowerCase()).filter(Boolean);
}

function normalizeList(value) {
  if (Array.isArray(value)) {
    return value
      .map((entry) => (typeof entry === "string" ? entry.trim() : ""))
      .filter(Boolean);
  }

  if (typeof value === "string") {
    return value
      .split(",")
      .map((entry) => entry.trim())
      .filter(Boolean);
  }

  return [];
}

function normalizeDomain(domain) {
  const normalized = domain.toLowerCase().trim().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  return normalized.replace(/^\.+|\.+$/g, "");
}

function sanitizePathSegment(value) {
  const sanitized = String(value || "")
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[. ]+$/g, "");
  if (!sanitized) {
    return "";
  }

  const normalized = sanitized.replace(/[- ]+/g, " ").trim();
  const stem = normalized.toLowerCase();
  if (WINDOWS_RESERVED_NAMES.has(stem)) {
    return `paper ${normalized}`;
  }

  return normalized;
}

function extractYear(values) {
  const currentYear = new Date().getFullYear();
  const latestYear = currentYear + 1;
  const yearPattern = /(^|[^0-9])((?:19|20|21)\d{2})(?=[^0-9]|$)/g;

  for (const value of values) {
    if (typeof value !== "string" || !value) {
      continue;
    }

    yearPattern.lastIndex = 0;
    for (const match of value.matchAll(yearPattern)) {
      const year = Number(match[2]);
      if (year >= 1900 && year <= latestYear) {
        return String(year);
      }
    }
  }

  return "";
}

function createRuleId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `rule-${Date.now()}-${Math.random().toString(16).slice(2)}`;
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
