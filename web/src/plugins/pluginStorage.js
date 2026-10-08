// Data a plugin interface saves in the browser (localStorage), separate for each plugin package: the keys are
// prefixed with "nocument.plugin.<package>.", so packages cannot read or overwrite each other's data, nor the web
// app's. Values are saved as JSON (numbers, strings, booleans, arrays, objects). The storage may be unavailable
// (private browsing) or full: set then returns false and get the fallback, so the interface keeps working.
export function createPluginStorage(packageName) {
  const prefix = `nocument.plugin.${packageName}.`;

  function storage() {
    try {
      return window.localStorage;
    } catch {
      return null;
    }
  }

  function ownKeys() {
    const store = storage();
    if (!store) {
      return [];
    }
    return Array.from({ length: store.length }, (_, index) => store.key(index)).filter((key) => key?.startsWith(prefix));
  }

  return Object.freeze({
    // Saved value of key, or fallback if there is none (or it cannot be read).
    get(key, fallback = null) {
      try {
        const saved = storage()?.getItem(prefix + key);
        return saved === null || saved === undefined ? fallback : JSON.parse(saved);
      } catch {
        return fallback;
      }
    },
    // Saves value (JSON) under key; returns false if it cannot be saved (storage unavailable or full).
    set(key, value) {
      try {
        storage().setItem(prefix + key, JSON.stringify(value));
        return true;
      } catch {
        return false;
      }
    },
    remove(key) {
      try {
        storage()?.removeItem(prefix + key);
      } catch {
        // Nothing to remove.
      }
    },
    // Keys saved by the package (without the prefix).
    keys() {
      return ownKeys().map((key) => key.slice(prefix.length));
    },
    // Deletes all the data of the package.
    clear() {
      for (const key of ownKeys()) {
        try {
          storage().removeItem(key);
        } catch {
          // Already removed.
        }
      }
    }
  });
}
