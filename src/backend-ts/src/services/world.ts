import { promises as fs } from 'fs';
import path from 'path';
import { WorldPackSchema } from '../schemas';
import type { WorldPack, LoreEntry, NPCData, LocationData, RegionData } from '../schemas';

export class WorldPackLoader {
  private packsDir: string;
  private loadedPacks: Map<string, WorldPack> = new Map();

  constructor(packsDir: string = './data/packs') {
    this.packsDir = packsDir;
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
    if (!location || !location.regionId) {
      return undefined;
    }
    return this.getRegion(pack, location.regionId);
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

      if (entry.applicableLocations.length > 0) {
        if (entry.applicableLocations.includes(locationId)) {
          matches.push(entry);
        }
        continue;
      }

      if (entry.applicableRegions.length > 0 && region) {
        if (entry.applicableRegions.includes(region.id)) {
          matches.push(entry);
        }
        continue;
      }

      if (entry.applicableLocations.length === 0 && entry.applicableRegions.length === 0) {
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

      if (includeSecondary && entry.secondaryKeys.length > 0) {
        const secondaryMatch = entry.secondaryKeys.some(
          (k) => keywordLower.includes(k.toLowerCase()) || k.toLowerCase().includes(keywordLower)
        );
        if (secondaryMatch) {
          matches.push(entry);
        }
      }
    }

    return matches.sort((a, b) => a.order - b.order);
  }
}
