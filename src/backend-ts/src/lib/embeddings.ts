/**
 * Embedding service using Transformers.js with Qwen3-Embedding-0.6B-ONNX
 *
 * Provides local, serverless text embedding generation for semantic search.
 * Uses the Qwen3-Embedding-0.6B model optimized for multilingual text (Chinese + English).
 *
 * Key Features:
 * - Instruction-aware embeddings (query vs document mode)
 * - Automatic model download with progress tracking
 * - Normalized embeddings for cosine similarity
 * - Singleton pattern for efficient resource usage
 * - 1024-dimensional output vectors
 *
 * @module lib/embeddings
 */

import {
  pipeline,
  env,
  type FeatureExtractionPipeline,
} from "@huggingface/transformers";

// Configure Transformers.js environment
env.cacheDir = "./data/.cache/transformers"; // Store models in data directory
env.allowLocalModels = false; // Always download from HuggingFace
env.allowRemoteModels = true;

/**
 * Embedding instruction prefixes for different use cases
 * Based on Qwen3-Embedding model documentation
 */
const INSTRUCTIONS = {
  /** Use for search queries - optimized for retrieval */
  query: "Represent this sentence for searching relevant passages: ",
  /** Use for documents/passages to be indexed */
  document: "",
} as const;

type InstructionType = keyof typeof INSTRUCTIONS;

/**
 * Progress callback for model download
 * @param progress - Download progress information
 */
export type DownloadProgressCallback = (progress: {
  status: "progress" | "ready" | "done";
  file?: string;
  loaded?: number;
  total?: number;
  progress?: number;
}) => void;

/**
 * Qwen3-Embedding-0.6B service using Transformers.js
 *
 * Singleton service that manages the embedding pipeline.
 * First call triggers model download (~240MB ONNX quantized).
 *
 * @example
 * ```typescript
 * const embedder = await QwenEmbedding.getInstance();
 *
 * // Embed a search query
 * const queryEmbed = await embedder.embed("玩家在哪里?", "query");
 *
 * // Embed documents for indexing
 * const docEmbeds = await embedder.embedBatch([
 *   "地点描述...",
 *   "角色背景..."
 * ], "document");
 * ```
 */
export class QwenEmbedding {
  private static instance: QwenEmbedding | null = null;
  private pipeline: FeatureExtractionPipeline | null = null;
  private initPromise: Promise<void> | null = null;

  /**
   * Model identifier on HuggingFace
   * Uses ONNX-optimized quantized version for fast inference
   */
  private static readonly MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B-ONNX";

  /**
   * Expected embedding dimension
   */
  public static readonly EMBEDDING_DIM = 1024;

  private constructor() {
    // Private constructor for singleton pattern
  }

  /**
   * Get or create the singleton instance
   *
   * @param onProgress - Optional callback for download progress
   * @returns Promise resolving to the QwenEmbedding instance
   *
   * @example
   * ```typescript
   * const embedder = await QwenEmbedding.getInstance((progress) => {
   *   if (progress.status === "progress") {
   *     console.log(`Downloading ${progress.file}: ${progress.progress}%`);
   *   }
   * });
   * ```
   */
  public static async getInstance(
    onProgress?: DownloadProgressCallback
  ): Promise<QwenEmbedding> {
    if (!QwenEmbedding.instance) {
      QwenEmbedding.instance = new QwenEmbedding();
    }

    // Initialize pipeline if not already done
    if (!QwenEmbedding.instance.initPromise) {
      QwenEmbedding.instance.initPromise =
        QwenEmbedding.instance.initialize(onProgress);
    }

    await QwenEmbedding.instance.initPromise;
    return QwenEmbedding.instance;
  }

  /**
   * Initialize the embedding pipeline
   * Downloads model on first run (~240MB)
   *
   * @param onProgress - Optional callback for download progress
   */
  private async initialize(
    onProgress?: DownloadProgressCallback
  ): Promise<void> {
    if (this.pipeline) {
      return; // Already initialized
    }

    console.log(
      `[QwenEmbedding] Loading model: ${QwenEmbedding.MODEL_NAME}...`
    );

    // Create pipeline with progress tracking
    this.pipeline = await pipeline(
      "feature-extraction",
      QwenEmbedding.MODEL_NAME,
      {
        // Progress callback wrapper
        progress_callback: onProgress
          ? (progress: any) => {
              onProgress({
                status: progress.status as "progress" | "ready" | "done",
                file: progress.file || "",
                loaded: progress.loaded || 0,
                total: progress.total || 0,
                progress: progress.progress || 0,
              });
            }
          : undefined,
      }
    );

    console.log("[QwenEmbedding] Model loaded successfully");
  }

  /**
   * Generate embedding for a single text
   *
   * @param text - Text to embed
   * @param type - Instruction type ("query" for search, "document" for indexing)
   * @returns Promise resolving to normalized embedding vector (1024-dim)
   *
   * @example
   * ```typescript
   * const embedder = await QwenEmbedding.getInstance();
   * const embedding = await embedder.embed("Hello world", "document");
   * console.log(embedding.length); // 1024
   * ```
   */
  public async embed(
    text: string,
    type: InstructionType = "document"
  ): Promise<number[]> {
    if (!this.pipeline) {
      throw new Error("QwenEmbedding not initialized. Call getInstance() first.");
    }

    // Add instruction prefix based on type
    const instructedText = INSTRUCTIONS[type] + text;

    // Generate embedding
    const output = await this.pipeline(instructedText, {
      pooling: "mean", // Mean pooling over token embeddings
      normalize: true, // L2 normalization for cosine similarity
    });

    // Extract embedding array
    // Output shape: [1, 1024]
    const embedding = Array.from(output.data as Float32Array);

    return embedding;
  }

  /**
   * Generate embeddings for multiple texts in batch
   *
   * More efficient than calling embed() multiple times.
   *
   * @param texts - Array of texts to embed
   * @param type - Instruction type for all texts
   * @returns Promise resolving to array of embedding vectors
   *
   * @example
   * ```typescript
   * const embedder = await QwenEmbedding.getInstance();
   * const embeddings = await embedder.embedBatch([
   *   "Text 1",
   *   "Text 2",
   *   "Text 3"
   * ], "document");
   * console.log(embeddings.length); // 3
   * console.log(embeddings[0].length); // 1024
   * ```
   */
  public async embedBatch(
    texts: string[],
    type: InstructionType = "document"
  ): Promise<number[][]> {
    if (!this.pipeline) {
      throw new Error("QwenEmbedding not initialized. Call getInstance() first.");
    }

    if (texts.length === 0) {
      return [];
    }

    // Add instruction prefixes
    const instructedTexts = texts.map((text) => INSTRUCTIONS[type] + text);

    // Generate embeddings in batch
    const output = await this.pipeline(instructedTexts, {
      pooling: "mean",
      normalize: true,
    });

    // Extract embeddings
    // Output shape: [batch_size, 1024]
    const embeddings: number[][] = [];
    const data = Array.from(output.data as Float32Array);

    for (let i = 0; i < texts.length; i++) {
      const start = i * QwenEmbedding.EMBEDDING_DIM;
      const end = start + QwenEmbedding.EMBEDDING_DIM;
      embeddings.push(data.slice(start, end));
    }

    return embeddings;
  }

  /**
   * Cleanup resources and destroy singleton instance
   *
   * Useful for testing or when you need to force re-initialization.
   * In production, the singleton should persist for the application lifetime.
   */
  public static async cleanup(): Promise<void> {
    if (QwenEmbedding.instance) {
      QwenEmbedding.instance.pipeline = null;
      QwenEmbedding.instance.initPromise = null;
      QwenEmbedding.instance = null;
    }
  }
}

/**
 * Helper function to get embedding service instance
 *
 * Convenience wrapper around QwenEmbedding.getInstance()
 *
 * @param onProgress - Optional download progress callback
 * @returns Promise resolving to QwenEmbedding instance
 *
 * @example
 * ```typescript
 * const embedder = await getEmbeddingService();
 * const embedding = await embedder.embed("Hello", "query");
 * ```
 */
export async function getEmbeddingService(
  onProgress?: DownloadProgressCallback
): Promise<QwenEmbedding> {
  return QwenEmbedding.getInstance(onProgress);
}
