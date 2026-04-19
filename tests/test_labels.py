from visiontag.labels_pt import COCO_PT, translate_label


def test_known_label():
    assert translate_label("car") == "carro"
    assert translate_label("dog") == "cachorro"
    assert translate_label("person") == "pessoa"


def test_unknown_label_returns_original():
    assert translate_label("spaceship") == "spaceship"
    assert translate_label("") == ""


def test_coco_pt_complete():
    assert len(COCO_PT) == 80
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in COCO_PT.items())
