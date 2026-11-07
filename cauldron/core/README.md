# Core Submodule

Contains reusable LED abstractions, effects, players, and lifecycle
orchestration. `Cauldron` accepts injected `Player` instances and manages their
handles; it does not load assets or construct project-specific effects.

The generic `EventBus` supports decoupled command dispatch. Project composition,
including effect/player construction and event subscriptions, lives in
`cauldron.application`.

`RealtimeAudioPlayer` can use `LiveBrightnessAnalyzer` to measure captured
audio chunks and update an injected strip's brightness while the live stream
continues through its configured audio effects. The Cauldron application starts
this analyzer continuously; set `CAULDRON_INPUT_DEVICE` in
`cauldron.config.config` to the operating system's loopback input to visualize
system playback instead of microphone input.