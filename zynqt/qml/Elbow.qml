import QtQuick

// The frame around the screens in themes with Theme.elbow (+enterprise/Elbow.qml draws it):
// nothing elsewhere. Main.qml places it and makes room for it from the tokens.
Item {
    property real arm: 180
    property real thickness: Theme.elbowBar
}
