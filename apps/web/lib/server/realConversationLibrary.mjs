import path from 'node:path';
import { access, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
const REAL_CONVERSATION_LIBRARY_RELATIVE_PATH =
  'testdata/agent/soil-moisture/real-conversations/cases/real-conversation-library.md';

function ancestorDirs(startDir) {
  const dirs = [];
  let currentDir = path.resolve(startDir);

  while (true) {
    dirs.push(currentDir);
    const parentDir = path.dirname(currentDir);
    if (parentDir === currentDir) {
      break;
    }
    currentDir = parentDir;
  }

  return dirs;
}

function candidateLibraryPaths() {
  const candidates = new Set();

  for (const baseDir of [...ancestorDirs(process.cwd()), ...ancestorDirs(MODULE_DIR)]) {
    candidates.add(path.resolve(baseDir, REAL_CONVERSATION_LIBRARY_RELATIVE_PATH));
  }

  return [...candidates];
}

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
  let lastError = null;

  for (const candidatePath of candidateLibraryPaths()) {
    try {
      await access(candidatePath);
      const markdown = await readFile(candidatePath, 'utf8');
      return parseRealConversationLibraryMarkdown(markdown);
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error('真实问答库文件不存在');
}
