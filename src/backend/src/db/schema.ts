import { integer, sqliteTable, text } from 'drizzle-orm/sqlite-core';
import { sql } from 'drizzle-orm';

export const gameSessions = sqliteTable('game_sessions', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  sessionId: text('session_id', { length: 64 }).notNull().unique(),
  worldPackId: text('world_pack_id', { length: 64 }).notNull(),
  playerName: text('player_name', { length: 128 }).notNull(),
  playerDataJson: text('player_data_json'),
  currentLocation: text('current_location', { length: 256 }).default(''),
  currentPhase: text('current_phase', { length: 32 }).default('waiting_input'),
  turnCount: integer('turn_count').default(0).notNull(),
  activeNpcIdsJson: text('active_npc_ids_json'),
  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(strftime('%s', 'now'))`)
    .notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' })
    .default(sql`(strftime('%s', 'now'))`)
    .notNull(),
});

export const messages = sqliteTable('messages', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  sessionId: text('session_id', { length: 64 })
    .notNull()
    .references(() => gameSessions.sessionId, { onDelete: 'cascade' }),
  role: text('role', { length: 32 }).notNull(),
  content: text('content').notNull(),
  turn: integer('turn').default(0).notNull(),
  extraDataJson: text('extra_data_json'),
  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(strftime('%s', 'now'))`)
    .notNull(),
});

export const saveSlots = sqliteTable('save_slots', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  sessionId: text('session_id', { length: 64 })
    .notNull()
    .references(() => gameSessions.sessionId, { onDelete: 'cascade' }),
  slotName: text('slot_name', { length: 128 }).notNull(),
  gameStateJson: text('game_state_json').notNull(),
  description: text('description', { length: 512 }),
  isAutoSave: integer('is_auto_save', { mode: 'boolean' }).default(false).notNull(),
  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(strftime('%s', 'now'))`)
    .notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' })
    .default(sql`(strftime('%s', 'now'))`)
    .notNull(),
});

export type GameSession = typeof gameSessions.$inferSelect;
export type NewGameSession = typeof gameSessions.$inferInsert;
export type Message = typeof messages.$inferSelect;
export type NewMessage = typeof messages.$inferInsert;
export type SaveSlot = typeof saveSlots.$inferSelect;
export type NewSaveSlot = typeof saveSlots.$inferInsert;
