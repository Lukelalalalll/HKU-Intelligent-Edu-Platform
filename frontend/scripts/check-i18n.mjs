/**
 * Guardrail: fail when user-facing CJK text is still hardcoded in the app.
 *
 * Parses every TS/TSX source file and reports Chinese characters inside string
 * literals, template literals and JSX text. Comments are ignored automatically
 * because they are not part of the AST that this script walks.
 *
 * Intentional exceptions (message catalogs, locale metadata, tests, native
 * language names) are skipped explicitly. Run with `npm run check:i18n`.
 */
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const SRC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src");
const CJK = /[\u3400-\u9fff\uf900-\ufaff]/;

// Copy lives in the message catalogs; these files legitimately contain CJK.
const SKIP_PATHS = [
  path.join(SRC, "i18n", "messages"),
  path.join(SRC, "i18n", "config.ts"), // native language labels (English / 粵語 / 简体中文)
];
const SKIP_FILE = /\.test\.(ts|tsx)$/;

function collectFiles(dir, files = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (SKIP_PATHS.some((skip) => full === skip || full.startsWith(`${skip}${path.sep}`))) continue;
    if (entry.isDirectory()) {
      collectFiles(full, files);
    } else if (/\.(ts|tsx)$/.test(entry.name) && !SKIP_FILE.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

function isModuleSpecifier(node) {
  const parent = node.parent;
  return Boolean(
    parent &&
      (ts.isImportDeclaration(parent) ||
        ts.isExportDeclaration(parent) ||
        ts.isModuleDeclaration(parent) ||
        ts.isExternalModuleReference(parent) ||
        (ts.isCallExpression(parent) && parent.expression.kind === ts.SyntaxKind.ImportKeyword)),
  );
}

const findings = [];

function report(sourceFile, node, text) {
  const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile));
  findings.push({ file: path.relative(path.resolve(SRC, ".."), sourceFile.fileName), line: line + 1, text: text.trim().slice(0, 120) });
}

function inspect(file) {
  const content = readFileSync(file, "utf8");
  const sourceFile = ts.createSourceFile(file, content, ts.ScriptTarget.Latest, true, file.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);

  const visit = (node) => {
    if (node.kind === ts.SyntaxKind.JsxText) {
      const text = node.getText(sourceFile);
      if (CJK.test(text)) report(sourceFile, node, text);
    } else if (node.kind === ts.SyntaxKind.StringLiteral || node.kind === ts.SyntaxKind.NoSubstitutionTemplateLiteral) {
      const text = node.text;
      if (CJK.test(text) && !isModuleSpecifier(node)) report(sourceFile, node, text);
    } else if (
      node.kind === ts.SyntaxKind.TemplateHead ||
      node.kind === ts.SyntaxKind.TemplateMiddle ||
      node.kind === ts.SyntaxKind.TemplateTail
    ) {
      const text = node.getText(sourceFile);
      if (CJK.test(text)) report(sourceFile, node, text);
    }
    ts.forEachChild(node, visit);
  };

  visit(sourceFile);
}

for (const file of collectFiles(SRC)) inspect(file);

if (findings.length) {
  console.error(`Hardcoded CJK copy found in ${findings.length} place(s):\n`);
  for (const finding of findings) console.error(`  ${finding.file}:${finding.line}  ${finding.text}`);
  console.error("\nMove the copy into src/i18n/messages/<namespace>.ts (en + zh-Hans + yue).");
  process.exit(1);
}

console.log("check:i18n passed — no hardcoded CJK copy outside src/i18n/messages.");
