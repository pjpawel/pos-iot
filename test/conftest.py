# import pytest
# from pos.start_node_flask import app as app_flask
#
#
# @pytest.fixture()
# def app():
#     app = app_flask()
#     app.config.update({
#         "TESTING": True,
#     })
#
#     yield app
#
#
# @pytest.fixture()
# def client(app):
#     return app.test_client()
