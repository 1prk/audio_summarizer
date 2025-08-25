from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Pre-load all models before starting server
    from app.tasks import preload_all_models
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Pre-loading models before server startup...")
    models_status = preload_all_models()
    
    ready_count = sum(models_status.values())
    total_models = len(models_status)
    
    if ready_count < total_models:
        logger.warning(f"Only {ready_count}/{total_models} models loaded successfully")
        logger.warning("Some features may not work correctly")
    else:
        logger.info("All models loaded successfully!")
    
    # Use SocketIO for development server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)