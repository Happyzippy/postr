import coincurve as cc

from postr.model.event import TextNote
from postr.user import User

def test_textnote():
    user = User()
    note = user.sign(TextNote(content="Hello World"))
    assert note.verify()