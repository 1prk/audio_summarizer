#!/usr/bin/env python3
"""
Automatically dump all data and clear the database while keeping structure.
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
            record_dict = {}
            for column in model_class.__table__.columns:
                value = getattr(record, column.name)
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                record_dict[column.name] = value
            data.append(record_dict)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Dumped {len(data)} records from {model_class.__name__}")
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
        return count
    
    except Exception as e:
        logger.error(f"Error clearing {model_class.__name__}: {str(e)}")
        return 0


def reset_sqlite_sequences():
    """Reset SQLite auto-increment sequences."""
    try:
        db_path = None
        if hasattr(db.engine.url, 'database') and db.engine.url.database:
            db_path = db.engine.url.database
        
        if db_path and os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sqlite_sequence")
            conn.commit()
            conn.close()
            logger.info("Reset SQLite sequences")
    
    except Exception as e:
        logger.error(f"Error resetting sequences: {str(e)}")


def main():
    """Main function."""
    app = create_app()
    
    with app.app_context():
        # Create backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(f"database_backup_{timestamp}")
        backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"Creating backup in: {backup_dir}")
        
        # Tables in order for foreign key constraints
        tables = [
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
        
        # 1. Dump data
        logger.info("=== BACKING UP DATA ===")
        total_backed_up = 0
        for model_class, filename in tables:
            filepath = backup_dir / filename
            count = dump_table_data(model_class, filepath)
            total_backed_up += count
        
        logger.info(f"Backup complete: {total_backed_up} records")
        
        # 2. Clear data
        logger.info("=== CLEARING DATA ===")
        total_cleared = 0
        for model_class, _ in reversed(tables):
            count = clear_table_data(model_class)
            total_cleared += count
        
        db.session.commit()
        reset_sqlite_sequences()
        
        logger.info(f"Clear complete: {total_cleared} records removed")
        
        # 3. Verify
        logger.info("=== VERIFICATION ===")
        all_clear = True
        for model_class, _ in tables:
            count = model_class.query.count()
            if count == 0:
                logger.info(f"✓ {model_class.__name__}: empty")
            else:
                logger.warning(f"⚠ {model_class.__name__}: {count} records remain")
                all_clear = False
        
        if all_clear:
            print(f"\n🎉 SUCCESS!")
            print(f"📁 Backup: {backup_dir.absolute()}")
            print(f"📊 Backed up: {total_backed_up} records")
            print(f"🗑 Cleared: {total_cleared} records")
            print(f"🗄 Database structure: PRESERVED")
            print(f"✨ Ready for fresh start!")
        else:
            print(f"\n⚠️ Some data may remain - check logs")


if __name__ == "__main__":
    main()