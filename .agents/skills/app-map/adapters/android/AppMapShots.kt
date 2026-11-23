// App map screenshots for an Android app: copied into the app's androidTest by run_shots.sh,
// never committed. At each snap it saves a screenshot and logs where every class the map draws
// sits on screen, in dp: Activities, Fragments and Views by class name, and @Composable
// functions by name, read from Compose's own inspector data (as Android Studio's Layout
// Inspector does).
package appmap

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.Rect
import android.os.Build
import android.util.Log
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.view.inspector.WindowInspector
import androidx.compose.runtime.tooling.CompositionData
import androidx.compose.ui.platform.isDebugInspectorInfoEnabled
import androidx.compose.ui.tooling.data.Group
import androidx.compose.ui.tooling.data.UiToolingDataApi
import androidx.compose.ui.tooling.data.asTree
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.runner.lifecycle.ActivityLifecycleMonitorRegistry
import androidx.test.runner.lifecycle.Stage
import java.io.File

/**
 * Call [AppMapShots.enable] before the activity starts (a test class's `init` block runs before
 * its rules), so Compose records what each composition draws.
 */
@OptIn(UiToolingDataApi::class)
class AppMapShots(classes: Collection<String>) {
    private val classes = classes.toSet()
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val out = File(instrumentation.targetContext.filesDir, "app-map-shots").apply {
        deleteRecursively()
        mkdirs()
    }
    private val log = File(out, "drive.log")
    private val density = instrumentation.targetContext.resources.displayMetrics.density
    private val failed = mutableListOf<String>()
    private var shots = 0
    private val opensDialog = mutableSetOf<String>()  // composables that only open a dialog
    private val dialogCalls = setOf("Dialog", "AlertDialog", "BasicAlertDialog", "DatePickerDialog", "ModalBottomSheet", "Popup")

    companion object {
        fun enable() {
            isDebugInspectorInfoEnabled = true
        }
    }

    fun log(line: String) {
        Log.i("AppMapShots", line)
        log.appendText(line + "\n")
    }

    /** Runs one step of the scenario; a failure is logged and the run goes on. */
    fun step(name: String, block: () -> Unit) {
        try {
            block()
        } catch (error: Throwable) {
            failed += name
            log("SHOT STEP FAILED: $name: ${error.message?.lineSequence()?.firstOrNull() ?: error}")
        }
    }

    /** A screenshot, and a `SHOT RECT` line for every class of the map that's on screen. */
    fun snap(name: String) {
        instrumentation.waitForIdleSync()
        Thread.sleep(700)
        val bitmap: Bitmap = instrumentation.uiAutomation.takeScreenshot()
        File(out, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        if (shots++ == 0) log("SHOT SCREEN ${bitmap.width / density} ${bitmap.height / density}")
        log("SHOT TAKEN $name")
        val found = mutableListOf<Pair<String, Rect>>()
        val hidden = mutableSetOf<Int>()
        instrumentation.runOnMainSync {
            val roots = rootViews()
            opensDialog.clear()
            roots.forEachIndexed { index, root ->
                val dimmedAbove = roots.drop(index + 1).any { it.isDimming() }
                val start = found.size
                walkViews(root, found)
                if (dimmedAbove) (start until found.size).forEach { hidden += it }
            }
            // A composable that only opens a dialog has no size of its own: it gets the dialog's.
            val activityRoot = currentActivity()?.window?.decorView
            val dialog = roots.lastOrNull { it !== activityRoot }?.let { composeContent(it) }
            if (dialog != null) opensDialog.forEach { found += it to dialog }
            currentActivity()?.let { activity ->
                val window = activity.window.decorView
                if (activity.javaClass.simpleName in classes) found += activity.javaClass.simpleName to window.screenRect()
                fragments(activity).forEach { (type, view) ->
                    if (type in classes && view.isShown) found += type to view.screenRect()
                }
            }
        }
        found.forEachIndexed { index, (type, rect) ->
            val hits = if (index in hidden) 0 else 5
            log("SHOT RECT $name $type ${dp(rect.left)} ${dp(rect.top)} ${dp(rect.width())} ${dp(rect.height())} $hits")
        }
    }

    /** The last line of the scenario: what ran and what didn't. */
    fun report() {
        log("SHOT DONE $shots shots, ${failed.size} failed step(s)${if (failed.isEmpty()) "" else ": " + failed.joinToString()}")
    }

    private fun dp(px: Int) = "%.1f".format(px / density)

    private fun rootViews(): List<View> =
        if (Build.VERSION.SDK_INT >= 29) WindowInspector.getGlobalWindowViews().filter { it.isShown }
        else listOfNotNull(currentActivity()?.window?.decorView)

    private fun View.isDimming(): Boolean {
        val params = layoutParams as? WindowManager.LayoutParams ?: return false
        return params.flags and WindowManager.LayoutParams.FLAG_DIM_BEHIND != 0 && params.dimAmount > 0f
    }

    private fun View.screenRect(): Rect {
        val at = IntArray(2)
        getLocationOnScreen(at)
        return Rect(at[0], at[1], at[0] + width, at[1] + height)
    }

    private fun walkViews(view: View, found: MutableList<Pair<String, Rect>>) {
        if (!view.isShown) return
        if (view.javaClass.simpleName in classes) found += view.javaClass.simpleName to view.screenRect()
        @Suppress("UNCHECKED_CAST")
        val tables = view.getTag(androidx.compose.ui.R.id.inspection_slot_table_set) as? Set<CompositionData>
        if (tables != null) {
            // Compose reports boxes in window coordinates.
            val origin = view.rootView.screenRect()
            tables.toList().forEach { table -> walkGroup(table.asTree(), origin, null, found) }
        }
        if (view is ViewGroup) for (index in 0 until view.childCount) walkViews(view.getChildAt(index), found)
    }

    private fun callsDialog(group: Group, depth: Int = 0): Boolean =
        group.name in dialogCalls || (depth < 40 && group.children.any { callsDialog(it, depth + 1) })

    /** Where a dialog window's Compose content is drawn on screen. */
    private fun composeContent(root: View): Rect? {
        if (root.getTag(androidx.compose.ui.R.id.inspection_slot_table_set) != null) return root.screenRect()
        if (root is ViewGroup) for (index in 0 until root.childCount) composeContent(root.getChildAt(index))?.let { return it }
        return null
    }

    /** A composable's box, clipped to its parents' (a list item under the app bar is cut). */
    private fun walkGroup(group: Group, origin: Rect, clip: Rect?, found: MutableList<Pair<String, Rect>>) {
        val box = group.box
        val own = Rect(origin.left + box.left, origin.top + box.top, origin.left + box.right, origin.top + box.bottom)
        val name = group.name
        if (name != null && name in classes && (own.width() <= 0 || own.height() <= 0) && callsDialog(group)) {
            opensDialog += name
        }
        if (name != null && name in classes && own.width() > 0 && own.height() > 0) {
            val visible = Rect(own)
            if (clip == null || visible.intersect(clip)) {
                val whole = visible == own
                found += name to (if (whole) own else visible)
            }
        }
        val childClip = if (own.width() > 0 && own.height() > 0) Rect(own).also { if (clip != null) it.intersect(clip) } else clip
        group.children.forEach { walkGroup(it, origin, childClip, found) }
    }

    /** Each shown Fragment and its view, when the app uses AndroidX Fragments (read by reflection,
     *  so a Compose-only app needs no fragment dependency). */
    private fun fragments(activity: Activity): List<Pair<String, View>> = try {
        val manager = activity.javaClass.getMethod("getSupportFragmentManager").invoke(activity)
        fun walk(manager: Any): List<Pair<String, View>> =
            (manager.javaClass.getMethod("getFragments").invoke(manager) as List<*>).filterNotNull().flatMap { fragment ->
                val view = fragment.javaClass.getMethod("getView").invoke(fragment) as? View
                val children = fragment.javaClass.getMethod("getChildFragmentManager").invoke(fragment)
                listOfNotNull(view?.let { fragment.javaClass.simpleName to it }) + walk(children)
            }
        walk(manager)
    } catch (error: ReflectiveOperationException) {
        emptyList()
    }

    private fun currentActivity(): Activity? {
        var activity: Activity? = null
        val read = {
            activity = ActivityLifecycleMonitorRegistry.getInstance()
                .getActivitiesInStage(Stage.RESUMED).firstOrNull()
        }
        if (android.os.Looper.myLooper() == android.os.Looper.getMainLooper()) read() else instrumentation.runOnMainSync(read)
        return activity
    }
}
