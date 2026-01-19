# TypeScript Backend Retrieval Implementation Plan

> **Generated**: 2026-01-19  
> **Status**: Planning  
> **Related**: Python backend (`src/backend/`) migration to TypeScript (`src/backend-ts/`)

## Overview

This document outlines the plan to complete the retrieval functionality in the TypeScript backend, ensuring feature parity with the Python backend's RAG (Retrieval-Augmented Generation) system.

---

## Current State Comparison

### Architecture Comparison

| Component | Python Backend | TypeScript Backend | Status |
|-----------|----------------|-------------------|--------|
| Vector Database | ChromaDB (PersistentClient) | LanceDB (Embedded) | Migrated |
| Embedding Model | Qwen3-Embedding-0.6B (sentence-transformers) | Qwen3-Embedding-0.6B-ONNX (Transformers.js) | Migrated |
| Vector Dimension | 1024-dim | 1024-dim | Consistent |
| Distance Metric | Cosine | Cosine | Consistent |
| Tokenizer | jieba (Chinese) | Intl.Segmenter (Native API) | Migrated |

### Feature Gap Analysis

#### 1. Lore Retrieval (World Knowledge Search)

| Feature | Python | TypeScript | Gap |
|---------|--------|------------|-----|
| Hybrid Search (Keyword + Vector) | Yes | Yes | None |
| Keyword Weights (Primary: 2.0, Secondary: 1.0) | Yes | Yes | None |
| Vector Weight (0.8 x similarity) | Yes | Yes | None |
| Dual Match Boost (1.5x) | Yes | Yes | None |
| Location Filtering (applicable_locations) | Yes | Yes | None |
| Region Filtering (applicable_regions) | Yes | Yes | None |
| **Auto-indexing on World Pack Load** | Yes | **No** | **To Implement** |
| **Hash-based Change Detection** | Yes | **No** | **To Implement** |

#### 2. NPC Memory Retrieval

| Feature | Python | TypeScript | Gap |
|---------|--------|------------|-----|
| Semantic Memory Retrieval | Yes | **No** | **To Implement** |
| Memory Persistence | Yes | **No** | **To Implement** |
| NPC-specific Collections | Yes | **No** | **To Implement** |
| Memory Metadata (keywords, timestamp) | Yes | **No** | **To Implement** |

#### 3. GM Conversation History Retrieval

| Feature | Python | TypeScript | Gap |
|---------|--------|------------|-----|
| Long History Vector Retrieval | Yes | **No** | **To Implement** |
| Session-specific Collections | Yes | **No** | **To Implement** |
| Threshold Trigger (>= 10 messages) | Yes | **No** | **To Implement** |
| Chronological Sorting Post-Retrieval | Yes | **No** | **To Implement** |

---

## Design Decisions

### 1. Indexing Timing: Asynchronous

**Decision**: Use asynchronous background indexing instead of synchronous blocking.

**Rationale**:
- Faster server startup time
- Non-blocking world pack loading
- Better user experience during initial load

**Implementation Approach**:
```typescript
// In WorldPackLoader.load()
const pack = await this.loadFromFile(packId);
// Fire-and-forget async indexing
this.indexLoreEntriesAsync(packId, pack).catch(console.error);
return pack;
```

### 2. NPC Memory Lifecycle: Session-Isolated

**Decision**: NPC memories are isolated per session, not globally persistent.

**Rationale**:
- Each game session is independent
- Prevents cross-session memory leakage
- Simpler cleanup semantics
- Aligns with TTRPG "fresh start" expectations

**Collection Naming Convention**:
```
npc_memories_{session_id}_{npc_id}
```

### 3. Old Session Cleanup: Deferred

**Decision**: No automatic cleanup of old session vector data for now.

**Rationale**:
- LanceDB storage is efficient
- Manual cleanup can be added later
- Avoid premature optimization
- Focus on core functionality first

---

## Implementation Plan

### Phase 1: Infrastructure (Priority: HIGH)

#### 1.1 Implement Lore Auto-Indexing

**File**: `src/backend-ts/src/services/world.ts`

**Tasks**:
- [ ] Add `indexLoreEntriesAsync()` method
- [ ] Create documents for both CN and EN versions
- [ ] Store metadata: `uid`, `keys`, `lang`, `visibility`, `applicable_regions`, `applicable_locations`
- [ ] Call indexing after successful pack load

**Reference** (Python implementation):
```python
# src/backend/services/world.py: _index_lore_entries()
documents.append(entry.content.cn)
metadatas.append({
    "uid": entry.uid,
    "keys": ",".join(entry.key),
    "order": entry.order,
    "lang": "cn",
    "constant": entry.constant,
    "visibility": entry.visibility,
    "applicable_regions": ",".join(entry.applicable_regions),
    "applicable_locations": ",".join(entry.applicable_locations),
})
```

#### 1.2 Implement Hash-based Change Detection

**File**: `src/backend-ts/src/services/world.ts`

**Tasks**:
- [ ] Add `computePackHash()` using `crypto.createHash('sha256')`
- [ ] Store hash in LanceDB table metadata
- [ ] Compare hashes before re-indexing
- [ ] Skip indexing if hash matches

**Algorithm**:
```typescript
async indexLoreEntriesAsync(packId: string, pack: WorldPack): Promise<void> {
  const currentHash = this.computePackHash(pack);
  const storedHash = await this.vectorStore.getTableMetadata(tableName, 'pack_hash');
  
  if (storedHash === currentHash) {
    console.log(`[WorldPackLoader] Index up-to-date (hash: ${currentHash.slice(0, 8)}...)`);
    return;
  }
  
  // Proceed with indexing...
}
```

#### 1.3 Extend LanceDB Metadata Support

**File**: `src/backend-ts/src/lib/lance.ts`

**Tasks**:
- [ ] Add `getTableMetadata()` method
- [ ] Add `setTableMetadata()` method (via table recreation or custom metadata table)
- [ ] Handle metadata storage for hash tracking

---

### Phase 2: NPC Memory System (Priority: MEDIUM)

#### 2.1 Inject VectorStore into NPCAgent

**File**: `src/backend-ts/src/agents/npc/index.ts`

**Tasks**:
- [ ] Add `vectorStore?: LanceDBService` to constructor
- [ ] Update NPCAgent instantiation points

```typescript
export class NPCAgent {
  constructor(
    private llm: LanguageModel,
    private vectorStore?: LanceDBService,  // Add this
    private maxTokens?: number
  ) {}
}
```

#### 2.2 Implement Memory Retrieval

**File**: `src/backend-ts/src/agents/npc/index.ts`

**Tasks**:
- [ ] Add `retrieveRelevantMemories()` method
- [ ] Query `npc_memories_{session_id}_{npc_id}` collection
- [ ] Return top N relevant memories
- [ ] Graceful fallback when vector store unavailable

```typescript
private async retrieveRelevantMemories(
  sessionId: string,
  npcId: string,
  playerInput: string,
  allMemories: Record<string, string[]>,
  nResults: number = 3
): Promise<string[]> {
  if (!this.vectorStore || Object.keys(allMemories).length === 0) {
    return [];
  }

  const collectionName = `npc_memories_${sessionId}_${npcId}`;
  const results = await this.vectorStore.search(collectionName, playerInput, nResults);
  return results.map(r => r.text);
}
```

#### 2.3 Implement Memory Persistence

**File**: `src/backend-ts/src/agents/npc/index.ts`

**Tasks**:
- [ ] Add `persistMemory()` method
- [ ] Store new memory events after NPC interactions
- [ ] Include metadata (keywords, timestamp)

```typescript
async persistMemory(
  sessionId: string,
  npcId: string,
  memoryEvent: string,
  keywords: string[]
): Promise<void> {
  if (!this.vectorStore) return;

  const collectionName = `npc_memories_${sessionId}_${npcId}`;
  await this.vectorStore.addDocuments(
    collectionName,
    [memoryEvent],
    [`${Date.now()}_${Math.random().toString(36).slice(2)}`],
    [{ keywords: keywords.join(','), timestamp: Date.now() }]
  );
}
```

---

### Phase 3: GM History Retrieval (Priority: MEDIUM)

#### 3.1 Implement History Retrieval

**File**: `src/backend-ts/src/agents/gm/index.ts`

**Tasks**:
- [ ] Add `retrieveRelevantHistory()` method
- [ ] Threshold check: only use vector search if messages >= 10
- [ ] Sort retrieved messages by turn for chronological order

```typescript
private async retrieveRelevantHistory(
  sessionId: string,
  playerInput: string,
  allMessages: GameMessage[],
  nResults: number = 5
): Promise<GameMessage[]> {
  // Short history: return all
  if (allMessages.length < 10) {
    return allMessages;
  }

  // No vector store: return recent
  if (!this.vectorStore) {
    return allMessages.slice(-nResults);
  }

  const collectionName = `conversation_history_${sessionId}`;
  const results = await this.vectorStore.search(collectionName, playerInput, nResults);
  
  const retrievedIds = new Set(results.map(r => r.id));
  const retrievedMessages = allMessages.filter(
    msg => retrievedIds.has(`${sessionId}_msg_${msg.turn}`)
  );

  // Sort by turn for chronological order
  return retrievedMessages.sort((a, b) => a.turn - b.turn);
}
```

#### 3.2 Implement History Indexing

**File**: `src/backend-ts/src/agents/gm/index.ts`

**Tasks**:
- [ ] Index each message after it's added to history
- [ ] Use message content as document
- [ ] Include metadata (role, turn, timestamp)

```typescript
private async indexMessage(
  sessionId: string,
  message: GameMessage
): Promise<void> {
  if (!this.vectorStore) return;

  const collectionName = `conversation_history_${sessionId}`;
  await this.vectorStore.addDocuments(
    collectionName,
    [message.content],
    [`${sessionId}_msg_${message.turn}`],
    [{ role: message.role, turn: message.turn, timestamp: message.timestamp }]
  );
}
```

#### 3.3 Modify buildContext()

**File**: `src/backend-ts/src/agents/gm/index.ts`

**Tasks**:
- [ ] Replace `messages.slice(-10)` with `retrieveRelevantHistory()` call
- [ ] Ensure backward compatibility when vector store unavailable

---

### Phase 4: Testing & Verification (Priority: STANDARD)

#### 4.1 Lore Indexing Tests

**File**: `tests/services/world.test.ts`

- [ ] Test index creation on first load
- [ ] Test hash change detection
- [ ] Test skip indexing when hash matches
- [ ] Test CN/EN dual document creation

#### 4.2 NPC Memory Tests

**File**: `tests/agents/npc.test.ts`

- [ ] Test memory retrieval with vector store
- [ ] Test memory persistence
- [ ] Test graceful fallback without vector store
- [ ] Test session isolation

#### 4.3 GM History Tests

**File**: `tests/agents/gm.test.ts`

- [ ] Test short history passthrough (< 10 messages)
- [ ] Test vector retrieval for long history
- [ ] Test chronological sorting
- [ ] Test graceful fallback

---

## Timeline

```
Week 1: Phase 1 (Infrastructure)
  Day 1-2: Task 1.3 (LanceDB metadata support)
  Day 3-4: Task 1.1 (Lore auto-indexing)
  Day 5:   Task 1.2 (Hash change detection)

Week 2: Phase 2 (NPC Memory)
  Day 1:   Task 2.1 (Inject vectorStore)
  Day 2-3: Task 2.2 (Memory retrieval)
  Day 4:   Task 2.3 (Memory persistence)
  Day 5:   Integration testing

Week 3: Phase 3 (GM History) + Phase 4 (Tests)
  Day 1-2: Task 3.1 (History retrieval)
  Day 3:   Task 3.2 (History indexing)
  Day 4:   Task 3.3 (Modify buildContext)
  Day 5:   Phase 4 tests
```

---

## File Change Summary

| File | Changes |
|------|---------|
| `src/backend-ts/src/lib/lance.ts` | Add metadata methods |
| `src/backend-ts/src/services/world.ts` | Add async indexing, hash detection |
| `src/backend-ts/src/agents/npc/index.ts` | Add vectorStore, memory retrieval/persistence |
| `src/backend-ts/src/agents/gm/index.ts` | Add history retrieval/indexing, modify buildContext |
| `src/backend-ts/src/index.ts` | Pass vectorStore to services/agents |
| `tests/services/world.test.ts` | New: indexing tests |
| `tests/agents/npc.test.ts` | New: memory tests |
| `tests/agents/gm.test.ts` | New: history tests |

---

## References

- Python VectorStoreService: `src/backend/services/vector_store.py`
- Python LoreService: `src/backend/services/lore.py`
- Python WorldPackLoader indexing: `src/backend/services/world.py` (lines 165-265)
- Python NPCAgent memory: `src/backend/agents/npc.py` (lines 184-225, 553-568)
- Python GMAgent history: `src/backend/agents/gm.py` (lines 1039-1098)
