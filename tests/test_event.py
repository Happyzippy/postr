import coincurve as cc
from postr.model.event import TextNote

def test_textnote():
    priv = cc.PrivateKey()
    note = TextNote.build(priv, "Hello world")
    assert note.verify()