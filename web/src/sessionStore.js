// Page sessions saved in IndexedDB (it supports Blobs and has no ~5 MB limit like localStorage).
// One session per page, identified by a key:
// - "analyzer" (the Compiler, named Analyzer before): { file, fileName, pdf, compiledDocx, keywords, keywordValues, sidebarWidth }
// - "builder": { file, fileName } (the last .docx returned by the backend)
const DB_NAME = "nocument";
const DB_VERSION = 2;
const STORE_NAME = "sessions";
// Version 1: only the Analyzer session, in the "analyzer-session" store with key "current".
const LEGACY_STORE_NAME = "analyzer-session";
const LEGACY_KEY = "current";

// Opens the database, creating the store the first time and moving the session saved by version 1.
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      const sessions = database.createObjectStore(STORE_NAME);
      if (database.objectStoreNames.contains(LEGACY_STORE_NAME)) {
        const legacy = request.transaction.objectStore(LEGACY_STORE_NAME).get(LEGACY_KEY);
        legacy.onsuccess = () => {
          if (legacy.result) {
            sessions.put(legacy.result, "analyzer");
          }
          database.deleteObjectStore(LEGACY_STORE_NAME);
        };
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Runs action on the store in a transaction and returns the result of the request.
async function withStore(mode, action) {
  const database = await openDatabase();
  try {
    return await new Promise((resolve, reject) => {
      const transaction = database.transaction(STORE_NAME, mode);
      const request = action(transaction.objectStore(STORE_NAME));
      transaction.oncomplete = () => resolve(request.result);
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally {
    database.close();
  }
}

// Returns the session saved with the given key, or undefined.
export function loadSession(key) {
  return withStore("readonly", (store) => store.get(key));
}

// Replaces the session saved with the given key.
export function saveSession(key, session) {
  return withStore("readwrite", (store) => store.put(session, key));
}

// Deletes the session saved with the given key.
export function clearSession(key) {
  return withStore("readwrite", (store) => store.delete(key));
}
