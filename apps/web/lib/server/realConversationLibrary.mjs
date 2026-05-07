import path from 'node:path';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
const REAL_CONVERSATION_LIBRARY_PATH = path.resolve(
  MODULE_DIR,
  '../../../../testdata/agent/soil-moisture/real-conversations/cases/real-conversation-library.md',
);

function isTableRow(line) {
  return line.trim().startsWith('|');
}

function isSeparatorRow(line) {
  return /^\|\s*-/.test(line.trim());
}

function parseTurns(question) {
  return String(question)
    .split('→')
    .map((part) => part.trim())
    .filter(Boolean);
}

export function parseRealConversationLibraryMarkdown(markdown) {
  const cases = [];

  for (const line of String(markdown).split(/\r?\n/)) {
    if (!isTableRow(line) || isSeparatorRow(line)) {
      continue;
    }

    const cells = line
      .split('|')
      .slice(1, -1)
      .map((cell) => cell.trim());

    if (cells.length < 5 || !/^\d+$/.test(cells[0])) {
      continue;
    }

    const [id, category, question, capability, expectation] = cells;
    cases.push({
      id: Number(id),
      category,
      question,
      turns: parseTurns(question),
      capability,
      expectation,
    });
  }

  return cases;
}

export async function listRealConversationCases() {
  const markdown = await readFile(REAL_CONVERSATION_LIBRARY_PATH, 'utf8');
  return parseRealConversationLibraryMarkdown(markdown);
}
