# Copilot Coding Agent — Steering Instructions
# Repository: Rogmar0071/ui-blueprint

## Android layout rules (CRITICAL — violations cause CI build failures)

### No percentage values in XML layout attributes
NEVER use percentage strings (e.g. `"70%"`) in any `android:layout_width` or
`android:layout_height` XML attribute. The Android resource linker rejects them with:
  error: 'X%' is incompatible with attribute layout_width (attr) dimension|enum

**Wrong:**
```xml
android:layout_width="70%"
```

**Correct — set width programmatically in the adapter/activity:**
```kotlin
val params = holder.bubbleContainer.layoutParams as FrameLayout.LayoutParams
params.width = (parentWidth * 0.70).toInt()
holder.bubbleContainer.layoutParams = params
```
Or use ConstraintLayout with `app:layout_constraintWidth_percent="0.70"`.

### Allowed dimension values in XML
Only these forms are valid for `layout_width` / `layout_height`:
- `match_parent`
- `wrap_content`
- Exact dp values: `"240dp"`, `"48dp"`, etc.
- `"0dp"` (used with `layout_weight` in LinearLayout)

---

## CI build environment
- Android Gradle Plugin with Gradle 8.7, JDK 17 (Temurin)
- `dl.google.com` is **blocked by the agent firewall** — do NOT trigger tasks that
  download from Google (e.g. fresh SDK components, new Gradle distributions).
  All required SDK components are pre-installed.
- Build command: `./gradlew :app:assembleDebug` (run from `android/` directory)
- Build must pass before marking a PR ready for review.

---

## PR workflow
- All Android UI PRs currently target `copilot/redesign-android-app-dark-theme` as
  base branch (not `main`) until the dark theme redesign is merged.
- Always run a mental lint pass on XML files before committing:
  check every `layout_width` / `layout_height` value.
- Keep Kotlin changes minimal when the fix is purely a layout change.
