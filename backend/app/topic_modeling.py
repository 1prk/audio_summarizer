"""
Topic modeling implementation using BERTopic for content intelligence.
"""
import os
import logging
import json
import pickle
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, Counter

import numpy as np
import pandas as pd
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.cluster import HDBSCAN
from umap import UMAP
from hdbscan import HDBSCAN
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)


@dataclass
class TopicInfo:
    """Information about a discovered topic."""
    topic_id: int
    name: str
    description: str
    keywords: List[str]
    size: int
    coherence_score: float
    representative_docs: List[str]
    created_at: datetime
    last_updated: datetime


@dataclass
class DocumentTopic:
    """Topic assignment for a document."""
    document_id: str
    topic_id: int
    probability: float
    text: str
    timestamp: Optional[datetime] = None


@dataclass
class TopicModelingResult:
    """Result of topic modeling analysis."""
    topics: List[TopicInfo]
    document_topics: List[DocumentTopic]
    model_info: Dict[str, Any]
    processing_time: float
    coherence_score: float


class TopicEvolutionTracker:
    """Track how topics evolve over time."""
    
    def __init__(self):
        self.topic_timeline = defaultdict(list)  # topic_id -> [(timestamp, strength)]
        self.topic_merges = []  # (old_topic_ids, new_topic_id, timestamp)
        self.topic_splits = []  # (old_topic_id, new_topic_ids, timestamp)
        
    def add_topic_observation(self, topic_id: int, timestamp: datetime, strength: float):
        """Add a topic observation at a specific time."""
        self.topic_timeline[topic_id].append((timestamp, strength))
    
    def detect_topic_emergence(self, topic_id: int, threshold_days: int = 7) -> bool:
        """Detect if a topic recently emerged."""
        if topic_id not in self.topic_timeline:
            return False
            
        observations = self.topic_timeline[topic_id]
        if not observations:
            return False
            
        first_observation = min(obs[0] for obs in observations)
        days_since_first = (datetime.now() - first_observation).days
        
        return days_since_first <= threshold_days
    
    def detect_topic_decline(self, topic_id: int, threshold_ratio: float = 0.5) -> bool:
        """Detect if a topic is declining in strength."""
        if topic_id not in self.topic_timeline:
            return False
            
        observations = sorted(self.topic_timeline[topic_id], key=lambda x: x[0])
        if len(observations) < 3:
            return False
            
        # Compare recent strength to peak strength
        recent_strength = np.mean([obs[1] for obs in observations[-3:]])
        peak_strength = max(obs[1] for obs in observations)
        
        return recent_strength < (peak_strength * threshold_ratio)
    
    def get_topic_trends(self, days_back: int = 30) -> Dict[int, float]:
        """Get topic trends over the specified period."""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        trends = {}
        
        for topic_id, observations in self.topic_timeline.items():
            recent_obs = [obs for obs in observations if obs[0] >= cutoff_date]
            if len(recent_obs) >= 2:
                # Calculate trend slope
                times = [(obs[0] - cutoff_date).days for obs in recent_obs]
                strengths = [obs[1] for obs in recent_obs]
                trend = np.polyfit(times, strengths, 1)[0]
                trends[topic_id] = trend
                
        return trends


class TopicModelManager:
    """Manage BERTopic models and topic analysis."""
    
    def __init__(self, model_dir: str = "models/topic_models"):
        """Initialize topic model manager."""
        self.model_dir = model_dir
        self.embedding_model = None
        self.topic_model = None
        self.evolution_tracker = TopicEvolutionTracker()
        
        # Create model directory
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize components
        self._setup_embedding_model()
        self._setup_topic_model()
    
    def _setup_embedding_model(self):
        """Setup sentence transformer model for embeddings."""
        try:
            # Use a model that works well for general content
            model_name = "all-MiniLM-L6-v2"
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise
    
    def _setup_topic_model(self):
        """Setup BERTopic model with custom configuration."""
        try:
            # Configure UMAP for dimensionality reduction
            umap_model = UMAP(
                n_neighbors=15,
                n_components=5,
                min_dist=0.0,
                metric='cosine',
                random_state=42
            )
            
            # Configure HDBSCAN for clustering
            hdbscan_model = HDBSCAN(
                min_cluster_size=5,
                metric='euclidean',
                cluster_selection_method='eom',
                prediction_data=True
            )
            
            # Configure CountVectorizer for topic representation
            vectorizer_model = CountVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                min_df=2,
                max_df=0.8
            )
            
            # Create BERTopic model
            self.topic_model = BERTopic(
                embedding_model=self.embedding_model,
                umap_model=umap_model,
                hdbscan_model=hdbscan_model,
                vectorizer_model=vectorizer_model,
                language="english",
                calculate_probabilities=True,
                verbose=True
            )
            
            logger.info("Initialized BERTopic model")
            
        except Exception as e:
            logger.error(f"Failed to setup topic model: {str(e)}")
            raise
    
    def train_topic_model(self, documents: List[str], 
                         document_ids: Optional[List[str]] = None,
                         timestamps: Optional[List[datetime]] = None) -> TopicModelingResult:
        """Train topic model on document collection."""
        import time
        start_time = time.time()
        
        if not documents:
            raise ValueError("No documents provided for training")
        
        # Filter out very short documents
        min_length = 50
        filtered_docs = []
        filtered_ids = []
        filtered_timestamps = []
        
        for i, doc in enumerate(documents):
            if len(doc.strip()) >= min_length:
                filtered_docs.append(doc)
                if document_ids:
                    filtered_ids.append(document_ids[i])
                if timestamps:
                    filtered_timestamps.append(timestamps[i])
        
        if len(filtered_docs) < 5:
            raise ValueError("Not enough valid documents for topic modeling")
        
        logger.info(f"Training topic model on {len(filtered_docs)} documents")
        
        try:
            # Train the model
            topics, probabilities = self.topic_model.fit_transform(filtered_docs)
            
            # Get topic information
            topic_info = self.topic_model.get_topic_info()
            
            # Create topic objects
            topics_list = []
            for _, row in topic_info.iterrows():
                if row['Topic'] == -1:  # Skip outlier topic
                    continue
                    
                topic_words = self.topic_model.get_topic(row['Topic'])
                keywords = [word for word, _ in topic_words[:10]]
                
                # Get representative documents
                representative_docs = self._get_representative_documents(
                    row['Topic'], filtered_docs, topics, max_docs=3
                )
                
                topic = TopicInfo(
                    topic_id=row['Topic'],
                    name=f"Topic {row['Topic']}",
                    description=self._generate_topic_description(keywords),
                    keywords=keywords,
                    size=row['Count'],
                    coherence_score=0.0,  # Calculate separately if needed
                    representative_docs=representative_docs,
                    created_at=datetime.now(),
                    last_updated=datetime.now()
                )
                topics_list.append(topic)
            
            # Create document-topic assignments
            document_topics = []
            for i, (topic_id, prob) in enumerate(zip(topics, probabilities)):
                if topic_id == -1:  # Skip outlier assignments
                    continue
                    
                doc_topic = DocumentTopic(
                    document_id=filtered_ids[i] if filtered_ids else str(i),
                    topic_id=topic_id,
                    probability=prob[topic_id] if prob is not None else 0.0,
                    text=filtered_docs[i][:200] + "...",  # Truncated text
                    timestamp=filtered_timestamps[i] if filtered_timestamps else None
                )
                document_topics.append(doc_topic)
            
            # Update evolution tracker
            if filtered_timestamps:
                self._update_evolution_tracker(document_topics)
            
            processing_time = time.time() - start_time
            
            # Calculate overall coherence (simplified)
            coherence_score = self._calculate_coherence_score(topics_list)
            
            result = TopicModelingResult(
                topics=topics_list,
                document_topics=document_topics,
                model_info={
                    "num_topics": len(topics_list),
                    "num_documents": len(filtered_docs),
                    "outlier_documents": topics.count(-1),
                    "model_type": "BERTopic"
                },
                processing_time=processing_time,
                coherence_score=coherence_score
            )
            
            logger.info(f"Topic modeling completed in {processing_time:.2f}s")
            logger.info(f"Discovered {len(topics_list)} topics from {len(filtered_docs)} documents")
            
            return result
            
        except Exception as e:
            logger.error(f"Topic modeling failed: {str(e)}")
            raise
    
    def _get_representative_documents(self, topic_id: int, documents: List[str], 
                                    topics: List[int], max_docs: int = 3) -> List[str]:
        """Get representative documents for a topic."""
        topic_docs = [doc for i, doc in enumerate(documents) if topics[i] == topic_id]
        
        # Return first few documents as representatives (could be improved with similarity scoring)
        return topic_docs[:max_docs]
    
    def _generate_topic_description(self, keywords: List[str]) -> str:
        """Generate a readable description from topic keywords."""
        if not keywords:
            return "No description available"
        
        # Simple description generation using top keywords
        if len(keywords) >= 3:
            return f"Discussion about {keywords[0]}, {keywords[1]}, and {keywords[2]}"
        elif len(keywords) == 2:
            return f"Discussion about {keywords[0]} and {keywords[1]}"
        else:
            return f"Discussion about {keywords[0]}"
    
    def _calculate_coherence_score(self, topics: List[TopicInfo]) -> float:
        """Calculate overall coherence score for topics."""
        if not topics:
            return 0.0
        
        # Simplified coherence calculation
        # In practice, you'd use more sophisticated coherence measures
        return 0.75  # Placeholder
    
    def _update_evolution_tracker(self, document_topics: List[DocumentTopic]):
        """Update topic evolution tracker with new observations."""
        topic_counts = Counter()
        topic_timestamps = defaultdict(list)
        
        for doc_topic in document_topics:
            if doc_topic.timestamp:
                topic_counts[doc_topic.topic_id] += 1
                topic_timestamps[doc_topic.topic_id].append(doc_topic.timestamp)
        
        # Add observations to tracker
        for topic_id, count in topic_counts.items():
            if topic_timestamps[topic_id]:
                avg_timestamp = min(topic_timestamps[topic_id])  # Use earliest timestamp
                strength = count / len(document_topics)  # Relative strength
                self.evolution_tracker.add_topic_observation(topic_id, avg_timestamp, strength)
    
    def predict_topics(self, documents: List[str]) -> List[Tuple[int, float]]:
        """Predict topics for new documents."""
        if not self.topic_model:
            raise ValueError("Topic model not trained yet")
        
        try:
            topics, probabilities = self.topic_model.transform(documents)
            
            results = []
            for i, (topic_id, prob) in enumerate(zip(topics, probabilities)):
                confidence = prob[topic_id] if prob is not None and topic_id != -1 else 0.0
                results.append((topic_id, confidence))
            
            return results
            
        except Exception as e:
            logger.error(f"Topic prediction failed: {str(e)}")
            raise
    
    def get_topic_trends(self, days_back: int = 30) -> Dict[int, float]:
        """Get topic trends over time."""
        return self.evolution_tracker.get_topic_trends(days_back)
    
    def get_emerging_topics(self, threshold_days: int = 7) -> List[int]:
        """Get list of recently emerging topics."""
        emerging = []
        for topic_id in self.evolution_tracker.topic_timeline.keys():
            if self.evolution_tracker.detect_topic_emergence(topic_id, threshold_days):
                emerging.append(topic_id)
        return emerging
    
    def get_declining_topics(self, threshold_ratio: float = 0.5) -> List[int]:
        """Get list of declining topics."""
        declining = []
        for topic_id in self.evolution_tracker.topic_timeline.keys():
            if self.evolution_tracker.detect_topic_decline(topic_id, threshold_ratio):
                declining.append(topic_id)
        return declining
    
    def save_model(self, model_name: str):
        """Save trained topic model to disk."""
        if not self.topic_model:
            raise ValueError("No topic model to save")
        
        model_path = os.path.join(self.model_dir, f"{model_name}.pkl")
        tracker_path = os.path.join(self.model_dir, f"{model_name}_tracker.pkl")
        
        try:
            # Save BERTopic model
            with open(model_path, 'wb') as f:
                pickle.dump(self.topic_model, f)
            
            # Save evolution tracker
            with open(tracker_path, 'wb') as f:
                pickle.dump(self.evolution_tracker, f)
            
            logger.info(f"Saved topic model to {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            raise
    
    def load_model(self, model_name: str):
        """Load topic model from disk."""
        model_path = os.path.join(self.model_dir, f"{model_name}.pkl")
        tracker_path = os.path.join(self.model_dir, f"{model_name}_tracker.pkl")
        
        try:
            # Load BERTopic model
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    self.topic_model = pickle.load(f)
                logger.info(f"Loaded topic model from {model_path}")
            
            # Load evolution tracker
            if os.path.exists(tracker_path):
                with open(tracker_path, 'rb') as f:
                    self.evolution_tracker = pickle.load(f)
                logger.info(f"Loaded evolution tracker from {tracker_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise
    
    def visualize_topics(self, width: int = 800, height: int = 600) -> str:
        """Generate topic visualization HTML."""
        if not self.topic_model:
            raise ValueError("No topic model available for visualization")
        
        try:
            # Generate topic visualization
            fig = self.topic_model.visualize_topics(width=width, height=height)
            return fig.to_html()
            
        except Exception as e:
            logger.error(f"Topic visualization failed: {str(e)}")
            return "<p>Visualization not available</p>"
    
    def get_topic_hierarchy(self) -> Optional[str]:
        """Generate hierarchical topic visualization."""
        if not self.topic_model:
            return None
        
        try:
            # Generate hierarchical topics
            hierarchical_topics = self.topic_model.hierarchical_topics(docs=None)
            fig = self.topic_model.visualize_hierarchy(hierarchical_topics=hierarchical_topics)
            return fig.to_html()
            
        except Exception as e:
            logger.error(f"Hierarchical visualization failed: {str(e)}")
            return None


# Global topic model manager instance
_topic_manager = None


def get_topic_manager() -> TopicModelManager:
    """Get or create global topic model manager instance."""
    global _topic_manager
    
    if _topic_manager is None:
        _topic_manager = TopicModelManager()
    
    return _topic_manager


def analyze_transcript_topics(transcript_texts: List[str],
                            transcript_ids: Optional[List[str]] = None,
                            timestamps: Optional[List[datetime]] = None) -> TopicModelingResult:
    """Analyze topics in transcript collection."""
    manager = get_topic_manager()
    return manager.train_topic_model(transcript_texts, transcript_ids, timestamps)


def predict_document_topics(documents: List[str]) -> List[Tuple[int, float]]:
    """Predict topics for new documents."""
    manager = get_topic_manager()
    return manager.predict_topics(documents)