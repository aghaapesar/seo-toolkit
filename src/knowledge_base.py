"""
Knowledge Base Module

Manages project-specific knowledge base for tracking content generation,
avoiding duplicates, and improving prediction models over time.

Features:
- Project-based knowledge storage
- Content generation history tracking
- Duplicate detection
- CTR prediction model improvement
- Performance metrics tracking
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Manages project-specific knowledge base for SEO content optimization.
    
    Stores:
    - Generated content titles and topics
    - Historical performance data
    - CTR predictions vs actual results
    - Keyword clusters
    - Content recommendations history
    """
    
    def __init__(self, project_name: str, base_dir: str = "knowledge_base", flat: bool = False):
        """
        Initialize knowledge base for a specific project.
        
        Args:
            project_name: Name of the project (e.g., website domain)
            base_dir: Base directory for knowledge base storage
            flat: When True, use base_dir directly (multi-project layout)
        """
        self.project_name = project_name
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        if flat:
            self.project_dir = self.base_dir
        else:
            self.project_dir = self.base_dir / self._sanitize_name(project_name)
        self.project_dir.mkdir(exist_ok=True)
        
        # File paths
        self.metadata_file = self.project_dir / "metadata.json"
        self.content_history_file = self.project_dir / "content_history.json"
        self.performance_file = self.project_dir / "performance_metrics.json"
        self.clusters_file = self.project_dir / "keyword_clusters.json"
        
        # Load existing data
        self.metadata = self._load_json(self.metadata_file, self._default_metadata())
        self.content_history = self._load_json(self.content_history_file, [])
        self.performance = self._load_json(self.performance_file, {})
        self.clusters = self._load_json(self.clusters_file, [])
        
        logger.info(f"Knowledge base initialized for project: {project_name}")
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize project name for use as directory name.
        
        Args:
            name: Project name
            
        Returns:
            Sanitized name safe for filesystem
        """
        # Remove special characters, keep only alphanumeric and basic punctuation
        import re
        sanitized = re.sub(r'[^\w\-\.]', '_', name)
        return sanitized.lower()
    
    def _default_metadata(self) -> Dict:
        """Get default metadata structure."""
        return {
            "project_name": self.project_name,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_analyses": 0,
            "total_content_generated": 0,
            "total_improvements_suggested": 0
        }
    
    def _load_json(self, file_path: Path, default: any) -> any:
        """
        Load JSON file or return default if not exists.
        
        Args:
            file_path: Path to JSON file
            default: Default value if file doesn't exist
            
        Returns:
            Loaded data or default
        """
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {file_path}: {str(e)}")
                return default
        return default
    
    def _save_json(self, file_path: Path, data: any):
        """
        Save data to JSON file.
        
        Args:
            file_path: Path to JSON file
            data: Data to save
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving {file_path}: {str(e)}")
    
    def _generate_content_hash(self, title: str, keywords: List[str]) -> str:
        """
        Generate unique hash for content identification.
        
        Args:
            title: Content title
            keywords: Related keywords
            
        Returns:
            MD5 hash
        """
        content_str = f"{title}_{'-'.join(sorted(keywords))}"
        return hashlib.md5(content_str.encode('utf-8')).hexdigest()
    
    def is_duplicate_content(self, title: str, keywords: List[str], threshold: float = 0.95) -> bool:
        """
        Check if similar content already exists in history.
        
        Args:
            title: Proposed content title
            keywords: Related keywords
            threshold: Similarity threshold (0-1)
            
        Returns:
            True if duplicate found
        """
        from difflib import SequenceMatcher
        
        # Check exact match by hash
        content_hash = self._generate_content_hash(title, keywords)
        
        for item in self.content_history:
            if item.get('content_hash') == content_hash:
                logger.info(f"Exact duplicate found: {title}")
                return True
            
            # Check similarity
            existing_title = item.get('title', '')
            similarity = SequenceMatcher(None, title.lower(), existing_title.lower()).ratio()
            
            if similarity >= threshold:
                logger.info(f"Similar content found: {title} (~{similarity:.0%} similar to: {existing_title})")
                return True
        
        return False
    
    def add_generated_content(
        self,
        title: str,
        keywords: List[str],
        content_type: str,
        predicted_impressions: int,
        cluster_info: Dict = None
    ):
        """
        Add newly generated content to history.
        
        Args:
            title: Content title
            keywords: Related keywords
            content_type: Type of content (article, guide, etc.)
            predicted_impressions: Predicted monthly impressions
            cluster_info: Additional cluster information
        """
        content_hash = self._generate_content_hash(title, keywords)
        
        entry = {
            "content_hash": content_hash,
            "title": title,
            "keywords": keywords,
            "content_type": content_type,
            "predicted_impressions": predicted_impressions,
            "generated_at": datetime.now().isoformat(),
            "cluster_info": cluster_info or {},
            "status": "suggested",  # suggested, in_progress, published
            "actual_performance": None
        }
        
        self.content_history.append(entry)
        self._save_json(self.content_history_file, self.content_history)
        
        # Update metadata
        self.metadata['total_content_generated'] += 1
        self.metadata['last_updated'] = datetime.now().isoformat()
        self._save_json(self.metadata_file, self.metadata)
        
        logger.info(f"Added content to history: {title}")
    
    def add_improvement_suggestion(
        self,
        url: str,
        keywords: List[str],
        suggestions: Dict,
        current_metrics: Dict
    ):
        """
        Add content improvement suggestion to history.
        
        Args:
            url: URL being improved
            keywords: Target keywords
            suggestions: Improvement suggestions
            current_metrics: Current performance metrics
        """
        entry = {
            "url": url,
            "keywords": keywords,
            "suggestions": suggestions,
            "current_metrics": current_metrics,
            "suggested_at": datetime.now().isoformat(),
            "status": "pending",  # pending, implemented, verified
            "improvement_results": None
        }
        
        # Store in performance tracking
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        if url_hash not in self.performance:
            self.performance[url_hash] = {
                "url": url,
                "history": []
            }
        
        self.performance[url_hash]['history'].append(entry)
        self._save_json(self.performance_file, self.performance)
        
        # Update metadata
        self.metadata['total_improvements_suggested'] += 1
        self.metadata['last_updated'] = datetime.now().isoformat()
        self._save_json(self.metadata_file, self.metadata)
        
        logger.info(f"Added improvement suggestion for: {url}")
    
    def save_keyword_cluster(self, cluster: Dict):
        """
        Save keyword cluster for future reference.
        
        Args:
            cluster: Cluster information
        """
        # Add timestamp and hash
        cluster['created_at'] = datetime.now().isoformat()
        cluster['cluster_hash'] = hashlib.md5(
            json.dumps(cluster.get('keywords', []), sort_keys=True).encode()
        ).hexdigest()
        
        self.clusters.append(cluster)
        self._save_json(self.clusters_file, self.clusters)
        
        logger.info(f"Saved keyword cluster: {cluster.get('main_topic', 'Unknown')}")
    
    def get_existing_keywords(self) -> Set[str]:
        """
        Get all keywords used in previous content.
        
        Returns:
            Set of used keywords
        """
        keywords = set()
        
        for item in self.content_history:
            keywords.update(item.get('keywords', []))
        
        for cluster in self.clusters:
            keywords.update(cluster.get('keywords', []))
        
        return keywords
    
    def get_content_suggestions_history(self, limit: int = 50) -> List[Dict]:
        """
        Get recent content suggestions.
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of recent content suggestions
        """
        sorted_history = sorted(
            self.content_history,
            key=lambda x: x.get('generated_at', ''),
            reverse=True
        )
        return sorted_history[:limit]
    
    def update_content_status(self, content_hash: str, new_status: str, actual_performance: Dict = None):
        """
        Update status of generated content.
        
        Args:
            content_hash: Hash of the content
            new_status: New status (published, in_progress, etc.)
            actual_performance: Actual performance metrics if available
        """
        for item in self.content_history:
            if item.get('content_hash') == content_hash:
                item['status'] = new_status
                item['updated_at'] = datetime.now().isoformat()
                
                if actual_performance:
                    item['actual_performance'] = actual_performance
                
                self._save_json(self.content_history_file, self.content_history)
                logger.info(f"Updated content status: {content_hash} -> {new_status}")
                return
        
        logger.warning(f"Content not found: {content_hash}")
    
    def get_ctr_prediction_data(self) -> Dict:
        """
        Get historical data for CTR prediction model training.
        
        Returns:
            Dictionary with prediction vs actual data
        """
        training_data = {
            "predictions": [],
            "actuals": [],
            "features": []
        }
        
        for item in self.content_history:
            if item.get('actual_performance'):
                training_data['predictions'].append(item.get('predicted_impressions', 0))
                training_data['actuals'].append(item['actual_performance'].get('impressions', 0))
                training_data['features'].append({
                    "content_type": item.get('content_type'),
                    "keyword_count": len(item.get('keywords', [])),
                    "title_length": len(item.get('title', ''))
                })
        
        return training_data
    
    def get_statistics(self) -> Dict:
        """
        Get knowledge base statistics.
        
        Returns:
            Dictionary with statistics
        """
        published_count = sum(1 for item in self.content_history if item.get('status') == 'published')
        
        total_predicted_impressions = sum(
            item.get('predicted_impressions', 0) for item in self.content_history
        )
        
        return {
            "project_name": self.project_name,
            "total_content_suggestions": len(self.content_history),
            "published_content": published_count,
            "total_keyword_clusters": len(self.clusters),
            "unique_keywords": len(self.get_existing_keywords()),
            "total_predicted_impressions": total_predicted_impressions,
            "total_improvements_tracked": len(self.performance),
            **self.metadata
        }
    
    def export_report(self, output_path: str = None) -> str:
        """
        Export knowledge base as comprehensive report.
        
        Args:
            output_path: Optional custom output path
            
        Returns:
            Path to exported report
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.project_dir / f"report_{timestamp}.json"
        
        report = {
            "metadata": self.metadata,
            "statistics": self.get_statistics(),
            "content_history": self.content_history,
            "keyword_clusters": self.clusters,
            "performance_tracking": self.performance,
            "generated_at": datetime.now().isoformat()
        }
        
        self._save_json(Path(output_path), report)
        logger.info(f"Exported knowledge base report: {output_path}")
        
        return str(output_path)

