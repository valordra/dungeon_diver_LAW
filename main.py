import random
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from models import *

app = FastAPI()
templates = Jinja2Templates(directory="templates")

global current_player
current_player: Player

global current_enemy
current_enemy: Enemy


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("homepage.html", {"request": request})


@app.get("/ask_name", response_class=HTMLResponse)
async def ask_name(request: Request):
    ask_prompt = "What is your name, player?"
    return templates.TemplateResponse("ask_name.html", {"request": request, "ask_prompt": ask_prompt})


@app.post("/create_player", response_class=HTMLResponse)
async def create_player(request: Request, player_name: str = Form(...)):
    print(player_name)
    global current_player
    current_player = Player(name=player_name)
    print(f"""
    Successfully created player {current_player.name}!"
    Stats:
    Health: {current_player.health_max}
    Attack: {current_player.attack}
    Defense: {current_player.defense}
    Level: {current_player.level}
    Current XP: {current_player.xp_current}
    """)
    return templates.TemplateResponse("main.html", {"request": request, "player": current_player,
                                                    "level_up_message": "You start your journey unto the dungeon..."})


def check_level_up():
    global current_player
    if current_player.xp_current > current_player.xp_needed:
        current_player.xp_overflow = current_player.xp_needed - current_player.xp_current
        current_player.level += 1
        current_player.xp_needed = int(10 * 1.75 ** current_player.level)
        current_player.heals = 3
        current_player.xp_current = current_player.xp_overflow
        current_player.xp_overflow = 0

        current_player.health_max += 5
        current_player.health_current = current_player.health_max
        current_player.attack += 3
        current_player.defense += 2

        return f"{current_player.name} levelled up!"
    return ""


@app.get("/main", response_class=HTMLResponse)
async def main(request: Request):
    global current_player
    level_up_message = check_level_up()
    return templates.TemplateResponse("main.html", {"request": request, "player": current_player,
                                                    "level_up_message": level_up_message})


def generate_enemy(base_level: int):
    if base_level < 1:
        base_level = 1
    name = "Enemy"
    health = random.randint(int(base_level * 0.2) + 5, int(base_level * 1.25) + 5)
    attack = random.randint(int(base_level * 0.2) + 1, int(base_level * 0.8) + 1)
    defense = random.randint(int(base_level * 0.25) + 1, int(base_level) + 1)
    new_enemy = Enemy(
        level=base_level,
        name=name,
        health=health,
        heals=1,
        attack=attack,
        defense=defense,
        xp_reward=int(5 * 1.25 ** base_level),
    )
    return new_enemy


def attack(attacker: Entity, defender: Entity, super_attack: bool = False, block: bool = False):
    attack_modifier = 1
    if super_attack:
        attack_modifier = 3

    defense_modifier = 1
    if block:
        defense_modifier = 3

    damage = attacker.attack * attack_modifier - (defender.defense * defense_modifier * 0.5)
    if damage < 1:
        damage = 1
    defender.health_current -= damage
    return damage


def heal(healer: Entity):
    healer.heals -= 1
    healer.health_current += int(healer.health_max * 0.75)
    overhealed = 0

    if healer.health_current > healer.health_max:
        overhealed = healer.health_current - healer.health_max
        healer.health_current = healer.health_max

    healed = int(healer.health_max * 0.75 - overhealed)
    return healed


@app.get("/encounter", response_class=HTMLResponse)
async def encounter(request: Request):
    global current_player
    enemy_level_offset = random.randint(-2, 3)
    new_enemy = generate_enemy(current_player.level - enemy_level_offset)

    global current_enemy
    current_enemy = new_enemy

    return templates.TemplateResponse("encounter.html",
                                      {"request": request, "player": current_player,
                                       "player_message": "You're facing the enemy.",
                                       "enemy": current_enemy,
                                       "enemy_message": "The enemy faces you."})


def check_highscore():
    scores = []
    global current_player
    scores.append((current_player.name, current_player.current_streak))
    with open("highscores.txt", "r") as highscores:
        for line in highscores.readlines():
            arguments = line.split(' - ')
            name = "".join(arguments[:-1])
            score = int(arguments[-1])
            scores.append((name, score))
    print(scores)
    scores.sort(key=lambda x: x[1], reverse=True)
    counter = 0
    with open("highscores.txt", "w+") as highscores:
        for name, score in scores:
            if counter >= 5:
                break
            highscores.write(name + ' - ' + str(score) + '\n')
            counter += 1
    if len(scores) > 5:
        return scores[:5]
    else:
        return scores


@app.get("/encounter/{action}", response_class=HTMLResponse)
async def encounter(request: Request, action: str):
    global current_player
    global current_enemy

    player_message = ""
    player_blocked = False
    enemy_message = ""

    # Player action
    if action == "heal":
        if current_player.heals > 0:
            healed = heal(current_player)
            player_message = f"{current_player.name} healed {healed} health points!"
        else:
            player_message = "Out of healing!"
    elif action == "attack":
        damage = attack(current_player, current_enemy)
        player_message = f"{current_player.name} attacked {current_enemy.name} for {damage} health points!"
    elif action == "block":
        player_blocked = True
        player_message = f"{current_player.name} is blocking!"
    elif action == "pass":
        player_message = f"{current_player.name} did nothing !?!"

    if current_enemy.health_current <= 0:
        xp_reward = current_enemy.xp_reward
        current_player.current_streak += 1
        current_player.xp_current += xp_reward
        return templates.TemplateResponse("reward.html",
                                          {"request": request, "player": current_player,
                                           "xp_reward": xp_reward})

    # Enemy action
    enemy_action = random.choices(['attack', 'pass', 'heal'], weights=[6, 3, 1])[0]
    if enemy_action == "heal":
        if current_enemy.heals > 0:
            enemy_healed = heal(current_enemy)
            enemy_message = f"{current_enemy.name} healed {enemy_healed} health points!"
        else:
            enemy_message = f"{current_enemy.name} did nothing?!"
    elif enemy_action == "attack":
        enemy_damage = attack(current_enemy, current_player, block=player_blocked)
        enemy_message = f"{current_enemy.name} damaged {current_player.name} for {enemy_damage} health points!"
    elif enemy_action == "pass":
        enemy_message = f"{current_enemy.name} did nothing?!"

    if current_player.health_current <= 0:
        highscores = check_highscore()
        return templates.TemplateResponse("game_over.html",
                                          {"request": request, "player": current_player, "highscores": highscores})

    return templates.TemplateResponse("encounter.html",
                                      {"request": request, "player": current_player, "player_message": player_message,
                                       "enemy": current_enemy, "enemy_message": enemy_message})
