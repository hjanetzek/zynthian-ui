// A part of the UI not needed for the first frame (a screen, a widget, the keypad): created at
// once while it is needed (shown), else after the first frame in the background (asynchronous,
// in the event loop's idle time: Startup.ready), and then kept, as before. A load in progress
// completes at once when the part becomes needed. The part comes as sourceComponent (an inline
// Component, so a theme's file selectors pick its type as everywhere else); its size follows
// the Loader's.
import QtQuick

Loader {
    property bool needed: false
    property bool allowed: true    // false: never created (e.g. no keypad in the theme)
    active: allowed && (needed || Startup.ready)
    asynchronous: !needed
}
