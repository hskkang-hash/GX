"""
Input schemas for drone communication functionality
"""
from ninja import Schema

"""
Input schemas for drone communication functionality
"""
class ChangeStatusInSchema(Schema):
    drone_uid: str
    status: str
    active: bool