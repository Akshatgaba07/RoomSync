"""Questionnaire schema: single source of truth shared by ML, backend and frontend.

Every question has a canonical key, the original Google-Form column title (for the CSV
pipeline), a type, and the ordered options. Ordinal options are listed in ascending order.
Two *extra* questions (alcohol / smoking in room) exist because two dealbreaker options in
the original form cannot be checked against any survey answer; demo profiles leave them blank.
"""
from __future__ import annotations

HOSTEL = ["Boys hostel", "Girls hostel"]
YEAR = ["1st", "2nd", "3rd", "4th"]

QUESTIONS: dict[str, dict] = {
    "year": dict(col="Year of study", type="single", options=YEAR, section="About you",
                 label="Year of study"),
    "hostel": dict(col="Hostel type", type="single", options=HOSTEL, section="About you",
                   label="Hostel type"),
    "bedtime": dict(col="Usual weekday bedtime", type="single", ordinal=True,
                    options=["Before 11 PM", "11 PM - 1 AM", "1 AM - 3 AM", "After 3 AM"],
                    section="Sleep & climate", label="Usual weekday bedtime"),
    "wake": dict(col="Usual weekday wake-up time", type="single", ordinal=True,
                 options=["Before 6 AM", "6 - 8 AM", "8 - 10 AM", "After 10 AM"],
                 section="Sleep & climate", label="Usual weekday wake-up time"),
    "light_tolerance": dict(
        col="How easily can you sleep with lights, laptop glow or a roommate moving around?",
        type="scale", min=1, max=5, section="Sleep & climate",
        label="How easily can you sleep with lights, laptop glow or a roommate moving around?",
        scale_hint=("Light sleeper", "Sleep through anything")),
    "climate": dict(col="Night-time AC / cooler / fan preference", type="single",
                    options=["Windows open, nothing on", "Fan only", "AC or cooler on all night", "No preference"],
                    section="Sleep & climate", label="Night-time AC / cooler / fan preference"),
    "tidiness": dict(col="How tidy do you keep your room and desk?", type="scale", min=1, max=5,
                     section="Cleanliness", label="How tidy do you keep your room and desk?",
                     scale_hint=("Very messy", "Spotless")),
    "clearing": dict(col="How soon do you clear dishes, wrappers and dirty laundry?", type="single",
                     ordinal=True,
                     options=["Immediately", "Same day", "When it starts piling up",
                              "Whenever / when someone complains"],
                     section="Cleanliness", label="How soon do you clear dishes, wrappers and dirty laundry?"),
    "study_time": dict(col="When do you mostly study?", type="single", ordinal=True,
                       options=["Daytime", "Evening", "Late night (after midnight)"],
                       section="Study & noise", label="When do you mostly study?"),
    "study_env": dict(col="Your ideal study environment", type="single",
                      options=["Total silence", "Low background noise is fine", "Music with headphones",
                               "Anything works, I don't mind"],
                      section="Study & noise", label="Your ideal study environment"),
    "gaming": dict(col="Gaming / streaming in the room per day", type="single", ordinal=True,
                   options=["Rarely", "1 - 2 hours", "3 - 5 hours", "5+ hours"],
                   section="Study & noise", label="Gaming / streaming in the room per day"),
    "audio": dict(col="Audio habits in the room", type="single", ordinal=True,
                  options=["Always headphones", "Mostly headphones", "Speakers sometimes", "Speakers usually"],
                  section="Study & noise", label="Audio habits in the room"),
    "calls": dict(col="How often do you take long phone/video calls in the room?", type="scale",
                  min=1, max=5, section="Study & noise",
                  label="How often do you take long phone/video calls in the room?",
                  scale_hint=("Never", "Very often")),
    "guest_freq": dict(col="How often do you have friends over in the room?", type="scale", min=1, max=5,
                       section="Social life", label="How often do you have friends over in the room?",
                       scale_hint=("Never", "Very often")),
    "guest_comfort": dict(
        col="How comfortable are you with your roommate's guests/hangouts in the room?",
        type="scale", min=1, max=5, section="Social life",
        label="How comfortable are you with your roommate's guests/hangouts in the room?",
        scale_hint=("Uncomfortable", "Totally fine")),
    "weekend": dict(col="What do your weekends usually look like?", type="single",
                    options=["Mostly in the hostel", "Mix of in and out", "Mostly out with friends",
                             "I go home often"],
                    section="Social life", label="What do your weekends usually look like?"),
    "food": dict(col="Your food preference", type="single",
                 options=["Vegetarian", "Eggetarian", "Non-vegetarian", "Jain / other restrictions"],
                 section="Food", label="Your food preference"),
    "nonveg_comfort": dict(col="Comfortable with a roommate eating non-veg in the room?", type="single",
                           options=["Yes", "Only if it's not smelly / cleaned up", "No"],
                           section="Food", label="Comfortable with a roommate eating non-veg in the room?"),
    "room_eating": dict(col="How often do you eat (snacks, takeaway, cooking) inside the room?",
                        type="scale", min=1, max=5, section="Food",
                        label="How often do you eat (snacks, takeaway, cooking) inside the room?",
                        scale_hint=("Never", "Very often")),
    "conflict": dict(col="When a roommate does something that bothers you, you usually...", type="single",
                     options=["Say it directly, right away", "Bring it up calmly later",
                              "Hint at it indirectly", "Stay quiet and avoid conflict"],
                     section="Living together",
                     label="When a roommate does something that bothers you, you usually..."),
    "sharing": dict(col="Sharing attitude (snacks, chargers, stationery, etc.)", type="scale", min=1, max=5,
                    section="Living together", label="Sharing attitude (snacks, chargers, stationery, etc.)",
                    scale_hint=("Keep mine separate", "Happy to share everything")),
    "alone_time": dict(col="How much alone time do you need in the room each day?", type="scale",
                       min=1, max=5, section="Living together",
                       label="How much alone time do you need in the room each day?",
                       scale_hint=("Very little", "A lot")),
    "relationship": dict(col="What kind of roommate relationship do you want?", type="single", ordinal=True,
                         options=["Polite coexistence, mostly keep to ourselves", "Friendly but independent",
                                  "Close friends"],
                         section="Living together", label="What kind of roommate relationship do you want?"),
    # --- extras not in the original Google Form (optional) ---
    "alcohol_in_room": dict(col=None, type="single", options=["Yes", "No"], optional=True,
                            section="Extras", label="Do you drink alcohol in the room?"),
    "smokes": dict(col=None, type="single", options=["Yes", "No"], optional=True,
                   section="Extras", label="Do you smoke / vape?"),
}

DEALBREAKER_COL = "Hard dealbreakers: you would NOT want a roommate who..."
PRIORITY_COL = "Which 3 things matter MOST to you in a roommate? (pick up to 3)"
CURRENT_COMPAT_COL = "How compatible are you with your CURRENT roommate overall?"
SYNTHETIC_COL = "SYNTHETIC"

DEALBREAKERS = [
    "Keeps lights / noise on late at night",
    "Takes loud calls at night",
    "Plays music or videos on speaker",
    "Eats non-veg in the room",
    "Has overnight guests often",
    "Keeps the room messy",
    "Drinks alcohol in the room",
    "Smokes / vapes",
]
NO_DEALBREAKER = "None of these"

PRIORITIES = [
    "Sleep schedule", "Noise and study environment", "Cleanliness", "Food habits",
    "Guests and social life", "Privacy and personal space", "Sharing and borrowing",
    "Handling conflict well",
]
MAX_PRIORITIES = 3

# Compatibility dimensions: display label, the priority option that boosts it, base importance.
DIMENSIONS: dict[str, dict] = {
    "sleep": dict(label="Sleep schedule", priority="Sleep schedule", base=1.3),
    "noise_study": dict(label="Noise & study environment", priority="Noise and study environment", base=1.3),
    "cleanliness": dict(label="Cleanliness & hygiene", priority="Cleanliness", base=1.2),
    "food": dict(label="Food habits", priority="Food habits", base=0.9),
    "climate": dict(label="Night-time AC / fan", priority=None, base=0.8),
    "entertainment": dict(label="Gaming, streaming & audio", priority="Noise and study environment", base=0.7),
    "guests": dict(label="Guests & visitors", priority="Guests and social life", base=1.0),
    "weekend": dict(label="Weekend lifestyle", priority="Guests and social life", base=0.5),
    "privacy": dict(label="Privacy & personal space", priority="Privacy and personal space", base=1.0),
    "sharing": dict(label="Sharing habits", priority="Sharing and borrowing", base=0.7),
    "conflict": dict(label="Conflict-resolution style", priority="Handling conflict well", base=0.9),
    "relationship": dict(label="Desired relationship", priority=None, base=0.8),
}
PRIORITY_BOOST = 1.8  # multiplier on dimensions tied to a student's top-3 priorities

REQUIRED_KEYS = [k for k, q in QUESTIONS.items() if not q.get("optional")]


def questionnaire_spec() -> list[dict]:
    """Serializable questionnaire definition for the frontend."""
    out = []
    for key, q in QUESTIONS.items():
        d = {k: v for k, v in q.items() if k != "col"}
        d["key"] = key
        out.append(d)
    return out
