"""
Example routes for the DevDox AI Portal API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

# Create router
router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_examples():
    """
    Get a list of examples.
    
    Returns:
        List[Dict[str, Any]]: A list of example items.
    """
    examples = [
        {"id": 1, "name": "Example 1", "description": "First example"},
        {"id": 2, "name": "Example 2", "description": "Second example"},
    ]
    return examples

@router.get("/{example_id}", response_model=Dict[str, Any])
async def get_example(example_id: int):
    """
    Get a specific example by ID.
    
    Args:
        example_id (int): The ID of the example to retrieve.
        
    Returns:
        Dict[str, Any]: The example details.
        
    Raises:
        HTTPException: If the example is not found.
    """
    examples = {
        1: {"id": 1, "name": "Example 1", "description": "First example"},
        2: {"id": 2, "name": "Example 2", "description": "Second example"},
    }
    
    if example_id not in examples:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Example with ID {example_id} not found"
        )
    
    return examples[example_id]
