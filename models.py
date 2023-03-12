from pydantic import BaseModel


class Entity(BaseModel):
    name: str = "Entity"
    health_max: int = 10
    health_current: int = 10
    heals: int = 3

    attack: int = 3

    defense: int = 2

    level: int = 1


class Player(Entity):
    xp_current: int = 0
    xp_needed: int = 10
    xp_overflow: int = 0

    current_streak: int = 0


class Enemy(Entity):
    xp_reward: int
