// Recent JavaScript methods used by pdf.js 6 but missing in browsers released before 2026 (e.g. Firefox ESR, older
// Chrome): Map/WeakMap.getOrInsert and getOrInsertComputed (TC39 "upsert"; without them the Compiler cannot show any
// document) and Math.sumPrecise (without it pdf.js logs warnings). Loaded in the page (main.js) and in the pdf.js
// worker (pdfWorker.js); browsers that have them keep their own.
for (const Type of [Map, WeakMap]) {
  if (!Type.prototype.getOrInsert) {
    Object.defineProperty(Type.prototype, "getOrInsert", {
      configurable: true,
      writable: true,
      value(key, value) {
        if (!this.has(key)) {
          this.set(key, value);
        }
        return this.get(key);
      }
    });
  }
  if (!Type.prototype.getOrInsertComputed) {
    Object.defineProperty(Type.prototype, "getOrInsertComputed", {
      configurable: true,
      writable: true,
      value(key, callback) {
        if (!this.has(key)) {
          this.set(key, callback(key));
        }
        return this.get(key);
      }
    });
  }
}

// Plain sum: the exact rounding of the native one does not matter for drawing the pages.
if (!Math.sumPrecise) {
  Math.sumPrecise = (values) => {
    let total = 0;
    for (const value of values) {
      total += value;
    }
    return total;
  };
}
