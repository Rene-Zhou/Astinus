/**
 * Location Context Service for building hierarchical location-based context.
 * 
 * Ported from src/backend/services/location_context.py
 * 
 * This service aggregates region + location context, filters lore by location/region/visibility,
 * and manages discovery state transitions.
 */

import { WorldPackLoader } from "./world";
import { getLocalizedString } from "../schemas";

export interface HierarchicalContext {
  region: {
    id: string;
    name: string;
    narrative_tone: string;
    atmosphere_keywords: string[];
  };
  location: {
    id: string;
    name: string;
    description: string;
    atmosphere: string;
    visible_items: string[];
    hidden_items_revealed: string[];
    hidden_items_remaining: string[];
  };
  basic_lore: string[];
  atmosphere_guidance: string;
}

export class LocationContextService {
  constructor(private worldPackLoader: WorldPackLoader) {}

  /**
   * Build complete hierarchical context for a location.
   */
  public async getContextForLocation(
    worldPackId: string,
    locationId: string,
    discoveredItems: string[],
    lang: "cn" | "en" = "cn"
  ): Promise<HierarchicalContext> {
    const pack = await this.worldPackLoader.load(worldPackId);
    
    // Get location
    const location = pack.locations[locationId];
    if (!location) {
      return this.emptyContext();
    }

    // Get region
    let region = location.region_id ? pack.regions[location.region_id] : undefined;
    if (!region && pack.regions) {
      // Try to get global region
      region = pack.regions["_global"];
    }

    // Build region context
    const regionContext = {
      id: region ? region.id : "_global",
      name: region 
        ? getLocalizedString(region.name, lang)
        : (lang === "cn" ? "全局区域" : "Global Region"),
      narrative_tone: region && region.narrative_tone
        ? getLocalizedString(region.narrative_tone, lang)
        : "",
      atmosphere_keywords: region ? region.atmosphere_keywords : [],
    };

    // Determine hidden items state
    const hiddenItems = location.hidden_items || [];
    const hiddenItemsRevealed = hiddenItems.filter(item => discoveredItems.includes(item));
    const hiddenItemsRemaining = hiddenItems.filter(item => !discoveredItems.includes(item));

    // Build location context
    const locationContext = {
      id: location.id,
      name: getLocalizedString(location.name, lang),
      description: getLocalizedString(location.description, lang),
      atmosphere: location.atmosphere 
        ? getLocalizedString(location.atmosphere, lang) 
        : "",
      visible_items: location.visible_items || location.items || [],
      hidden_items_revealed: hiddenItemsRevealed,
      hidden_items_remaining: hiddenItemsRemaining,
    };

    // Get basic lore
    // Manual iteration is required as getLoreForLocation is not available on WorldPack type
    const basicLoreEntries: string[] = [];
    if (pack.entries) {
      for (const entry of Object.values(pack.entries)) {
        if (entry.visibility !== "basic") continue;
        
        const isApplicableLoc = entry.applicable_locations?.includes(locationId);
        const isApplicableRegion = region && entry.applicable_regions?.includes(region.id);
        
        if (isApplicableLoc || isApplicableRegion) {
          basicLoreEntries.push(getLocalizedString(entry.content, lang));
        }
      }
    }

    const atmosphereGuidance = this.buildAtmosphereGuidance(
      regionContext,
      locationContext,
      lang
    );

    return {
      region: regionContext,
      location: locationContext,
      basic_lore: basicLoreEntries,
      atmosphere_guidance: atmosphereGuidance,
    };
  }

  private emptyContext(): HierarchicalContext {
    return {
      region: {
        id: "_global",
        name: "Unknown",
        narrative_tone: "",
        atmosphere_keywords: [],
      },
      location: {
        id: "",
        name: "Unknown",
        description: "",
        atmosphere: "",
        visible_items: [],
        hidden_items_revealed: [],
        hidden_items_remaining: [],
      },
      basic_lore: [],
      atmosphere_guidance: "",
    };
  }

  private buildAtmosphereGuidance(
    regionContext: HierarchicalContext["region"],
    locationContext: HierarchicalContext["location"],
    lang: "cn" | "en"
  ): string {
    const parts: string[] = [];

    if (regionContext.narrative_tone) {
      parts.push(regionContext.narrative_tone);
    }

    if (locationContext.atmosphere) {
      parts.push(locationContext.atmosphere);
    }

    if (regionContext.atmosphere_keywords && regionContext.atmosphere_keywords.length > 0) {
      const keywords = regionContext.atmosphere_keywords.join(", ");
      if (lang === "cn") {
        parts.push(`氛围关键词: ${keywords}`);
      } else {
        parts.push(`Atmosphere keywords: ${keywords}`);
      }
    }

    return parts.join(" | ");
  }
}
