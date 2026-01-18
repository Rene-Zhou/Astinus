import { LanceDBService } from "../lib/lance";
import { WorldPackLoader } from "./world";
import type { LoreEntry, WorldPack } from "../schemas";

const KEYWORD_MATCH_WEIGHT = 2.0;
const KEYWORD_SECONDARY_WEIGHT = 1.0;
const VECTOR_MATCH_WEIGHT = 0.8;
const DUAL_MATCH_BOOST = 1.5;

interface EntryScore {
  entry: LoreEntry;
  score: number;
  keywordMatch: boolean;
  vectorMatch: boolean;
}

export class LoreService {
  constructor(
    private worldPackLoader: WorldPackLoader,
    private vectorStore?: LanceDBService
  ) {}

  async search(params: {
    query: string;
    context?: string;
    worldPackId?: string;
    currentLocation?: string;
    currentRegion?: string;
    lang?: "cn" | "en";
  }): Promise<string> {
    const {
      query,
      context = "",
      worldPackId = "demo_pack",
      currentLocation,
      currentRegion,
      lang = "cn",
    } = params;

    if (!query) {
      return lang === "cn" ? "未提供查询内容。" : "No query provided.";
    }

    try {
      const worldPack = await this.worldPackLoader.load(worldPackId);

      const loreEntries = await this.searchLore(
        worldPack,
        query,
        context,
        worldPackId,
        currentLocation,
        currentRegion
      );

      return this.formatLore(loreEntries, query, context, lang);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return lang === "cn"
        ? `检索背景信息时出错: ${message}`
        : `Error retrieving lore: ${message}`;
    }
  }

  private async searchLore(
    worldPack: WorldPack,
    query: string,
    _context: string,
    worldPackId: string,
    currentLocation?: string,
    currentRegion?: string
  ): Promise<LoreEntry[]> {
    const constantEntries = this.getConstantEntries(worldPack);

    if (!this.vectorStore) {
      return this.keywordOnlySearch(
        worldPack,
        query,
        constantEntries,
        currentLocation,
        currentRegion
      );
    }

    const entryScores = new Map<string, EntryScore>();

    const searchTerms = this.extractSearchTerms(query);
    const keywordMatchedUids = new Set<number>();

    for (const term of searchTerms) {
      const primaryMatches = this.searchEntriesByKeyword(
        worldPack,
        term,
        false
      );
      for (const entry of primaryMatches) {
        keywordMatchedUids.add(entry.uid);
        if (!entryScores.has(String(entry.uid))) {
          entryScores.set(String(entry.uid), {
            entry,
            score: KEYWORD_MATCH_WEIGHT,
            keywordMatch: true,
            vectorMatch: false,
          });
        }
      }

      const secondaryMatches = this.searchEntriesByKeyword(
        worldPack,
        term,
        true
      );
      for (const entry of secondaryMatches) {
        if (keywordMatchedUids.has(entry.uid)) {
          continue;
        }
        keywordMatchedUids.add(entry.uid);
        if (!entryScores.has(String(entry.uid))) {
          entryScores.set(String(entry.uid), {
            entry,
            score: KEYWORD_SECONDARY_WEIGHT,
            keywordMatch: true,
            vectorMatch: false,
          });
        }
      }
    }

    try {
      const searchLang = this.detectLanguage(query);
      const collectionName = `lore_entries_${worldPackId}`;

      const results = await this.vectorStore.search(
        collectionName,
        query,
        10,
        `lang = "${searchLang}"`
      );

      for (const result of results) {
        const uid = parseInt(result.id, 10);
        const distance = result.distance;
        const similarity = 1.0 - distance;
        const vectorScore = VECTOR_MATCH_WEIGHT * similarity;

        const existingScore = entryScores.get(String(uid));
        if (existingScore) {
          existingScore.score *= DUAL_MATCH_BOOST;
          existingScore.vectorMatch = true;
        } else {
          const entry = this.getEntry(worldPack, uid);
          if (entry) {
            entryScores.set(String(uid), {
              entry,
              score: vectorScore,
              keywordMatch: false,
              vectorMatch: true,
            });
          }
        }
      }
    } catch (error) {
      console.error("[LoreService] Vector search failed:", error);
    }

    for (const entry of constantEntries) {
      if (!entryScores.has(String(entry.uid))) {
        entryScores.set(String(entry.uid), {
          entry,
          score: 2.0,
          keywordMatch: false,
          vectorMatch: false,
        });
      }
    }

    const filtered = this.filterByLocation(
      Array.from(entryScores.values()),
      currentLocation,
      currentRegion
    );

    const sorted = filtered.sort((a, b) => {
      if (a.score !== b.score) {
        return b.score - a.score;
      }
      return a.entry.order - b.entry.order;
    });

    return sorted.slice(0, 5).map((item) => item.entry);
  }

  private filterByLocation(
    entryScores: EntryScore[],
    currentLocation?: string,
    currentRegion?: string
  ): EntryScore[] {
    return entryScores.filter((item) => {
      const { entry } = item;

      if (entry.visibility !== "basic" && !entry.constant) {
        return false;
      }

      if (
        entry.applicable_locations &&
        entry.applicable_locations.length > 0 &&
        (!currentLocation ||
          !entry.applicable_locations.includes(currentLocation))
      ) {
        return false;
      }

      if (
        entry.applicable_regions &&
        entry.applicable_regions.length > 0 &&
        (!currentRegion || !entry.applicable_regions.includes(currentRegion))
      ) {
        return false;
      }

      return true;
    });
  }

  private keywordOnlySearch(
    worldPack: WorldPack,
    query: string,
    constantEntries: LoreEntry[],
    currentLocation?: string,
    currentRegion?: string
  ): LoreEntry[] {
    const searchTerms = this.extractSearchTerms(query);
    const matchedEntries: LoreEntry[] = [];

    for (const term of searchTerms) {
      const matches = this.searchEntriesByKeyword(worldPack, term, true);
      matchedEntries.push(...matches);
    }

    const uniqueEntries = new Map<string, LoreEntry>();
    for (const entry of [...constantEntries, ...matchedEntries]) {
      uniqueEntries.set(String(entry.uid), entry);
    }

    const filtered = Array.from(uniqueEntries.values()).filter((entry) => {
      if (entry.visibility !== "basic" && !entry.constant) {
        return false;
      }

      if (
        entry.applicable_locations &&
        entry.applicable_locations.length > 0 &&
        (!currentLocation ||
          !entry.applicable_locations.includes(currentLocation))
      ) {
        return false;
      }

      if (
        entry.applicable_regions &&
        entry.applicable_regions.length > 0 &&
        (!currentRegion || !entry.applicable_regions.includes(currentRegion))
      ) {
        return false;
      }

      return true;
    });

    return filtered.sort((a, b) => a.order - b.order);
  }

  private extractSearchTerms(query: string): string[] {
    const stopWords = new Set([
      "的",
      "了",
      "是",
      "在",
      "我",
      "你",
      "他",
      "她",
      "它",
      "有",
      "没有",
      "什么",
      "怎么",
      "如何",
      "这",
      "那",
      "就",
      "也",
      "都",
      "很",
      "非常",
      "a",
      "an",
      "the",
      "is",
      "are",
      "was",
      "were",
      "be",
      "been",
      "being",
      "have",
      "has",
      "had",
      "do",
      "does",
      "did",
      "will",
      "would",
      "should",
    ]);

    const segmenter = new Intl.Segmenter(["zh-CN", "en"], {
      granularity: "word",
    });
    const segments = segmenter.segment(query);

    const terms: string[] = [];
    const seen = new Set<string>();

    for (const { segment } of segments) {
      const cleanWord = segment
        .trim()
        .replace(/[，。！？：；''()（）\[\]【】""]/g, "");

      if (
        cleanWord &&
        !stopWords.has(cleanWord) &&
        cleanWord.length > 1 &&
        cleanWord.trim().length > 0 &&
        !seen.has(cleanWord)
      ) {
        seen.add(cleanWord);
        terms.push(cleanWord);
        if (terms.length >= 5) {
          break;
        }
      }
    }

    return terms;
  }

  private formatLore(
    entries: LoreEntry[],
    query: string,
    _context: string,
    lang: "cn" | "en"
  ): string {
    if (entries.length === 0) {
      return lang === "cn"
        ? `没有找到与'${query}'相关的背景信息。`
        : `No background information found related to '${query}'.`;
    }

    const formattedParts = entries.map((entry) => {
      const content = entry.content[lang] || entry.content.en || "";

      if (entry.key && entry.key.length > 0) {
        const keyStr = entry.key.join(" / ");
        return `[${keyStr}]\n${content}`;
      }

      return content;
    });

    const loreText = formattedParts.join("\n\n");

    const header =
      lang === "cn"
        ? `与'${query}'相关的背景信息：\n`
        : `Background information related to '${query}':\n`;

    return header + loreText;
  }

  private getConstantEntries(worldPack: WorldPack): LoreEntry[] {
    return Object.values(worldPack.entries).filter((entry: any) => entry.constant);
  }

  private searchEntriesByKeyword(
    worldPack: WorldPack,
    keyword: string,
    includeSecondary: boolean
  ): LoreEntry[] {
    return Object.values(worldPack.entries).filter((entry: any) => {
      const primaryMatch = entry.key.some((k: any) =>
        k.toLowerCase().includes(keyword.toLowerCase())
      );

      if (primaryMatch) {
        return true;
      }

      if (includeSecondary && entry.secondary_keys) {
        return entry.secondary_keys.some((k: any) =>
          k.toLowerCase().includes(keyword.toLowerCase())
        );
      }

      return false;
    });
  }

  private getEntry(worldPack: WorldPack, uid: number): LoreEntry | undefined {
    return Object.values(worldPack.entries).find((entry: any) => entry.uid === uid);
  }

  private detectLanguage(text: string): "cn" | "en" {
    for (const char of text) {
      if (char >= "\u4e00" && char <= "\u9fff") {
        return "cn";
      }
    }
    return "en";
  }
}

export async function getLoreService(
  worldPackLoader: WorldPackLoader,
  vectorStore?: LanceDBService
): Promise<LoreService> {
  return new LoreService(worldPackLoader, vectorStore);
}
