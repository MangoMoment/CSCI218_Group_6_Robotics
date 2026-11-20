/**
 * MAQUEEN — FIND THE OBJECT ON BLACK, GRAB IT, BRING IT HOME
 * CSCI218 Lab 8 (humanitarian warehouse pick-up)
 *
 * WHAT IT DOES
 *   Press A. The robot visits each direction in ANGLES (left, centre, right) one at a time:
 *   it turns, drives straight out, and checks the floor under it.
 *     - Floor turns black  -> target: open claw, creep in, close claw, reverse home.
 *     - Reaches an object without black -> wrong one: reverse home, face forward, try the next.
 *   After every trip it is back at the start facing forward, so errors don't build up.
 *
 * SETUP (makecode.microbit.org)
 *   1. New Project -> Settings (gear) -> Extensions -> search "maqueen" -> pick the first one.
 *   2. JavaScript tab -> delete everything -> paste this file -> Download to the micro:bit.
 *   3. Claw servo plugged into S1. Fresh batteries; Maqueen power switch ON.
 *   If line "maqueen.Ultrasonic()" shows red, change it to maqueen.Ultrasonic(PingUnit.Centimeters)
 *   (older extension version).
 *
 * LAYOUT
 *   - Mark the start point with tape. Robot on it, facing forward.
 *   - One object in each direction listed in ANGLES (default: 45° left, straight ahead,
 *     45° right), about 30 cm from the robot.
 *   - Target object sits on MATTE black (paper/card/tape — shiny black doesn't work).
 *     The black must reach 10–15 cm toward the robot so the sensors underneath
 *     roll onto it before the robot gets close to the object.
 *   - Rest of the floor light-coloured. Nothing else within ~60 cm.
 *
 * CALIBRATE (do once per robot, ~5 minutes)
 *   1. CLAW: after switching on, the claw should close. Press B to open / close it.
 *      Adjust CLAW_OPEN / CLAW_CLOSED below (low number = open, high = closed on our claws;
 *      below ~100 is past the open limit). If the servo buzzes when closed, lower CLAW_CLOSED by 10.
 *   2. FLOOR SENSOR: if the robot drives over black without stopping, change BLACK to 0.
 *   3. TURNING: HOLD B while switching on -> robot does one full 360° turn.
 *      Turned too little -> raise TURN_90_MS. Too much -> lower it. Repeat until it ends where it began.
 *      (If the wheels hum but it doesn't turn, raise TURN_SPEED.)
 *
 * SCREEN
 *   ☺ starting · 1/2/3 trip number · ✓ black found, grabbing · ✗ wrong object
 *   ◆ done, holding object at start · ? no target found
 *   Stop in an emergency: switch the robot off.
 */

// ===================== SETTINGS — TUNE ON YOUR ROBOT =====================
const ANGLES = [-45, 0, 45]   // directions to try, in degrees (negative = left), in this order

const CLAW_OPEN = 120         // servo angle: claw open wide enough for the object
const CLAW_CLOSED = 170       // servo angle: claw gripping the object

const BLACK = 1               // what the floor sensors read on black (1 on our robots; else 0)

const SPEED = 50              // driving speed (0–255) — keep low for safety and accuracy
const SLOW = 30               // creeping speed for the final grab
const TURN_SPEED = 80         // turning speed — too low and the robot won't rotate
const TURN_90_MS = 400        // time to turn 90° — calibrate with the 360° test

const STOP_CM = 8             // stop this far from an object if no black was found
const GRAB_CM = 5             // while creeping with the claw open, stop at this distance
const MAX_DRIVE_MS = 4000     // safety limit for driving out (stops even if nothing is seen)
const CREEP_MAX_MS = 2000     // safety limit for the creep
const PUSH_MS = 200           // extra push at the end (sensor can't see very close objects)
const SETTLE_MS = 300         // pause after each move so the robot stops wobbling
// ========================================================================

let running = false
let clawIsOpen = false
let driveMs = 0
let creepMs = 0

function stopMotors() {
    maqueen.motorStop(maqueen.Motors.All)
}

function setClaw(open: boolean) {
    if (open) {
        maqueen.servoRun(maqueen.Servos.S1, CLAW_OPEN)
    } else {
        maqueen.servoRun(maqueen.Servos.S1, CLAW_CLOSED)
    }
    clawIsOpen = open
    basic.pause(600)
}

// Turn on the spot. Positive = right, negative = left.
function turnDegrees(deg: number) {
    if (deg == 0) {
        return
    }
    if (deg > 0) {
        maqueen.motorRun(maqueen.Motors.M1, maqueen.Dir.CW, TURN_SPEED)   // left wheel forward
        maqueen.motorRun(maqueen.Motors.M2, maqueen.Dir.CCW, TURN_SPEED)  // right wheel back
    } else {
        maqueen.motorRun(maqueen.Motors.M1, maqueen.Dir.CCW, TURN_SPEED)
        maqueen.motorRun(maqueen.Motors.M2, maqueen.Dir.CW, TURN_SPEED)
    }
    basic.pause(Math.abs(deg) * TURN_90_MS / 90)
    stopMotors()
    basic.pause(SETTLE_MS)
}

// Distance ahead in cm. 0 or silly values mean "nothing seen".
function distanceCm(): number {
    let d = maqueen.Ultrasonic()
    if (d <= 0 || d > 300) {
        d = 999
    }
    return d
}

function onBlack(): boolean {
    return maqueen.readPatrol(maqueen.Patrol.PatrolLeft) == BLACK ||
        maqueen.readPatrol(maqueen.Patrol.PatrolRight) == BLACK
}

// Drive straight out. Returns true if black was found.
// Needs two readings in a row to agree, so one noisy reading can't fool it.
function approach(): boolean {
    let start = input.runningTime()
    let blackHits = 0
    let closeHits = 0
    let black = false
    maqueen.motorRun(maqueen.Motors.All, maqueen.Dir.CW, SPEED)
    while (input.runningTime() - start < MAX_DRIVE_MS) {
        if (onBlack()) {
            blackHits += 1
        } else {
            blackHits = 0
        }
        if (blackHits >= 2) {
            black = true
            break
        }
        if (distanceCm() <= STOP_CM) {
            closeHits += 1
        } else {
            closeHits = 0
        }
        if (closeHits >= 2) {
            break
        }
        basic.pause(10)
    }
    stopMotors()
    driveMs = input.runningTime() - start
    basic.pause(SETTLE_MS)
    return black
}

// Open the claw, creep up to the object, close the claw.
function grab() {
    setClaw(true)
    let start = input.runningTime()
    maqueen.motorRun(maqueen.Motors.All, maqueen.Dir.CW, SLOW)
    while (input.runningTime() - start < CREEP_MAX_MS) {
        if (distanceCm() <= GRAB_CM) {
            break
        }
        basic.pause(10)
    }
    basic.pause(PUSH_MS)
    stopMotors()
    creepMs = input.runningTime() - start
    basic.pause(SETTLE_MS)
    setClaw(false)
}

// Reverse along the same straight line back to the start.
function reverseHome() {
    if (creepMs > 0) {
        maqueen.motorRun(maqueen.Motors.All, maqueen.Dir.CCW, SLOW)
        basic.pause(creepMs)
    }
    if (driveMs > 0) {
        maqueen.motorRun(maqueen.Motors.All, maqueen.Dir.CCW, SPEED)
        basic.pause(driveMs)
    }
    stopMotors()
    basic.pause(SETTLE_MS)
    driveMs = 0
    creepMs = 0
}

// ---------------- A: run the task ----------------
input.onButtonPressed(Button.A, function () {
    if (running) {
        return
    }
    running = true
    let found = false
    setClaw(false)
    basic.showIcon(IconNames.Happy)
    basic.pause(1000)

    for (let i = 0; i < ANGLES.length; i++) {
        let angle = ANGLES[i]
        basic.showNumber(i + 1)
        turnDegrees(angle)
        if (approach()) {
            basic.showIcon(IconNames.Yes)
            grab()
            found = true
        } else {
            basic.showIcon(IconNames.No)
        }
        reverseHome()
        turnDegrees(-angle)   // face forward again at the start
        if (found) {
            break
        }
    }

    if (found) {
        basic.showIcon(IconNames.Diamond)
    } else {
        basic.showString("?")
    }
    running = false
})

// ---------------- B: open / close the claw (testing, or to release the object) ----------------
input.onButtonPressed(Button.B, function () {
    if (!running) {
        setClaw(!clawIsOpen)
    }
})

// ---------------- On start ----------------
if (input.buttonIsPressed(Button.B)) {
    // Calibration: hold B while switching on -> one full turn
    basic.showString("T")
    basic.pause(1000)
    turnDegrees(360)
    basic.showIcon(IconNames.Yes)
} else {
    setClaw(false)
    basic.showIcon(IconNames.Happy)
}
