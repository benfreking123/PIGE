import src.flaskapp as FlaskApp


if __name__ == '__main__':
    flask = FlaskApp.create_flask_app()

    try:
        flask.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        pass