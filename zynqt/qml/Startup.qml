pragma Singleton
import QtQml

// The UI's start: ready once the first frame is on screen (Main.qml). Deferred parts of the UI
// are created after that, in the background.
QtObject {
    property bool ready: false
}
