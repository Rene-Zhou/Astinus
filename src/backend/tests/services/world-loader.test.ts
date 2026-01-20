import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WorldPackLoader } from '../../src/services/world';
import path from 'path';
import { promises as fs } from 'fs';

// Mock fs and path
vi.mock('fs', async () => {
  return {
    promises: {
      readFile: vi.fn(),
      readdir: vi.fn(),
      access: vi.fn(),
    },
  };
});

describe('WorldPackLoader', () => {
  let loader: WorldPackLoader;
  const mockPacksDir = '/mock/data/packs';

  beforeEach(() => {
    vi.clearAllMocks();
    loader = new WorldPackLoader(mockPacksDir);
  });

  describe('listAvailable', () => {
    it('should return list of available pack IDs', async () => {
      (fs.readdir as any).mockResolvedValue([
        { name: 'pack1.json', isFile: () => true },
        { name: 'pack2.json', isFile: () => true },
        { name: 'other.txt', isFile: () => true },
        { name: 'folder', isFile: () => false },
      ]);
      (fs.access as any).mockResolvedValue(undefined); // succeed

      const packs = await loader.listAvailable();
      expect(packs).toEqual(['pack1', 'pack2']);
    });

    it('should return empty list on error', async () => {
      (fs.readdir as any).mockRejectedValue(new Error('Read error'));
      const packs = await loader.listAvailable();
      expect(packs).toEqual([]);
    });
  });

  describe('load', () => {
    it('should load and validate a valid world pack', async () => {
      const validPack = {
        info: {
          name: { cn: 'Test World', en: 'Test World' },
          description: { cn: 'A test world', en: 'A test world' },
          version: '1.0.0',
          author: 'Tester',
        },
        locations: {},
        npcs: {},
        entries: {},
        regions: {},
      };

      (fs.readFile as any).mockResolvedValue(JSON.stringify(validPack));

      const pack = await loader.load('test_pack');
      expect(pack.info.name.cn).toBe('Test World');
      expect(fs.readFile).toHaveBeenCalledWith(path.join(mockPacksDir, 'test_pack.json'), 'utf-8');
    });

    it('should throw error for invalid pack structure', async () => {
      const invalidPack = {
        info: {
          // Missing name
          version: '1.0.0',
        },
      };

      (fs.readFile as any).mockResolvedValue(JSON.stringify(invalidPack));

      await expect(loader.load('invalid_pack')).rejects.toThrow();
    });

    it('should use cached pack if already loaded', async () => {
      const validPack = {
        info: {
          name: { cn: 'Test', en: 'Test' },
          description: { cn: 'Desc', en: 'Desc' },
          version: '1.0'
        },
        locations: {}, npcs: {}, entries: {}, regions: {}
      };
      (fs.readFile as any).mockResolvedValue(JSON.stringify(validPack));

      await loader.load('cached_pack');
      await loader.load('cached_pack');

      expect(fs.readFile).toHaveBeenCalledTimes(1);
    });
  });

  describe('Helper methods', () => {
    const mockPack: any = {
      entries: {
        '101': { uid: 101, key: ['Test'], constant: true, content: { cn: 'Const' } },
        '102': { uid: 102, key: ['Hidden'], constant: false, content: { cn: 'Secret' }, visibility: 'hidden' },
      },
      npcs: {
        'npc_1': { id: 'npc_1', name: 'NPC 1' }
      },
      locations: {
        'loc_1': { id: 'loc_1', region_id: 'reg_1' }
      },
      regions: {
        'reg_1': { id: 'reg_1', name: 'Region 1' }
      }
    };

    it('getEntry should return correct entry', () => {
      expect(loader.getEntry(mockPack, 101)).toBeDefined();
      expect(loader.getEntry(mockPack, 999)).toBeUndefined();
    });

    it('getConstantEntries should filter constant entries', () => {
      const consts = loader.getConstantEntries(mockPack);
      expect(consts).toHaveLength(1);
      expect(consts[0].uid).toBe(101);
    });

    it('getLocationRegion should resolve region from location', () => {
      const region = loader.getLocationRegion(mockPack, 'loc_1');
      expect(region?.id).toBe('reg_1');
    });
  });
});
