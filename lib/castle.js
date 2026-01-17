const crypto = require("crypto");

const BASE = process.env.CASTLE_BASE || "https://api.fstcy.com";
const PKG = process.env.CASTLE_PKG || "com.external.castle";
const CHANNEL = process.env.CASTLE_CHANNEL || "IndiaA";
const CLIENT = process.env.CASTLE_CLIENT || "1";
const LANG = process.env.CASTLE_LANG || "en-US";
const SUFFIX = process.env.CASTLE_SUFFIX || "T!BgJB";

const DEFAULT_HEADERS = {
  "User-Agent": "okhttp/4.9.3",
  Accept: "application/json",
  "Accept-Language": "en-US,en;q=0.9",
  Connection: "Keep-Alive",
  Referer: BASE,
};

const SECURITY_CACHE = {
  value: null,
  fetchedAt: 0,
};

const SECURITY_TTL_MS = 10 * 60 * 1000;

function deriveKeyFromSec(secB64) {
  const apiKey = Buffer.from(secB64, "base64");
  let keyMaterial = Buffer.concat([apiKey, Buffer.from(SUFFIX, "ascii")]);
  if (keyMaterial.length < 16) {
    keyMaterial = Buffer.concat([
      keyMaterial,
      Buffer.alloc(16 - keyMaterial.length),
    ]);
  } else if (keyMaterial.length > 16) {
    keyMaterial = keyMaterial.subarray(0, 16);
  }
  return keyMaterial;
}

function decryptB64(cipherB64, secB64) {
  if (!cipherB64) {
    throw new Error("Empty ciphertext");
  }
  const key = deriveKeyFromSec(secB64);
  const ciphertext = Buffer.from(cipherB64, "base64");
  const decipher = crypto.createDecipheriv("aes-128-cbc", key, key);
  const plaintext = Buffer.concat([
    decipher.update(ciphertext),
    decipher.final(),
  ]);
  return plaintext.toString("utf-8");
}

async function extractCipherFromResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const payload = await response.json();
    if (payload && typeof payload === "object") {
      const data = payload.data;
      if (typeof data === "string" && data.trim()) {
        return data.trim();
      }
    }
  } else {
    try {
      const payload = await response.json();
      if (payload && typeof payload === "object") {
        const data = payload.data;
        if (typeof data === "string" && data.trim()) {
          return data.trim();
        }
      }
    } catch (error) {
      // ignore and fall back to text
    }
  }
  const text = (await response.text()).trim();
  if (text) {
    return text;
  }
  throw new Error(
    `Empty/invalid response (HTTP ${response.status}) from ${response.url}`
  );
}

async function fetchSecurityKey() {
  const now = Date.now();
  if (SECURITY_CACHE.value && now - SECURITY_CACHE.fetchedAt < SECURITY_TTL_MS) {
    return SECURITY_CACHE.value;
  }
  const url = `${BASE}/v0.1/system/getSecurityKey/1?channel=${CHANNEL}&clientType=${CLIENT}&lang=${LANG}`;
  const response = await fetch(url, { headers: DEFAULT_HEADERS });
  const payload = await response.json().catch(() => null);
  if (!payload || payload.code !== 200 || !payload.data) {
    throw new Error(`securityKey: unexpected response: ${JSON.stringify(payload)}`);
  }
  SECURITY_CACHE.value = payload.data;
  SECURITY_CACHE.fetchedAt = now;
  return payload.data;
}

async function decryptPayload(cipherText, secB64) {
  const securityKey = secB64 || (await fetchSecurityKey());
  const decrypted = decryptB64(cipherText, securityKey);
  return JSON.parse(decrypted);
}

async function fetchHome(secB64, page, size) {
  const url = `${BASE}/film-api/v0.1/category/home?channel=${CHANNEL}&clientType=${CLIENT}&lang=${LANG}&locationId=1001&mode=1&packageName=${PKG}&page=${page}&size=${size}`;
  const response = await fetch(url, { headers: DEFAULT_HEADERS });
  const cipher = await extractCipherFromResponse(response);
  return decryptPayload(cipher, secB64);
}

async function fetchSearch(secB64, keyword, page, size) {
  const params = new URLSearchParams({
    channel: CHANNEL,
    clientType: CLIENT,
    keyword,
    lang: LANG,
    mode: "1",
    packageName: PKG,
    page: String(page),
    size: String(size),
  });
  const url = `${BASE}/film-api/v1.1.0/movie/searchByKeyword?${params.toString()}`;
  const response = await fetch(url, { headers: DEFAULT_HEADERS });
  const cipher = await extractCipherFromResponse(response);
  return decryptPayload(cipher, secB64);
}

async function fetchDetails(secB64, movieId) {
  const url = `${BASE}/film-api/v1.1/movie?channel=${CHANNEL}&clientType=${CLIENT}&lang=${LANG}&movieId=${movieId}&packageName=${PKG}`;
  const response = await fetch(url, { headers: DEFAULT_HEADERS });
  const cipher = await extractCipherFromResponse(response);
  return decryptPayload(cipher, secB64);
}

async function fetchVideo2(secB64, payload) {
  const url = `${BASE}/film-api/v2.0.1/movie/getVideo2?clientType=${CLIENT}&packageName=${PKG}&channel=${CHANNEL}&lang=${LANG}`;
  const body = {
    mode: "1",
    appMarket: "GuanWang",
    clientType: "1",
    woolUser: "false",
    apkSignKey: "ED0955EB04E67A1D9F3305B95454FED485261475",
    androidVersion: "13",
    movieId: payload.movieId,
    episodeId: payload.episodeId,
    isNewUser: "true",
    resolution: String(payload.resolution),
    packageName: PKG,
  };
  const response = await fetch(url, {
    method: "POST",
    headers: {
      ...DEFAULT_HEADERS,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const cipher = await extractCipherFromResponse(response);
  return decryptPayload(cipher, secB64);
}

async function fetchVideoV1(secB64, payload) {
  const params = new URLSearchParams({
    apkSignKey: "ED0955EB04E67A1D9F3305B95454FED485261475",
    channel: CHANNEL,
    clientType: CLIENT,
    episodeId: String(payload.episodeId),
    lang: LANG,
    languageId: String(payload.languageId),
    mode: "1",
    movieId: String(payload.movieId),
    packageName: PKG,
    resolution: String(payload.resolution),
  });
  const url = `${BASE}/film-api/v1.9.1/movie/getVideo?${params.toString()}`;
  const response = await fetch(url, { headers: DEFAULT_HEADERS });
  const cipher = await extractCipherFromResponse(response);
  return decryptPayload(cipher, secB64);
}

function parseNumber(value, fallback, { min, max } = {}) {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed)) {
    return fallback;
  }
  if (typeof min === "number" && parsed < min) {
    return min;
  }
  if (typeof max === "number" && parsed > max) {
    return max;
  }
  return parsed;
}

module.exports = {
  fetchSecurityKey,
  fetchHome,
  fetchSearch,
  fetchDetails,
  fetchVideo2,
  fetchVideoV1,
  parseNumber,
};
