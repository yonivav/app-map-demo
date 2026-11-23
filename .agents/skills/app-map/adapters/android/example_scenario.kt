package appmap

import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.espresso.Espresso
import com.example.app.MainActivity // the app's launcher activity
import org.junit.Rule
import org.junit.Test

/**
 * One pass through every module of the map: a few `snap`s per screen, in module order.
 * Run it with `app-map shots android <app module> <this file> <out> [--variant Debug]`.
 * A Hilt app also needs its HiltAndroidRule (order 0) and `@HiltAndroidTest`.
 */
class AppMapScenario {
    init {
        AppMapShots.enable() // before the activity starts: Compose records what it draws
    }

    @get:Rule
    val compose = createAndroidComposeRule<MainActivity>()

    // Every class the map's diagrams draw: Activities, Fragments, Views, @Composable functions.
    private val shots = AppMapShots(listOf("MainActivity", "HomeScreen", "ItemCard", "DetailScreen", "SettingsDialog"))

    private fun settle() {
        compose.waitForIdle()
        Thread.sleep(1500)
    }

    @Test
    fun appMap() {
        settle()
        shots.step("home") {
            shots.snap("home_01_list")
        }
        shots.step("detail") {
            compose.onNodeWithText("First item").performClick()
            settle()
            shots.snap("detail_01_item")
            Espresso.pressBack()
            settle()
        }
        shots.step("settings") {
            compose.onNodeWithContentDescription("Settings").performClick()
            settle()
            shots.snap("settings_01_dialog")
        }
        shots.report()
    }
}
