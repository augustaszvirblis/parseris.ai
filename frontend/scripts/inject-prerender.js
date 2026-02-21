/**
 * Injects parseris.ai prerender content into build/index.html for SEO.
 * Run after `npm run build` when PARSERIS_PRERENDER=1 (e.g. parseris.ai deployment).
 * Replaces title and meta description, and adds static heading/paragraph inside #root
 * so crawlers see real content before JavaScript runs. React will replace #root on mount.
 */

const fs = require("fs");
const path = require("path");

const PARSERIS_PRERENDER = process.env.PARSERIS_PRERENDER === "1";
const buildDir = path.join(__dirname, "..", "build");
const indexPath = path.join(buildDir, "index.html");

if (!PARSERIS_PRERENDER) {
  process.exit(0);
}

if (!fs.existsSync(indexPath)) {
  console.error(
    "inject-prerender: build/index.html not found. Run after npm run build."
  );
  process.exit(1);
}

const TITLE = "Parseris.ai - Free PDF to Excel";
const META_DESCRIPTION =
  "Convert PDF to Excel for free. Extract tables and data from PDFs into spreadsheets quickly and accurately with Parseris.ai.";
const PRERENDER_BODY = [
  '<main id="prerender-content" style="font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem;">',
  '  <h1 style="font-size:1.75rem;margin-bottom:0.5rem;">Parseris.ai – Free PDF to Excel</h1>',
  '  <p style="font-size:1.125rem;line-height:1.6;color:#333;">Convert PDF to Excel for free. Extract tables and data from PDFs into spreadsheets quickly and accurately.</p>',
  '  <p style="font-size:0.9375rem;color:#666;">Sign in or sign up to get started.</p>',
  "</main>",
].join("\n");

let html = fs.readFileSync(indexPath, "utf8");

// Replace title
html = html.replace(/<title>[\s\S]*?<\/title>/, `<title>${TITLE}</title>`);

// Replace or add meta description
if (html.includes('name="description"')) {
  html = html.replace(
    /<meta\s+name="description"\s+content="[^"]*"\s*\/?>/,
    `<meta name="description" content="${META_DESCRIPTION}" />`
  );
} else {
  html = html.replace(
    /<meta\s+name="viewport"/,
    `<meta name="description" content="${META_DESCRIPTION}" />\n    <meta name="viewport"`
  );
}

// Inject prerender content inside <div id="root"> (React will replace it on mount)
html = html.replace(
  /<div id="root"><\/div>/,
  `<div id="root">${PRERENDER_BODY}</div>`
);

fs.writeFileSync(indexPath, html, "utf8");
console.log(
  "inject-prerender: Injected parseris.ai title, description, and prerender content into build/index.html"
);
