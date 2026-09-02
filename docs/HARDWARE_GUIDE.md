# 🎸 HeadRush Hardware & NAM Mod Guide

This guide covers everything you need to know about using Neural Amp Modeler (NAM) models on HeadRush hardware (MX5, Prime, Core, Gigboard, Pedalboard) with the **headrush-nam-mod**.

---

## 🔌 Connecting Your HeadRush via USB Transfer

1. Connect your HeadRush pedal to your computer using a standard USB cable.
2. On the touchscreen:
   - Tap the **3 dots** (Global Menu / Hardware Settings) in the top-right corner.
   - Tap **USB Transfer**.
3. Your computer will mount the HeadRush internal storage as a removable drive (usually `E:`, `F:`, or `D:`).
4. Launch **HeadRush NAM Studio** or run the CLI.

> ⚠️ **CRITICAL STEP - DISCONNECTING & REBOOTING**:
> When you finish transferring new `.nam` models or presets:
> 1. Tap **Sync / Eject** on the HeadRush touchscreen and disconnect the USB cable.
> 2. **RESTART YOUR HEADRUSH** (turn off with the power switch/button and turn back on).
> 3. *Why?* The HeadRush OS only indexes and preloads `.nam` files from `/NAM` into memory during boot. If you don't restart, the newly installed slots will produce silence!

---

## 🎛️ How the NAM Mod Works on HeadRush

The mod hijacks the stock **Anxiety OD** (and optionally **Anxiety OD V2**) distortion pedals inside the firmware.

| Knob on Pedal | Function in NAM Mode |
|---|---|
| **DRIVE** | Selects the active NAM Model (`0%` = Slot 000, `100%` = Slot 100) |
| **TONE** | Input Trim (calibrates pickup signal strength into the neural network) |
| **LEVEL** | Output Trim / Volume (adjusts output signal level without clipping) |

---

## 📁 File Structure on HeadRush Drive

- `E:\NAM\`: Contains `.nam` models named with a 3-digit index prefix:
  - `000 - ModelName.nam`
  - `001 - AnotherModel.nam`
  - ... up to `100 - LastModel.nam` (maximum 101 slots).
- `E:\Blocks\ANXIETY OD\` & `E:\Blocks\ANXIETY OD V2\`:
  - Contains `.block` presets corresponding to each slot.
  - Selecting the preset automatically sets the **DRIVE** knob to the exact slot percentage and sets your saved **TONE** and **LEVEL** trims.
- `E:\Impulse Responses\`:
  - Contains `.wav` IR files organized into folders (e.g., `Celestion EVH`, `Mesa OS 4x12`).
- `E:\Blocks\IR\`:
  - Contains `.block` presets referencing specific IRs.

---

## 🔊 Rig Building Best Practices

1. **Amp Only Models (Head / Preamp)**:
   - Add `Anxiety OD V2` (or `Anxiety OD`) block.
   - Immediately follow it with an **IR** block (load your favorite cabinet IR).
2. **Full Rig Models (Amp + Cab)**:
   - Add `Anxiety OD V2` block.
   - Do **NOT** add an IR block after it (the speaker cabinet response is already baked in).
3. **Overdrive / Distortion Pedal Captures**:
   - Place the `Anxiety OD V2` block **before** your standard amp simulation or before another NAM amp block (if running 4-instance mod).
