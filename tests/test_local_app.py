import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAYUZ_DIR = os.path.join(BASE_DIR, "8_Arayuz")
if ARAYUZ_DIR not in sys.path:
    sys.path.insert(0, ARAYUZ_DIR)


def test_required_directories_and_models_exist():
    assert os.path.isdir(ARAYUZ_DIR)
    assert os.path.isdir(os.path.join(ARAYUZ_DIR, "models"))
    assert os.path.isdir(os.path.join(ARAYUZ_DIR, "templates"))
    assert os.path.isfile(os.path.join(BASE_DIR, "requirements.txt"))


def test_flask_app_boots_and_serves_home():
    orig_cwd = os.getcwd()
    os.chdir(ARAYUZ_DIR)
    try:
        import main as web_main
        client = web_main.app.test_client()
        resp = client.get("/", follow_redirects=True)
        assert resp.status_code == 200
        assert b"<html" in resp.data.lower()
    finally:
        os.chdir(orig_cwd)
