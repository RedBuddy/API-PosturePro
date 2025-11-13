from app.init import create_app
# ...existing code...
app = create_app()

if __name__ == "__main__":
    # Cambia host/port si lo necesitas
    app.run(host="0.0.0.0", port=5000, debug=True)