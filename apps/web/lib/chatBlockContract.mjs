export const PAGINATED_TABLE_BLOCK_TYPES = Object.freeze([
  'list_table',
  'group_table',
]);

export const PAGINATED_TABLE_TOTAL_UNITS = Object.freeze({
  list_table: '条',
  group_table: '组',
});

export function isPaginatedTableBlockType(blockType) {
  return typeof blockType === 'string' && PAGINATED_TABLE_BLOCK_TYPES.includes(blockType);
}

export function isPaginatedTableBlock(block) {
  return Boolean(block) && typeof block === 'object' && !Array.isArray(block) && isPaginatedTableBlockType(block.block_type);
}

export function paginatedTableTotalUnit(blockType) {
  return PAGINATED_TABLE_TOTAL_UNITS[blockType] || '条';
}
