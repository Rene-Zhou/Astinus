import fs from 'node:fs';
import path from 'node:path';
import yaml from 'js-yaml';
import { SettingsConfigSchema, type SettingsConfig } from '../schemas/config.js';

export class ConfigService {
  private static instance: ConfigService;
  private config: SettingsConfig | null = null;
  private configPath: string;

  private constructor() {
    // Default path relative to src/backend-ts root
    // Assuming process.cwd() is src/backend-ts
    this.configPath = path.resolve(process.cwd(), '../../config/settings.yaml');
  }

  public static getInstance(): ConfigService {
    if (!ConfigService.instance) {
      ConfigService.instance = new ConfigService();
    }
    return ConfigService.instance;
  }

  public getConfigPath(): string {
    return this.configPath;
  }

  public async load(): Promise<SettingsConfig> {
    try {
      if (!fs.existsSync(this.configPath)) {
        throw new Error(`Config file not found at: ${this.configPath}`);
      }

      const fileContents = fs.readFileSync(this.configPath, 'utf8');
      const parsed = yaml.load(fileContents);
      
      const validationResult = SettingsConfigSchema.safeParse(parsed);

      if (!validationResult.success) {
        console.error('Config validation failed:', validationResult.error);
        throw new Error('Invalid configuration file format');
      }

      this.config = validationResult.data;
      
      // Auto-migrate legacy format if present and new format is empty
      if (this.config.llm && (!this.config.providers || this.config.providers.length === 0)) {
        this.migrateLegacyConfig();
      }

      return this.config;
    } catch (error) {
      console.error(`Failed to load config from ${this.configPath}:`, error);
      throw error;
    }
  }

  public get(): SettingsConfig {
    if (!this.config) {
      throw new Error('Config not loaded. Call load() first.');
    }
    return this.config;
  }

  public async save(newConfig: SettingsConfig): Promise<void> {
    const validationResult = SettingsConfigSchema.safeParse(newConfig);

    if (!validationResult.success) {
      throw new Error(`Invalid configuration: ${validationResult.error.message}`);
    }

    const yamlStr = yaml.dump(newConfig);
    fs.writeFileSync(this.configPath, yamlStr, 'utf8');
    this.config = validationResult.data;
  }

  private migrateLegacyConfig() {
    if (!this.config?.llm) return;

    // Basic migration logic could go here
    // For now, we'll just log that we are using legacy mode internally
    // or relying on the legacy config presence
    console.warn('Legacy LLM config detected. Migration logic placeholder.');
  }
}
