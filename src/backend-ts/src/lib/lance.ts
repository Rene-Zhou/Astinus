import lancedb, { type Connection, type Table } from "vectordb";
import { getEmbeddingService, QwenEmbedding } from "./embeddings";

interface VectorRecord {
  id: string;
  text: string;
  vector: number[];
  metadata?: Record<string, string | number | boolean>;
}

interface SearchResult {
  id: string;
  text: string;
  distance: number;
  metadata?: Record<string, string | number | boolean>;
}

export class LanceDBService {
  private static instance: LanceDBService | null = null;
  private connection: Connection | null = null;
  private embedder: QwenEmbedding | null = null;
  private initPromise: Promise<void> | null = null;

  private static readonly DB_PATH = "./data/lancedb";

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
    return await this.connection.createTable(tableName, emptySchema);
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
      id: ids[i],
      text,
      vector: embeddings[i],
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

    const results = await query.execute();

    return results.map((row) => ({
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
