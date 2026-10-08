import { execSync } from "node:child_process";
import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// Version of the frontend: the git commit it is built from (hash and date), shown in Settings. From NOCUMENT_COMMIT
// and NOCUMENT_COMMIT_DATE when set (the Docker build has no .git), otherwise from git; null if unknown.
function frontendVersion() {
  let commit = process.env.NOCUMENT_COMMIT?.trim() ?? "";
  let date = process.env.NOCUMENT_COMMIT_DATE?.trim() ?? "";
  if (!commit) {
    try {
      [commit = "", date = ""] = execSync("git -c safe.directory=* log -1 --format=%H%n%cI", { cwd: "..", stdio: ["ignore", "pipe", "ignore"] })
        .toString().trim().split("\n");
    } catch {
      // No git (or not a repository): unknown version.
    }
  }
  return { commit: commit || null, date: date || null };
}

export default defineConfig({
  plugins: [svelte()],
  define: {
    __NOCUMENT_VERSION__: JSON.stringify(frontendVersion())
  },
  server: {
    // Host names the dev server answers to besides localhost (e.g. the name of the server in the local network).
    allowedHosts: (process.env.NOCUMENT_DEV_ALLOWED_HOSTS ?? "").split(",").map((host) => host.trim()).filter(Boolean),
    // The translations live in ../locales, shared with the backend.
    fs: { allow: [".."] },
    proxy: {
      // The development backend (python -m src.app), on the same port it listens on.
      "/api": `http://localhost:${process.env.NOCUMENT_BACKEND_PORT || 5000}`
    }
  }
});
