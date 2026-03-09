"""
Feedback collector for human corrections.

Collects corrections from human reviewers to build data flywheel.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid


class FeedbackCollector:
    """
    Collects human corrections to improve intent recognition.
    
    Stores feedback in memory (would be database in production).
    """
    
    def __init__(self):
        """Initialize feedback collector."""
        self.storage: List[Dict[str, Any]] = []
    
    async def submit(self, feedback: Dict[str, Any]) -> str:
        """
        Submit a new feedback entry.
        
        Args:
            feedback: Feedback data dictionary
            
        Returns:
            Feedback ID
        """
        feedback_id = feedback.get("feedback_id", str(uuid.uuid4()))
        
        # Add timestamp
        feedback["created_at"] = datetime.now(timezone.utc)
        
        # Add to storage
        self.storage.append(feedback)
        
        return feedback_id
    
    async def get_pending(self) -> List[Dict[str, Any]]:
        """
        Get all pending feedback entries.
        
        Returns:
            List of pending feedback
        """
        return [
            f for f in self.storage
            if not f.get("resolved", False)
        ]
    
    async def get_by_meeting(self, meeting_id: str) -> List[Dict[str, Any]]:
        """
        Get feedback for a specific meeting.
        
        Args:
            meeting_id: Meeting ID
            
        Returns:
            List of feedback entries
        """
        return [
            f for f in self.storage
            if f.get("meeting_id") == meeting_id
        ]
    
    async def resolve(self, feedback_id: str) -> bool:
        """
        Mark feedback as resolved.
        
        Args:
            feedback_id: Feedback ID
            
        Returns:
            True if resolved, False if not found
        """
        for feedback in self.storage:
            if feedback.get("feedback_id") == feedback_id:
                feedback["resolved"] = True
                feedback["resolved_at"] = datetime.now(timezone.utc)
                return True
        return False
    
    async def export_training_data(self) -> List[Dict[str, Any]]:
        """
        Export feedback as training data for model improvement.
        
        Returns:
            List of training examples
        """
        # Filter resolved feedback only
        resolved = [f for f in self.storage if f.get("resolved", False)]
        
        # Transform to training format
        training_data = []
        for feedback in resolved:
            example = {
                "original_intent": feedback.get("original_intent"),
                "corrected_intent": feedback.get("corrected_intent"),
                "feedback_type": feedback.get("feedback_type"),
                "meeting_context": feedback.get("meeting_context")
            }
            training_data.append(example)
        
        return training_data
    
    async def clear(self) -> int:
        """
        Clear all feedback (for testing).
        
        Returns:
            Number of items cleared
        """
        count = len(self.storage)
        self.storage = []
        return count
