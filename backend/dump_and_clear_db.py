#!/usr/bin/env python3
"""
Dump all data from the database and then clear it while keeping the structure.
This script will:
1. Create a backup of all data
2. Clear all tables
3. Keep the database schema intact
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app, db
from app.models import (
    Video, Channel, ProcessingTask, Transcript, Entity, EntityMention, 
    Topic, TopicAssignment, Embedding, EmotionAnalysis
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def dump_table_data(model_class, filename):
    """Dump data from a table to JSON file."""
    try:
        data = []
        records = model_class.query.all()
        
        for record in records:
            # Convert SQLAlchemy object to dictionary
            record_dict = {}
            for column in model_class.__table__.columns:
                value = getattr(record, column.name)
                # Handle datetime objects
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                record_dict[column.name] = value
            data.append(record_dict)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Dumped {len(data)} records from {model_class.__name__} to {filename}")
        return len(data)
    
    except Exception as e:
        logger.error(f"Error dumping {model_class.__name__}: {str(e)}")
        return 0


def clear_table_data(model_class):
    """Clear all data from a table."""
    try:
        count = model_class.query.count()
        if count > 0:
            model_class.query.delete()
            logger.info(f"Cleared {count} records from {model_class.__name__}")
        else:
            logger.info(f"Table {model_class.__name__} was already empty")
        return count
    
    except Exception as e:
        logger.error(f"Error clearing {model_class.__name__}: {str(e)}")
        return 0


def reset_sqlite_sequences():
    """Reset SQLite auto-increment sequences."""
    try:
        # Get database file path
        db_path = None
        if hasattr(db.engine.url, 'database') and db.engine.url.database:
            db_path = db.engine.url.database
        
        if db_path and os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Reset all sequences
            cursor.execute("DELETE FROM sqlite_sequence")
            conn.commit()
            conn.close()
            logger.info("Reset SQLite auto-increment sequences")
        else:
            logger.info("Not using SQLite or database file not found - skipping sequence reset")
    
    except Exception as e:
        logger.error(f"Error resetting sequences: {str(e)}")


def main():
    """Main function to dump and clear database."""
    app = create_app()
    
    with app.app_context():
        # Create backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(f"database_backup_{timestamp}")
        backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"Creating database backup in: {backup_dir}")
        
        # Define tables in order (respecting foreign key constraints)
        tables_to_process = [
            (EmotionAnalysis, "emotion_analysis.json"),
            (TopicAssignment, "topic_assignments.json"),
            (Topic, "topics.json"),
            (Embedding, "embeddings.json"),
            (EntityMention, "entity_mentions.json"),
            (Entity, "entities.json"),
            (Transcript, "transcripts.json"),
            (ProcessingTask, "processing_tasks.json"),
            (Video, "videos.json"),
            (Channel, "channels.json"),
        ]
        
        total_records = 0
        
        # 1. Dump all data
        logger.info("=== DUMPING DATA ===")
        for model_class, filename in tables_to_process:
            filepath = backup_dir / filename
            count = dump_table_data(model_class, filepath)
            total_records += count
        
        # Create summary file
        summary = {
            "backup_timestamp": timestamp,
            "total_records": total_records,
            "tables": {model.__name__: model.query.count() for model, _ in tables_to_process}
        }
        
        with open(backup_dir / "backup_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Backup completed: {total_records} total records")
        
        # 2. Confirm before clearing
        response = input(f"\nBackup created with {total_records} records in {backup_dir}/\n"
                        "Do you want to clear all data from the database? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("Operation cancelled. Data preserved.")
            return
        
        # 3. Clear all data
        logger.info("=== CLEARING DATA ===")
        total_cleared = 0
        
        # Clear in reverse order to respect foreign key constraints
        for model_class, _ in reversed(tables_to_process):
            count = clear_table_data(model_class)
            total_cleared += count
        
        # Commit all changes
        db.session.commit()
        
        # Reset auto-increment sequences
        reset_sqlite_sequences()
        
        logger.info(f"Database cleared: {total_cleared} records removed")
        logger.info("Database structure preserved")
        
        # 4. Verify cleanup
        logger.info("=== VERIFICATION ===")
        for model_class, _ in tables_to_process:
            count = model_class.query.count()
            if count == 0:
                logger.info(f"✓ {model_class.__name__}: empty")
            else:
                logger.warning(f"⚠ {model_class.__name__}: still has {count} records")
        
        print(f"\n✅ Database cleared successfully!")
        print(f"📁 Backup saved to: {backup_dir.absolute()}")
        print(f"📊 {total_records} records backed up, {total_cleared} records cleared")
        print(f"🗄 Database structure preserved")


if __name__ == "__main__":
    main()