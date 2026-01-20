import Database from 'better-sqlite3';
import { drizzle, BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import * as schema from './schema';

const dbPath = process.env.DATABASE_PATH || '../../data/astinus.db';

const sqlite = new Database(dbPath);
sqlite.pragma('journal_mode = WAL');
sqlite.pragma('synchronous = NORMAL');
sqlite.pragma('cache_size = -64000');
sqlite.pragma('temp_store = MEMORY');

export const db: BetterSQLite3Database<typeof schema> = drizzle(sqlite, { schema });

export { schema };
