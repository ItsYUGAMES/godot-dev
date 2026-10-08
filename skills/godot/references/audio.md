# Audio

- Buses: layout in `res://default_bus_layout.tres` (commit it). Players reference buses by name and
  silently fall back to `Master` on typos — don't rename buses casually. Keep Master ≤0 dB with
  AudioEffectHardLimiter last (`AudioEffectLimiter` is deprecated).
- Volume sliders: `AudioServer.set_bus_volume_linear(idx, v)` / `volume_linear`, or
  `linear_to_db()`/`db_to_linear()`; mute via `set_bus_mute`, not hiding nodes (hiding a
  positional player doesn't stop it).
- Overlapping SFX from one player: raise `max_polyphony` (default 1). Variation:
  AudioStreamRandomizer (pitch/volume/random clips) instead of code.
- `finished` is not emitted on `stop()`, tree exit, or for looping streams.
- Formats: WAV for short SFX (QOA compression default), Ogg Vorbis for music; looping is an
  import flag (Ogg/MP3 loop offset only). Positional: AudioStreamPlayer2D/3D; 3D doppler needs
  `doppler_tracking` on both the player and the Camera3D.
- Music sync: song time = `get_playback_position() + AudioServer.get_time_since_last_mix() -
  AudioServer.get_output_latency()`; drop values that go backwards.
- Areas can override reverb buses (`audio_bus_override`); 4.7: `AudioStreamPlayer2D/3D.area_mask`
  defaults to 0 — re-enable layer 1 if relying on Area bus overrides.
- Each scene owns its own players; avoid a global SFX pool autoload. A music autoload
  (persistent across scene changes) is a legitimate autoload.
- Web: default playback type is Sample — no bus effects, reverb or procedural audio; audio starts
  only after a user gesture. Mic input needs `audio/driver/enable_input`.
