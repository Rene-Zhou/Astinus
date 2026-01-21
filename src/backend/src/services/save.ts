import { eq, desc } from 'drizzle-orm';
import { db, schema } from '../db';
import type { GameState } from '../schemas';
import { GameStateSchema } from '../schemas';

const MAX_SAVE_SLOTS = 10;

export interface SaveSlotPreview {
  id: number;
  sessionId: string;
  slotName: string;
  description: string | null;
  worldPackId: string;
  currentLocation: string;
  turnCount: number;
  playerName: string;
  characterName: string;
  lastMessage: string | null;
  isAutoSave: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateSaveRequest {
  slotName: string;
  description?: string;
  isAutoSave?: boolean;
  overwrite?: boolean;
}

export interface CreateSaveResult {
  success: boolean;
  save?: SaveSlotPreview;
  exists?: boolean;
  existingId?: number;
  error?: string;
}

export interface LoadSaveResult {
  success: boolean;
  gameState?: GameState;
  error?: string;
}

export class SaveService {
  private static instance: SaveService | null = null;

  private constructor() {}

  public static getInstance(): SaveService {
    if (!SaveService.instance) {
      SaveService.instance = new SaveService();
    }
    return SaveService.instance;
  }

  private async ensureGameSessionExists(gameState: GameState): Promise<void> {
    const existing = await db
      .select()
      .from(schema.gameSessions)
      .where(eq(schema.gameSessions.sessionId, gameState.session_id))
      .limit(1);

    if (existing.length === 0) {
      await db.insert(schema.gameSessions).values({
        sessionId: gameState.session_id,
        worldPackId: gameState.world_pack_id,
        playerName: gameState.player_name,
        playerDataJson: JSON.stringify(gameState.player),
        currentLocation: gameState.current_location,
        currentPhase: gameState.current_phase,
        turnCount: gameState.turn_count,
        activeNpcIdsJson: JSON.stringify(gameState.active_npc_ids),
      });
    } else {
      await db
        .update(schema.gameSessions)
        .set({
          currentLocation: gameState.current_location,
          currentPhase: gameState.current_phase,
          turnCount: gameState.turn_count,
          activeNpcIdsJson: JSON.stringify(gameState.active_npc_ids),
          updatedAt: new Date(),
        })
        .where(eq(schema.gameSessions.sessionId, gameState.session_id));
    }
  }

  public async listSaves(): Promise<SaveSlotPreview[]> {
    const saves = await db
      .select()
      .from(schema.saveSlots)
      .orderBy(desc(schema.saveSlots.updatedAt));

    return saves.map((save) => this.toPreview(save));
  }

  public async getSaveCount(): Promise<number> {
    const result = await db.select().from(schema.saveSlots);
    return result.length;
  }

  public async findByName(slotName: string): Promise<SaveSlotPreview | null> {
    const results = await db
      .select()
      .from(schema.saveSlots)
      .where(eq(schema.saveSlots.slotName, slotName))
      .limit(1);

    if (results.length === 0) {
      return null;
    }

    return this.toPreview(results[0]!);
  }

  public async findById(id: number): Promise<SaveSlotPreview | null> {
    const results = await db
      .select()
      .from(schema.saveSlots)
      .where(eq(schema.saveSlots.id, id))
      .limit(1);

    if (results.length === 0) {
      return null;
    }

    return this.toPreview(results[0]!);
  }

  public async createSave(
    gameState: GameState,
    request: CreateSaveRequest
  ): Promise<CreateSaveResult> {
    const count = await this.getSaveCount();
    if (count >= MAX_SAVE_SLOTS && !request.overwrite) {
      return {
        success: false,
        error: `Save limit reached (${MAX_SAVE_SLOTS}). Delete old saves or overwrite existing ones.`,
      };
    }

    const existing = await this.findByName(request.slotName);
    if (existing && !request.overwrite) {
      return {
        success: false,
        exists: true,
        existingId: existing.id,
        error: `Save "${request.slotName}" already exists.`,
      };
    }

    if (existing && request.overwrite) {
      await this.deleteSave(existing.id);
    }

    await this.ensureGameSessionExists(gameState);

    const gameStateJson = JSON.stringify(gameState);

    const result = await db
      .insert(schema.saveSlots)
      .values({
        sessionId: gameState.session_id,
        slotName: request.slotName,
        gameStateJson: gameStateJson,
        description: request.description || null,
        isAutoSave: request.isAutoSave || false,
      })
      .returning();

    if (result.length === 0) {
      return {
        success: false,
        error: 'Failed to create save slot.',
      };
    }

    return {
      success: true,
      save: this.toPreview(result[0]!),
    };
  }

  public async loadSave(id: number): Promise<LoadSaveResult> {
    const results = await db
      .select()
      .from(schema.saveSlots)
      .where(eq(schema.saveSlots.id, id))
      .limit(1);

    if (results.length === 0) {
      return {
        success: false,
        error: `Save slot with ID ${id} not found.`,
      };
    }

    const save = results[0]!;

    try {
      const rawGameState = JSON.parse(save.gameStateJson);
      const gameState = GameStateSchema.parse(rawGameState);

      return {
        success: true,
        gameState,
      };
    } catch (error) {
      console.error('[SaveService] Failed to parse save:', error);
      return {
        success: false,
        error: `Failed to parse save data: ${error}`,
      };
    }
  }

  public async deleteSave(id: number): Promise<boolean> {
    const result = await db.delete(schema.saveSlots).where(eq(schema.saveSlots.id, id)).returning();

    return result.length > 0;
  }

  private toPreview(save: typeof schema.saveSlots.$inferSelect): SaveSlotPreview {
    let worldPackId = '';
    let currentLocation = '';
    let turnCount = 0;
    let playerName = '';
    let characterName = '';
    let lastMessage: string | null = null;

    try {
      const gameState = JSON.parse(save.gameStateJson) as GameState;
      worldPackId = gameState.world_pack_id;
      currentLocation = gameState.current_location;
      turnCount = gameState.turn_count;
      playerName = gameState.player_name;
      characterName = gameState.player?.name || '';

      if (gameState.messages && gameState.messages.length > 0) {
        const last = gameState.messages[gameState.messages.length - 1];
        if (last) {
          lastMessage =
            last.content.length > 100 ? last.content.substring(0, 100) + '...' : last.content;
        }
      }
    } catch {
      // parsing failed, use defaults
    }

    return {
      id: save.id,
      sessionId: save.sessionId,
      slotName: save.slotName,
      description: save.description,
      worldPackId,
      currentLocation,
      turnCount,
      playerName,
      characterName,
      lastMessage,
      isAutoSave: save.isAutoSave,
      createdAt: save.createdAt,
      updatedAt: save.updatedAt,
    };
  }
}

export function getSaveService(): SaveService {
  return SaveService.getInstance();
}
