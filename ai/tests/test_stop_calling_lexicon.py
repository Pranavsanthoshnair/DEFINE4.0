import pytest

from app.intent.rules import classify


@pytest.mark.parametrize(
    ("language", "text"),
    [
        ("en", "I don't want to be called"),
        ("en", "Don't call me again"),
        ("en", "Stop callin"),
        ("hi", "mujhe phone mat karo"),
        ("hi", "call karna band karo"),
        ("hi", "stop callin"),
        ("hi", "मुझे फोन मत करो"),
        ("hi", "कॉल करना बंद करो"),
        ("hi", "मुझे फिर फोन मत करो"),
        ("ml", "vilikalle"),
        ("ml", "enne vilikkaruth"),
        ("ml", "stop callin"),
        ("ml", "വിളിക്കല്ലേ"),
        ("ml", "എന്നെ വിളിക്കരുത്"),
        ("ml", "വീണ്ടും വിളിക്കരുത്"),
        ("ta", "ennai azhaikkadheenga"),
        ("ta", "azhaippathai niruthungal"),
        ("ta", "stop callin"),
        ("ta", "என்னை அழைக்காதீர்கள்"),
        ("ta", "அழைப்பதை நிறுத்துங்கள்"),
        ("ta", "மீண்டும் அழைக்காதீர்கள்"),
    ],
)
def test_stop_calling_pattern_matches(language, text):
    label, confidence = classify(text, language, ["stop_calling"])

    assert label == "stop_calling"
    assert confidence == 0.95
