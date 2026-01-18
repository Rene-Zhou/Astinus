import { vi } from 'vitest';

vi.mock('../src/lib/embeddings', () => ({
  getEmbeddingService: vi.fn().mockResolvedValue({
    embed: vi.fn().mockResolvedValue([0.1, 0.2, 0.3]),
    embedBatch: vi.fn().mockResolvedValue([[0.1, 0.2, 0.3]]),
  }),
}));

vi.mock('../src/lib/lance', () => ({
  getVectorStoreService: vi.fn().mockResolvedValue({
    search: vi.fn().mockResolvedValue([]),
    upsert: vi.fn().mockResolvedValue(undefined),
  }),
}));
