from app import create_app


app = create_app()


if __name__ == "__main__":
    # Bind to all interfaces so it is reachable when running inside a container.
    app.run(host="0.0.0.0", port=5000, debug=True)
