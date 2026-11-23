// Runs the scenario under the app's own Application (`run_shots.sh --real-app`): its real
// dependency injection, data and image loading, instead of the test runner's test Application.
package appmap

import androidx.test.runner.AndroidJUnitRunner

class AppMapRunner : AndroidJUnitRunner()
