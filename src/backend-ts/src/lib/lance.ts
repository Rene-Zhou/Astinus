import * as lancedb from "@lancedb/lancedb";
import type { Connection, Table } from "@lancedb/lancedb";
import { getEmbeddingService, QwenEmbedding } from "./embeddings";

interface VectorRecord {
  id: string;
  text: string;
  vector: number[];
  metadata?: Record<string, string | number | boolean>;
  [key: string]: unknown; // Index signature for LanceDB compatibility
}

interface SearchResult {
  id: string;
  text: string;
  distance: number;
  metadata?: Record<string, string | number | boolean>;
}

// Metadata storage record (for table-level metadata like pack_hash)
interface MetadataRecord {
  key: string;
  value: string;
  [key: string]: unknown; // Index signature for LanceDB compatibility
}

export class LanceDBService {
  private static instance: LanceDBService | null = null;
  private connection: Connection | null = null;
  private embedder: QwenEmbedding | null = null;
  private initPromise: Promise<void> | null = null;

  private static readonly DB_PATH = "../../data/lancedb";

  private constructor() {}

  public static async getInstance(): Promise<LanceDBService> {
    if (!LanceDBService.instance) {
      LanceDBService.instance = new LanceDBService();
    }

    if (!LanceDBService.instance.initPromise) {
      LanceDBService.instance.initPromise =
        LanceDBService.instance.initialize();
    }

    await LanceDBService.instance.initPromise;
    return LanceDBService.instance;
  }

  private async initialize(): Promise<void> {
    if (this.connection) {
      return;
    }

    console.log(`[LanceDB] Connecting to database at ${LanceDBService.DB_PATH}`);
    this.connection = await lancedb.connect(LanceDBService.DB_PATH);

    console.log("[LanceDB] Loading embedding service...");
    this.embedder = await getEmbeddingService();

    console.log("[LanceDB] Service initialized");
  }

  public async getOrCreateTable(tableName: string): Promise<Table> {
    if (!this.connection) {
      throw new Error("LanceDB not initialized");
    }

    const tableNames = await this.connection.tableNames();

    if (tableNames.includes(tableName)) {
      return await this.connection.openTable(tableName);
    }

    const emptySchema: VectorRecord[] = [];
    return await this.connection.createTable({ name: tableName, data: emptySchema });
  }

  public async addDocuments(
    tableName: string,
    documents: string[],
    ids: string[],
    metadatas?: Record<string, string | number | boolean>[]
  ): Promise<void> {
    if (!this.embedder) {
      throw new Error("Embedder not initialized");
    }

    if (documents.length !== ids.length) {
      throw new Error("documents and ids arrays must have the same length");
    }

    if (metadatas && metadatas.length !== documents.length) {
      throw new Error("metadatas array must match documents length");
    }

    const embeddings = await this.embedder.embedBatch(documents, "document");

    const records: VectorRecord[] = documents.map((text, i) => ({
      id: ids[i]!,
      text,
      vector: embeddings[i]!,
      metadata: metadatas?.[i],
    }));

    const table = await this.getOrCreateTable(tableName);
    await table.add(records);
  }

  public async search(
    tableName: string,
    queryText: string,
    limit: number = 10,
    filter?: string
  ): Promise<SearchResult[]> {
    if (!this.embedder) {
      throw new Error("Embedder not initialized");
    }

    const table = await this.getOrCreateTable(tableName);

    const queryVector = await this.embedder.embed(queryText, "query");

    let query = table.search(queryVector).limit(limit);

    if (filter) {
      query = query.where(filter);
    }

    const results = await query.toArray();

    return results.map((row: any) => ({
      id: row.id as string,
      text: row.text as string,
      distance: row._distance as number,
      metadata: row.metadata as Record<string, string | number | boolean> | undefined,
    }));
  }

  public async deleteTable(tableName: string): Promise<void> {
    if (!this.connection) {
      throw new Error("LanceDB not initialized");
    }

    await this.connection.dropTable(tableName);
  }

  public async clearTable(tableName: string): Promise<void> {
    await this.deleteTable(tableName);
    await this.getOrCreateTable(tableName);
  }

  /**
   * Get metadata for a table (stored in a separate _metadata table).
   * Used for tracking pack hashes to avoid unnecessary re-indexing.
   *
   * @param tableName - The table to get metadata for
   * @param key - The metadata key to retrieve
   * @returns The metadata value, or null if not found
   */
  public async getTableMetadata(tableName: string, key: string): Promise<string | null> {
    if (!this.connection) {
      throw new Error("LanceDB not initialized");
    }

    const metadataTableName = `${tableName}_metadata`;
    const tableNames = await this.connection.tableNames();

    if (!tableNames.includes(metadataTableName)) {
      return null;
    }

    try {
      const table = await this.connection.openTable(metadataTableName);
      // LanceDB uses query().where() for filtering
      const results = await table.query().where(`key = '${key}'`).limit(1).toArray();

      if (results.length > 0) {
        return (results[0] as MetadataRecord).value;
      }
      return null;
    } catch (error) {
      console.error(`[LanceDB] Failed to get metadata for ${tableName}:`, error);
      return null;
    }
  }

  /**
   * Set metadata for a table (stored in a separate _metadata table).
   * Used for tracking pack hashes to avoid unnecessary re-indexing.
   *
   * @param tableName - The table to set metadata for
   * @param key - The metadata key
   * @param value - The metadata value
   */
  public async setTableMetadata(tableName: string, key: string, value: string): Promise<void> {
    if (!this.connection) {
      throw new Error("LanceDB not initialized");
    }

    const metadataTableName = `${tableName}_metadata`;
    const tableNames = await this.connection.tableNames();

    // If table exists, try to update or delete+recreate
    if (tableNames.includes(metadataTableName)) {
      try {
        // Delete existing table and recreate with new data
        await this.connection.dropTable(metadataTableName);
      } catch (error) {
        // Ignore error if table doesn't exist
      }
    }

    // Create metadata table with the new value
    const record: MetadataRecord = { key, value };
    await this.connection.createTable({
      name: metadataTableName,
      data: [record],
    });
  }

  /**
   * Check if a table exists.
   *
   * @param tableName - The table name to check
   * @returns True if the table exists
   */
  public async tableExists(tableName: string): Promise<boolean> {
    if (!this.connection) {
      throw new Error("LanceDB not initialized");
    }

    const tableNames = await this.connection.tableNames();
    return tableNames.includes(tableName);
  }

  public static async cleanup(): Promise<void> {
    if (LanceDBService.instance) {
      LanceDBService.instance.connection = null;
      LanceDBService.instance.embedder = null;
      LanceDBService.instance.initPromise = null;
      LanceDBService.instance = null;
    }
  }
}

export async function getVectorStoreService(): Promise<LanceDBService> {
  return LanceDBService.getInstance();
}
