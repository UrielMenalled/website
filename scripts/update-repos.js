/**
 * update-repos.js
 *
 * Fetches all public GitHub repositories for a user,
 * filters out excluded repos, and updates the marked
 * section in research.html with styled repository tiles.
 *
 * Runs in GitHub Actions — no API token required for public repos.
 */

import https from "https";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ── Configuration ────────────────────────────────────────────────────────────

const USERNAME = process.env.GITHUB_USERNAME || "UrielMenalled";
const EXCLUDED_REPOS = ["UrielMenalled", "lab-website"];
const HTML_FILE = path.join(process.cwd(), "research.html");

// These markers must exist in your research.html
const START_MARKER = "<!-- REPO-TILES:START -->";
const END_MARKER = "<!-- REPO-TILES:END -->";

// ── Fetch repos from GitHub API ───────────────────────────────────────────────

function fetchRepos(username) {
  return new Promise((resolve, reject) => {
    const allRepos = [];

    function fetchPage(page) {
      const url = `https://api.github.com/users/${username}/repos?type=public&sort=updated&per_page=100&page=${page}`;
      const options = {
        headers: {
          "User-Agent": "repo-tile-updater",
          Accept: "application/vnd.github+json",
        },
      };

      https
        .get(url, options, (res) => {
          let body = "";
          res.on("data", (chunk) => (body += chunk));
          res.on("end", () => {
            if (res.statusCode !== 200) {
              reject(new Error(`GitHub API returned ${res.statusCode}: ${body}`));
              return;
            }
            const repos = JSON.parse(body);
            if (repos.length === 0) {
              resolve(allRepos);
            } else {
              allRepos.push(...repos);
              if (repos.length === 100) {
                fetchPage(page + 1);
              } else {
                resolve(allRepos);
              }
            }
          });
        })
        .on("error", reject);
    }

    fetchPage(1);
  });
}

// ── Build the HTML tiles ──────────────────────────────────────────────────────

function buildTilesHTML(repos) {
  const filtered = repos
    .filter((r) => !EXCLUDED_REPOS.includes(r.name))
    .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));

  if (filtered.length === 0) {
    return `<p class="repo-tiles__empty">No public repositories found.</p>`;
  }

  const tiles = filtered
    .map((repo) => {
      const description = repo.description
        ? escapeHTML(repo.description)
        : '<span class="repo-tile__no-desc">No description provided.</span>';

      const language = repo.language
        ? `<span class="repo-tile__language">${escapeHTML(repo.language)}</span>`
        : "";

      const stars =
        repo.stargazers_count > 0
          ? `<span class="repo-tile__stars">★ ${repo.stargazers_count}</span>`
          : "";

      return `
      <a class="repo-tile" href="${repo.html_url}" target="_blank" rel="noopener noreferrer">
        <div class="repo-tile__header">
          <span class="repo-tile__name">${escapeHTML(repo.name)}</span>
          ${language}
        </div>
        <p class="repo-tile__desc">${description}</p>
        <div class="repo-tile__footer">
          ${stars}
          <span class="repo-tile__updated">Updated ${formatDate(repo.updated_at)}</span>
        </div>
      </a>`.trim();
    })
    .join("\n      ");

  return `\n      ${tiles}\n    `;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function escapeHTML(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

// ── Update research.html ──────────────────────────────────────────────────────

function updateHTML(tilesHTML) {
  if (!fs.existsSync(HTML_FILE)) {
    throw new Error(`research.html not found at ${HTML_FILE}`);
  }

  const original = fs.readFileSync(HTML_FILE, "utf8");

  const startIdx = original.indexOf(START_MARKER);
  const endIdx = original.indexOf(END_MARKER);

  if (startIdx === -1 || endIdx === -1) {
    throw new Error(
      `Markers not found in research.html.\n` +
        `Make sure both "${START_MARKER}" and "${END_MARKER}" exist in your file.`
    );
  }

  const before = original.slice(0, startIdx + START_MARKER.length);
  const after = original.slice(endIdx);
  const updated = before + tilesHTML + after;

  if (updated === original) {
    console.log("No changes detected — research.html is already up to date.");
    return false;
  }

  fs.writeFileSync(HTML_FILE, updated, "utf8");
  console.log("research.html updated successfully.");
  return true;
}

// ── Main ──────────────────────────────────────────────────────────────────────

(async () => {
  try {
    console.log(`Fetching public repos for: ${USERNAME}`);
    const repos = await fetchRepos(USERNAME);
    console.log(`Found ${repos.length} public repos.`);

    const tilesHTML = buildTilesHTML(repos);
    updateHTML(tilesHTML);
  } catch (err) {
    console.error("Error:", err.message);
    process.exit(1);
  }
})();
