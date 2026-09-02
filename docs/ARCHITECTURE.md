# 📐 Architecture & Reverse Engineering Details

This document explains the technical implementation of **HeadRush NAM Studio Pro**, the internal block file schemas, and the communication mechanics with HeadRush OS.

---

## 1. HeadRush Block Preset Schema (`.block`)

HeadRush block presets are JSON files containing metadata, unique UUIDs, and a nested serialized JSON string in the `content` field.

### Anxiety OD / Anxiety OD V2 Schema
```json
{
  "content": "{\"data\":{\"Anxiety OD V2\":{\"childorder\":[\"Level\",\"Drive\",\"Tone\",\"Hi-Lo\"],\"children\":{\"Drive\":{\"type\":0,\"value\":28},\"Hi-Lo\":{\"state\":false,\"type\":1},\"Level\":{\"type\":0,\"value\":70},\"Tone\":{\"type\":0,\"value\":50}}}},\"info\":{\"version\":\"1.0.9\"}}",
  "id": "e2c34a1b-9f0e-48a1-b8d2-192a84920482",
  "readonly": false,
  "type": "ANXIETY OD V2"
}
```

- `"type": 0`: Integer parameter type.
- `"Drive": {"value": N}`: Drives the knob position directly to slot index `N` (0 to 100).
- `"Tone": {"value": N}`: Input Trim (0 to 100, default 50).
- `"Level": {"value": N}`: Output Trim (0 to 100, default 70).

### IR Block Preset Schema
```json
{
  "content": "{\"data\":{\"IR\":{\"childorder\":[\"DoubleStates\",\"IR\",\"Gain\",\"HiCut\",\"LoCut\",\"Mix\"],\"children\":{\"DoubleStates\":{\"state\":false,\"type\":3},\"Gain\":{\"type\":0,\"value\":-10.0},\"HiCut\":{\"type\":0,\"value\":10000},\"IR\":{\"string\":\"[directory](Celestion EVH 5150)[name](EVH_5150_4x12_SM57_Center)\",\"type\":8},\"LoCut\":{\"type\":0,\"value\":50},\"Mix\":{\"type\":0,\"value\":100}}}},\"info\":{\"version\":\"1.0.9\"}}",
  "id": "3b7fa120-7cd9-411a-8c54-4a2791845110",
  "readonly": false,
  "type": "IR"
}
```

- `"type": 8`: String reference type.
- `IR String syntax`: `[directory](<FolderName>)[name](<WavFilenameWithoutExtension>)`.

---

## 2. Dual-Compatibility Generation Strategy

To ensure zero-error compatibility across all firmware variants:
1. When installing any NAM model or updating trims, the application writes block presets to **both**:
   - `E:\Blocks\ANXIETY OD\` (`type: "ANXIETY OD"`)
   - `E:\Blocks\ANXIETY OD V2\` (`type: "ANXIETY OD V2"`)
2. This guarantees that regardless of whether the user installed the 2-instance or 4-instance firmware mod, the preset will appear and work in their chosen pedal block.

---

## 3. SQLite FTS5 Search Engine

The local catalog utilizes SQLite with Full-Text Search (FTS5):
- `models_fts`: Indexed on model name, pack title, creator username, category, and tags.
- Query latency is sub-millisecond (< 1ms) across 97,974 records.
- Supports architecture filtering (`architecture_version = '2'` for A2 slim models optimized for embedded ARM DSP).
