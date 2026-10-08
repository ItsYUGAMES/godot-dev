# UI, themes, focus, text, localization

## Layout
- Non-trivial layouts use Containers. Container children lose manual position/size: control them
  with `size_flags_horizontal/vertical` (Fill/Expand/Shrink), `size_flags_stretch_ratio`,
  `custom_minimum_size`. Don't set offsets/position/scale of container children.
- Anchors 0..1 of the parent; offsets in pixels from anchors; use presets (Full Rect) for roots.
- Margins/separations are theme constants, not properties:
  `margin.add_theme_constant_override(&"margin_left", 16)`; `vbox.add_theme_constant_override(&"separation", 8)`.
- Containers lag one frame after `resized`; re-layout via `call_deferred`.
- Autowrap Labels/RichTextLabels need a maximum width (`custom_maximum_size` or a parent with
  `propagate_maximum_size`, containers default true) in 4.7.
- Decorative/overlay Controls: `mouse_filter = Control.MOUSE_FILTER_IGNORE` (Control default
  STOP blocks clicks; Containers default PASS).
- HUD in a CanvasLayer above the game. Popups: `popup()`/`popup_centered()`, not `show()`.
  Windows don't close themselves: handle `close_requested`.

## Focus and gamepad/keyboard navigation
- Give focus at start: `%StartButton.grab_focus.call_deferred()` — otherwise keyboard and pad
  navigation does nothing.
- `ui_*` actions drive focus navigation: never use them for gameplay. Set
  `focus_neighbor_*`/`focus_next/previous` explicitly in complex menus; hidden controls lose focus.
- UI input in `_gui_input(event)` + `accept_event()`. Custom controls draw a focus indicator when
  `has_focus()` and react to `NOTIFICATION_THEME_CHANGED`/`NOTIFICATION_RESIZED`.
- Accessibility (4.5+): `accessibility_name`/`accessibility_description` on controls.

## Themes
- One project theme (`gui/theme/custom`, a `.tres`): scenes run alone ignore a theme set only on
  a root Control. Lookup: local override → nearest ancestor `theme` → project theme → default.
- Reuse styles with `theme_type_variation` instead of repeated local overrides. Runtime tweaks:
  `add_theme_stylebox_override(&"normal", style.duplicate())`; `Theme.merge_with()` mutates the receiver.
- Focus StyleBoxes draw on top: outlines or translucent fills.

## Fonts and text
- Font size belongs to the using node/LabelSettings (4.0+). FontVariation for faux bold, spacing,
  variable axes; SystemFont for OS fonts; fallbacks for CJK/emoji (emoji fonts CBDT/SVG).
- Pixel fonts: Nearest filter, subpixel positioning off, integer sizes. MSDF for big/scaled text.
- RichTextLabel: `bbcode_enabled = true`; build with `append_text()`/`push_*()`/`pop()`
  (assigning `text` wipes them); never interleave tags; escape user text (`[` → `[lb]`);
  `[url]` needs a `meta_clicked` handler (`str(meta)`). `is_ready()` → `is_finished()`.

## Pause menus and screens
- Pause: `get_tree().paused = true`; menu root `process_mode = PROCESS_MODE_ALWAYS`; fade with a
  tween; restore focus on resume.
- Responsive: stretch `canvas_items` + `expand`, AspectRatioContainer for fixed-ratio panels;
  verify at two window sizes (e.g. 1280×720 and 1920×1080, plus portrait if mobile).

## Localization
- Register translations in Project Settings → Localization. CSV: UTF-8 without BOM,
  case-sensitive keys, `?plural`/`?context` columns (4.6+); PO for translator tooling/plurals.
- `tr("KEY")`, `tr_n(singular, plural, n)`, format after translating:
  `tr("{name} hit {target}").format({"name": a, "target": b})`.
- `auto_translate_mode = AUTO_TRANSLATE_MODE_DISABLED` on Controls showing user data.
- Non-Latin scripts: font fallbacks; export with `internationalization/locale/include_text_server_data`.
- Test with `internationalization/locale/test` (clear before commit) or pseudolocalization.
- Ignore generated `*.translation` in VCS.
