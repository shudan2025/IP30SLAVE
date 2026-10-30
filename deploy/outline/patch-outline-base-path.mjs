import { readFileSync, writeFileSync } from "node:fs";

const sourcePath = process.argv[2];
if (!sourcePath) {
  throw new Error("Usage: node patch-outline-base-path.mjs <history.ts>");
}

let source = readFileSync(sourcePath, "utf8");
const importLine =
  'import { createBrowserHistory, createPath, parsePath } from "history";';
const historyLine = "const history = createBrowserHistory();";

function replaceExactlyOnce(input, search, replacement) {
  const occurrences = input.split(search).length - 1;
  if (occurrences !== 1) {
    throw new Error(`Expected one occurrence of ${JSON.stringify(search)}, found ${occurrences}`);
  }
  return input.replace(search, replacement);
}

source = replaceExactlyOnce(
  source,
  importLine,
  `${importLine}\nimport env from "~/env";`
);
source = replaceExactlyOnce(
  source,
  historyLine,
  String.raw`const basename = new URL(env.URL).pathname.replace(/\/+$/, "");
const history = createBrowserHistory({ basename });`
);

writeFileSync(sourcePath, source);
