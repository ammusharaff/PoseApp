# src/poseapp/activities/activity_defs.py
# Map "primary_joints" to keys from angles_of_interest() in geometry/angles.py  # file-level note

ACTIVITY_LIBRARY = {  # central registry of guided activities shown in the UI
    "squat": {  # bodyweight squat definition
        "label": "Squat",  # human-readable name in menus
        "reps": 5,  # default target repetitions per set
        "primary_joints": ["knee_L_flex", "knee_R_flex", "hip_L_flex", "hip_R_flex", "ankle_L_flex", "ankle_R_flex"],  # joints tracked for scoring/overlay
        "score_joint": "knee_L_flex",     # main angle used to time/score reps (uses left knee by default)
        "targets": {"knee_L_flex": 90, "knee_R_flex": 90, "hip_L_flex": 85, "hip_R_flex": 85, "ankle_L_flex": 75, "ankle_R_flex": 75},  # target peak angles (deg)
        "guide": "assets/guides/squat.gif"  # path to a reference GIF for the guided panel
    },
    "arm_abduction": {  # lateral arm raise definition
        "label": "Arm Abduction",  # menu label
        "reps": 5,  # default reps
        "primary_joints": ["shoulder_L_abd", "shoulder_R_abd"],  # both shoulders’ abduction angles
        "score_joint": "shoulder_L_abd",  # use left shoulder as the cycle/scoring signal
        "targets": {"shoulder_L_abd": 90, "shoulder_R_abd": 90, "shoulder_L_abd_alt": 120, "shoulder_R_abd_alt": 120},  # base + optional higher target
        "guide": "assets/guides/arm_abduction.gif"  # reference GIF
    },
    "forward_flexion": {  # shoulder flexion (sagittal plane) definition
        "label": "Forward Flexion",  # menu label
        "reps": 5,  # default reps
        "primary_joints": ["shoulder_L_flex", "shoulder_R_flex"],  # both shoulders’ flexion angles
        "score_joint": "shoulder_L_flex",  # use left shoulder flexion as scoring signal
        "targets": {"shoulder_L_flex": 90, "shoulder_R_flex": 90},  # target peak flexion (deg)
        "guide": "assets/guides/forward_flexion.gif"  # reference GIF
    },
    "calf_raise": {  # heel raise definition
        "label": "Calf Raises",  # menu label
        "reps": 10,  # default reps
        "primary_joints": ["ankle_L_flex", "ankle_R_flex"],  # ankle flex metric (note: elsewhere code may expect *_pf for plantarflexion)  # WARNING: naming may differ from other modules
        "score_joint": "ankle_L_flex",  # use left ankle flex as cycle/scoring signal
        "targets": {"ankle_L_flex": 110, "ankle_R_flex": 110},  # target ankle flexion (deg)
        "guide": "assets/guides/calf_raise.gif"  # reference GIF
    },
    "jumping_jack": {  # jumping jack definition
        "label": "Jumping Jacks",  # menu label
        "reps": 10,  # default reps
        "primary_joints": ["shoulder_L_abd", "shoulder_R_abd", "hip_L_abd", "hip_R_abd"],  # arms and legs abduction angles
        "score_joint": "shoulder_L_abd",  # use left shoulder abduction to drive rep timing
        "targets": {"shoulder_L_abd": 120, "shoulder_R_abd": 120, "hip_L_abd": 45, "hip_R_abd": 45},  # target ranges for arms/legs
        "guide": "assets/guides/jumping_jack.gif"  # reference GIF
    }
}
