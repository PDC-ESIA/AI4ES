// Análise sintática, sem carregar/executar o spec. Complementa o isolamento.
const ts = require('typescript');
const fs = require('node:fs');
const source = ts.createSourceFile('test.spec.ts', fs.readFileSync(process.argv[2], 'utf8'),
  ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
let invalid = source.parseDiagnostics.length > 0;
const blocked = new Set(['process', 'global', 'globalThis', 'require', 'eval', 'Function']);
function visit(node) {
  if (ts.isImportDeclaration(node)) {
    if (!ts.isStringLiteral(node.moduleSpecifier) || node.moduleSpecifier.text !== '@playwright/test') invalid = true;
  }
  if (ts.isExportDeclaration(node) || ts.isImportEqualsDeclaration(node)) invalid = true;
  if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) invalid = true;
  if (ts.isIdentifier(node) && blocked.has(node.text)) invalid = true;
  if (ts.isPropertyAccessExpression(node) && ['constructor', '__proto__'].includes(node.name.text)) invalid = true;
  if (ts.isElementAccessExpression(node) && (!ts.isStringLiteral(node.argumentExpression)
      || ['constructor', '__proto__', 'env'].includes(node.argumentExpression.text))) invalid = true;
  ts.forEachChild(node, visit);
}
visit(source);
process.exit(invalid ? 1 : 0);
