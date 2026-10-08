# Multiplayer and networking

## High-level multiplayer
- Peer: `var peer := ENetMultiplayerPeer.new()`; check `peer.create_server(port)` /
  `create_client(ip, port)` returns OK, then `multiplayer.multiplayer_peer = peer`. Reset with
  `multiplayer.multiplayer_peer = null` (or `OfflineMultiplayerPeer`). Server id is 1.
  ENet is UDP; WebSocket/WebRTC peers for Web.
- Connect all five signals in `_ready`: `peer_connected`, `peer_disconnected`,
  `connected_to_server`, `connection_failed`, `server_disconnected`.
- Server-authoritative by default. Guard with `if not multiplayer.is_server(): return` or
  `is_multiplayer_authority()`; set authority per node with `set_multiplayer_authority(id)`.
- RPCs: `@rpc` (defaults `"authority", "call_remote", "reliable", 0`); call with `fn.rpc(args)` /
  `fn.rpc_id(1, args)`. Every peer must declare the same `@rpc` functions at the same NodePath
  (checksum mismatch causes odd errors) — add networked nodes with `add_child(node, true)` for
  stable names.
- `any_peer` RPCs run on the server with client input: read `multiplayer.get_remote_sender_id()`
  first (before any `await` — it returns 0 later), validate sender, arguments and rate.
- `call_local` when the host also plays; `"unreliable"`/`"unreliable_ordered"` for
  high-frequency transforms on their own channel.
- Never pass Objects/Callables through RPCs; never enable `allow_object_decoding` with untrusted
  peers (remote code execution).
- High-level multiplayer works only between identical Godot versions/builds.

## Spawning and sync
- MultiplayerSpawner: set `spawn_path`; scenes in its spawnable list replicate when added as
  direct children of that path; or `spawn_function` returning a node not yet in the tree (don't
  add_child it yourself) and call `spawner.spawn(data)` on the server. Type-check the data array;
  name player nodes after the peer id.
- MultiplayerSynchronizer: split an input synchronizer (client authority) from a state
  synchronizer (server authority); clamp synced input in setters. Don't sync Object/Resource/RID
  properties.
- Lobby pattern: server waits for every peer to report `player_loaded.rpc_id(1)` before starting.
  Optional auth: `SceneMultiplayer.auth_callback` + `complete_auth()` on both sides.

## Testing
- Run two instances: Debug → Customize Run Instances (one server, one client) or two CLI runs;
  verify join, spawn, movement sync, disconnect handling. Log peer ids in output for evidence.

## HTTP, WebSocket, low level
- HTTPRequest: keep in tree, one request in flight per node (else `ERR_BUSY`); in
  `request_completed` check `result == HTTPRequest.RESULT_SUCCESS` and `response_code`; never
  embed secrets in the client.
- WebSocketPeer/WebRTCPeerConnection/HTTPClient: `poll()` every frame, drain with
  `while peer.get_available_packet_count() > 0`, `close()` in `_exit_tree`; no blocking loops on Web.
- TLS: self-signed certs go in the TLS bundle override; never ship private keys. Native WebRTC
  needs the webrtc-native GDExtension. Android needs the INTERNET permission.
