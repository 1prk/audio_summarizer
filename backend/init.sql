-- PostgreSQL initialization script for Audio Summarizer
-- This script sets up the database with necessary extensions

-- Create the database (if using initdb)
-- CREATE DATABASE audio_summarizer;

-- Connect to the database
\c audio_summarizer;

-- Enable pgvector extension for vector storage (when available)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Create indexes for better performance (will be created by SQLAlchemy migrations)
-- These are examples for future optimization

-- Performance indexes for common queries
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_external_id ON videos(external_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_processing_status ON videos(processing_status);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_channels_external_id ON channels(external_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transcripts_video_id ON transcripts(video_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transcripts_start_time ON transcripts(start_time);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_tasks_status ON processing_tasks(status);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_tasks_video_id ON processing_tasks(video_id);

-- Full-text search indexes for transcripts
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transcripts_text_fts ON transcripts USING gin(to_tsvector('english', text));

-- Composite indexes for common query patterns
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_channel_status ON videos(channel_id, processing_status);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_status_created ON videos(processing_status, created_at DESC);

GRANT ALL PRIVILEGES ON DATABASE audio_summarizer TO audio_user;