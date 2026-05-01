export const PAGINATED_TABLE_BLOCK_TYPES: readonly ['list_table', 'group_table'];

export const PAGINATED_TABLE_TOTAL_UNITS: Readonly<{
  list_table: '条';
  group_table: '组';
}>;

export function isPaginatedTableBlockType(blockType: unknown): blockType is 'list_table' | 'group_table';

export function isPaginatedTableBlock(
  block: unknown,
): block is {
  block_type: 'list_table' | 'group_table';
};

export function paginatedTableTotalUnit(blockType: unknown): string;
