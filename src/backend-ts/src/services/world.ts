import { promises as fs } from 'fs';
import path from 'path';
import crypto from 'crypto';
import { WorldPackSchema } from '../schemas';
import type { WorldPack, LoreEntry, NPCData, LocationData, RegionData } from '../schemas';
import type { LanceDBService } from '../lib/lance';

export class WorldPackLoader {
  private packsDir: string;
  private loadedPacks: Map<string, WorldPack> = new Map();
  private vectorStore?: LanceDBService;

  constructor(packsDir: string = './data/packs', vectorStore?: LanceDBService) {
    this.packsDir = packsDir;
    this.vectorStore = vectorStore;
  }

  /**
   * Set the vector store service (can be set after construction).
   */
  setVectorStore(vectorStore: LanceDBService): void {
    this.vectorStore = vectorStore;
  }

  async load(packId: string): Promise<WorldPack> {
    if (this.loadedPacks.has(packId)) {
      return this.loadedPacks.get(packId)!;
    }

    const packPath = path.join(this.packsDir, `${packId}.json`);
    
    try {
      const content = await fs.readFile(packPath, 'utf-8');
      const rawData = JSON.parse(content);
      console.log(`[WorldPackLoader] Parsing pack: ${packId}`);
      const worldPack = WorldPackSchema.parse(rawData);
      console.log(`[WorldPackLoader] Pack validated successfully`);

      this.loadedPacks.set(packId, worldPack);

      // Fire-and-forget async indexing (non-blocking)
      if (this.vectorStore) {
        this.indexLoreEntriesAsync(packId, worldPack).catch((error) => {
          console.error(`[WorldPackLoader] Async indexing failed for ${packId}:`, error);
        });
      }

      return worldPack;
    } catch (error) {
      console.error(`[WorldPackLoader] Error loading pack "${packId}":`, error);
      if (error instanceof Error) {
        throw new Error(`Failed to load world pack "${packId}": ${error.message}`);
      }
      throw error;
    }
  }

  async listAvailable(): Promise<string[]> {
    try {
      const entries = await fs.readdir(this.packsDir, { withFileTypes: true });
      const packIds: string[] = [];

      for (const entry of entries) {
        if (entry.isFile() && entry.name.endsWith('.json')) {
          const packPath = path.join(this.packsDir, entry.name);
          try {
            await fs.access(packPath);
            const packId = entry.name.replace(/\.json$/, '');
            packIds.push(packId);
          } catch {
            continue;
          }
        }
      }

      return packIds;
    } catch {
      return [];
    }
  }

  getEntry(pack: WorldPack, uid: number): LoreEntry | undefined {
    return pack.entries[uid.toString()];
  }

  getNPC(pack: WorldPack, npcId: string): NPCData | undefined {
    return pack.npcs[npcId];
  }

  getLocation(pack: WorldPack, locationId: string): LocationData | undefined {
    return pack.locations[locationId];
  }

  getRegion(pack: WorldPack, regionId: string): RegionData | undefined {
    return pack.regions[regionId];
  }

  getLocationRegion(pack: WorldPack, locationId: string): RegionData | undefined {
    const location = this.getLocation(pack, locationId);
    if (!location || !location.region_id) {
      return undefined;
    }
    return this.getRegion(pack, location.region_id);
  }

  getConstantEntries(pack: WorldPack): LoreEntry[] {
    return Object.values(pack.entries).filter((e) => e.constant);
  }

  getLoreForLocation(
    pack: WorldPack,
    locationId: string,
    visibility: string = 'basic'
  ): LoreEntry[] {
    const region = this.getLocationRegion(pack, locationId);

    const matches: LoreEntry[] = [];

    for (const entry of Object.values(pack.entries)) {
      if (entry.visibility !== visibility && !entry.constant) {
        continue;
      }

      if (entry.constant) {
        matches.push(entry);
        continue;
      }

      if (entry.applicable_locations.length > 0) {
        if (entry.applicable_locations.includes(locationId)) {
          matches.push(entry);
        }
        continue;
      }

      if (entry.applicable_regions.length > 0 && region) {
        if (entry.applicable_regions.includes(region.id)) {
          matches.push(entry);
        }
        continue;
      }

      if (entry.applicable_locations.length === 0 && entry.applicable_regions.length === 0) {
        matches.push(entry);
      }
    }

    return matches.sort((a, b) => a.order - b.order);
  }

  searchEntriesByKeyword(
    pack: WorldPack,
    keyword: string,
    includeSecondary: boolean = true
  ): LoreEntry[] {
    const matches: LoreEntry[] = [];
    const keywordLower = keyword.toLowerCase();

    for (const entry of Object.values(pack.entries)) {
      const keyMatch = entry.key.some(
        (k) => keywordLower.includes(k.toLowerCase()) || k.toLowerCase().includes(keywordLower)
      );

      if (keyMatch) {
        matches.push(entry);
        continue;
      }

      if (includeSecondary && entry.secondary_keys.length > 0) {
        const secondaryMatch = entry.secondary_keys.some(
          (k) => keywordLower.includes(k.toLowerCase()) || k.toLowerCase().includes(keywordLower)
        );
        if (secondaryMatch) {
          matches.push(entry);
        }
      }
    }

    return matches.sort((a, b) => a.order - b.order);
  }

  // ============================================================
  // Lore Auto-Indexing (Phase 1.1 & 1.2)
  // ============================================================

  /**
   * Compute SHA-256 hash of world pack entries for change detection.
   * Only hashes the lore entries (content, keys, metadata) since that's what we index.
   *
   * @param pack - WorldPack to hash
   * @returns SHA-256 hash string (hex)
   */
  private computePackHash(pack: WorldPack): string {
    const entriesData = Object.values(pack.entries)
      .map((entry) => ({
        uid: entry.uid,
        key: entry.key,
        secondary_keys: entry.secondary_keys,
        content: entry.content,
        order: entry.order,
        constant: entry.constant,
        visibility: entry.visibility,
        applicable_regions: entry.applicable_regions,
        applicable_locations: entry.applicable_locations,
      }))
      .sort((a, b) => a.uid - b.uid);

    const hashInput = JSON.stringify(entriesData);
    return crypto.createHash('sha256').update(hashInput).digest('hex');
  }

  /**
   * Async index lore entries for vector search.
   * Uses hash-based change detection to skip unnecessary re-indexing.
   *
   * Creates separate documents for Chinese and English versions of each entry,
   * with metadata for filtering (visibility, applicable_regions, applicable_locations).
   *
   * @param packId - World pack identifier
   * @param pack - Loaded WorldPack
   */
  async indexLoreEntriesAsync(packId: string, pack: WorldPack): Promise<void> {
    if (!this.vectorStore) {
      console.log(`[WorldPackLoader] No vector store, skipping indexing for ${packId}`);
      return;
    }

    if (!pack.entries || Object.keys(pack.entries).length === 0) {
      console.log(`[WorldPackLoader] No entries in pack ${packId}, skipping indexing`);
      return;
    }

    const collectionName = `lore_entries_${packId}`;
    const currentHash = this.computePackHash(pack);

    // Check if re-indexing is needed
    const storedHash = await this.vectorStore.getTableMetadata(collectionName, 'pack_hash');

    if (storedHash === currentHash) {
      console.log(`[WorldPackLoader] Index up-to-date for ${packId} (hash: ${currentHash.slice(0, 8)}...)`);
      return;
    }

    if (storedHash === null) {
      console.log(`[WorldPackLoader] First-time indexing for ${packId} (${Object.keys(pack.entries).length} entries)`);
    } else {
      console.log(`[WorldPackLoader] Pack changed, re-indexing ${packId} (hash: ${currentHash.slice(0, 8)}...)`);
    }

    // Prepare for re-indexing - delete old table if exists
    const tableExists = await this.vectorStore.tableExists(collectionName);
    if (tableExists) {
      try {
        await this.vectorStore.deleteTable(collectionName);
      } catch (error) {
        // Ignore error if table doesn't exist
      }
    }

    // Prepare documents and metadata
    const documents: string[] = [];
    const ids: string[] = [];
    const metadatas: Record<string, string | number | boolean>[] = [];

    for (const entry of Object.values(pack.entries)) {
      // Chinese document
      if (entry.content.cn) {
        documents.push(entry.content.cn);
        ids.push(`${entry.uid}`);  // Use uid as id for easy lookup
        metadatas.push({
          uid: entry.uid,
          keys: entry.key.join(','),
          order: entry.order,
          lang: 'cn',
          constant: entry.constant,
          visibility: entry.visibility,
          applicable_regions: entry.applicable_regions.join(','),
          applicable_locations: entry.applicable_locations.join(','),
        });
      }

      // English document (with different id suffix to avoid collision)
      if (entry.content.en) {
        documents.push(entry.content.en);
        ids.push(`${entry.uid}_en`);
        metadatas.push({
          uid: entry.uid,
          keys: entry.key.join(','),
          order: entry.order,
          lang: 'en',
          constant: entry.constant,
          visibility: entry.visibility,
          applicable_regions: entry.applicable_regions.join(','),
          applicable_locations: entry.applicable_locations.join(','),
        });
      }
    }

    // Add documents to vector store
    try {
      await this.vectorStore.addDocuments(collectionName, documents, ids, metadatas);

      // Store the hash for future change detection
      await this.vectorStore.setTableMetadata(collectionName, 'pack_hash', currentHash);

      console.log(`[WorldPackLoader] ✅ Indexed ${documents.length} documents for ${packId}`);
    } catch (error) {
      console.error(`[WorldPackLoader] ❌ Failed to index ${packId}:`, error);
      throw error;
    }
  }
}
