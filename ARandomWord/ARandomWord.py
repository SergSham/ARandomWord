import json
import telebot
import random
import time
from telebot import types
from collections import defaultdict, deque

# Initialize the bot with your token (replace 'YOUR_BOT_TOKEN' with actual token)
TOKEN = '8204537981:AAEA-CgGQEg2t9qH_8bK3bFDPGS8Kmquc9Y'
bot = telebot.TeleBot(TOKEN)

# Game state storage
games = {}  # {chat_id: game_state}
players = {}  # {user_id: player_data}
game_states = {}  # {chat_id: game_status}

# Emotion definitions with probabilities based on multipliers
EMOTIONS = {
    "Меланхолия": {"multiplier": 3, "description": "Игрок становится тихим и задумчивым. Его ставки осторожны, а реакция слегка замедлена.", "probability": 0.9},
    "Раздражение": {"multiplier": 4, "description": "Вспыльчивость. Игрок начинает спорить с дилером и другими игроками.", "probability": 0.85},
    "Зависть": {"multiplier": 5, "description": "Игрок завидует выигрышу другого игрока и чаще ставит на то, где выиграл", "probability": 0.8},
    "Сожаление": {"multiplier": 6, "description": "Постоянная оглядка на прошлые ходы. Игрок не может сосредоточиться на текущем раунде.", "probability": 0.75},
    "Подозрительность": {"multiplier": 5, "description": "Паранойя. Игроку кажется, что все вокруг сговорились против него.", "probability": 0.7},
    "Стыд": {"multiplier": 7, "description": "Желание спрятать лицо. Игрок боится делать крупные ставки.", "probability": 0.65},
    "Гнев": {"multiplier": 8, "description": "Потеря самообладания. Игрок склонен к агрессивным ставкам 'пан или пропал'.", "probability": 0.6},
    "Мучительная вина": {"multiplier": 9, "description": "Ощущение собственного недостоинства. Игрок подсознательно хочет проиграть.", "probability": 0.55},
    "Ослепляющая ненависть": {"multiplier": 10, "description": "Желание уничтожить оппонента любой ценой.", "probability": 0.4},
    "Беспросветное отчаяние": {"multiplier": 20, "description": "Ощущение пустоты. Игрок перестает ценить свою жизнь и имущество.", "probability": 0.2}
}

# Game class
class RouletteGame:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = {}  # {user_id: player_data}
        self.current_round = 0
        self.is_active = False
        self.wheel_result = None
        self.bets = defaultdict(list)  # {user_id: [bet_details]}
        self.emotion_bets = defaultdict(dict)  # {user_id: {emotion: bet_amount}}
        self.dual_bets = defaultdict(list)  # {user_id: [dual_bet_details]}
        self.all_players_made_bets = False
        self.bet_count = defaultdict(int)
        self.min_bet = 5  # Минимальная ставка
        
    def add_player(self, user_id, username):
        if user_id not in self.players:
            self.players[user_id] = {
                "username": username,
                "balance": 100,
                "emotions": defaultdict(int),  # {emotion: intensity}
                "emotion_bets": defaultdict(int),  # {emotion: bet_amount}
                "last_bet": None,
                "is_active": True
            }
            
    def remove_player(self, user_id):
        if user_id in self.players:
            del self.players[user_id]
            
    def place_bet(self, user_id, amount, number=None, emotion=None):
        if user_id not in self.players or not self.players[user_id]["is_active"]:
            return False
            
        player = self.players[user_id]

         # Проверка минимальной ставки
        if amount < self.min_bet:
          return False


        
        # Check if player has enough balance
        if player["balance"] < amount:
            return False
            
        # Deduct bet from balance
        player["balance"] -= amount
        
        # Store the bet
        bet = {
            "amount": amount,
            "number": number,
            "emotion": emotion,
            "timestamp": time.time()
        }
        
        if emotion:
            self.emotion_bets[user_id][emotion] = amount
        else:
            self.bets[user_id].append(bet)
            
        player["last_bet"] = bet
        self.bet_count[user_id] += 1
        
        return True
        
    def place_dual_bet(self, user_id, number_amount, emotion_amount, number, emotion):
        if user_id not in self.players or not self.players[user_id]["is_active"]:
            return False
            
        player = self.players[user_id]
        
        # Check if player has enough balance
        if player["balance"] < (number_amount + emotion_amount):
            return False

         # Проверка минимальной ставки
        if number_amount < self.min_bet or emotion_amount < self.min_bet:
          return False
            
        # Deduct bets from balance
        player["balance"] -= (number_amount + emotion_amount)
        
        # Store the dual bet
        dual_bet = {
            "number_amount": number_amount,
            "emotion_amount": emotion_amount,
            "number": number,
            "emotion": emotion,
            "timestamp": time.time()
        }
        
        self.dual_bets[user_id].append(dual_bet)
        
        # Add emotion to player
        player["emotions"][emotion] += emotion_amount
        
        player["last_bet"] = dual_bet
        self.bet_count[user_id] += 1
        
        return True
        
    def spin_wheel(self):
        # Generate a random result (0-32)
        self.wheel_result = random.randint(0, 32)

         # Увеличиваем минимальную ставку каждые 5 спинов
        self.current_round += 1
        if self.current_round % 5 == 0:
         self.min_bet *= 2
    
        return self.wheel_result
        
    def spin_emotion_wheel(self):
        """Второе колесо рулетки для случайного выбора эмоции по её вероятности"""
        emotions = list(EMOTIONS.keys())
        probabilities = [EMOTIONS[emotion]["probability"] for emotion in emotions]
        selected_emotion = random.choices(emotions, weights=probabilities, k=1)[0]
        return selected_emotion
        
    def process_results(self):
      results = {}
      emotion_result = self.spin_emotion_wheel()
    
    # Process regular number bets
      for user_id, bets in self.bets.items():
        player = self.players[user_id]
        winnings = 0
        
        for bet in bets:
            if bet["number"] == self.wheel_result:
                winnings += bet["amount"] * 2
                
        if winnings > 0:
            player["balance"] += winnings
            results[user_id] = {"type": "number", "winnings": winnings, "bet": bet}
    
    # Process emotion bets
      for user_id, emotion_bets in self.emotion_bets.items():
        player = self.players[user_id]
        winnings = 0
        
        for emotion, bet_amount in emotion_bets.items():
            # Check if the player has this emotion
            if emotion == emotion_result:
                # Calculate winnings based on multiplier
                multiplier = EMOTIONS[emotion]["multiplier"]
                winnings += bet_amount * multiplier
                
                # Reduce emotion intensity
                player["emotions"][emotion] = max(0, player["emotions"][emotion] - bet_amount)
                
        if winnings > 0:
            player["balance"] += winnings
            results[user_id] = {"type": "emotion", "winnings": winnings, "emotion": emotion_result}
        else:
            # Если не угадали эмоцию, вычитаем ставку из баланса
            for emotion, bet_amount in emotion_bets.items():
                player["balance"] -= bet_amount
                # Добавляем эмоцию игроку при проигрыше
                if emotion in player["emotions"]:
                    player["emotions"][emotion] += bet_amount
                else:
                    player["emotions"][emotion] = bet_amount
    
    # Process dual bets - только если выпадают оба условия
      for user_id, dual_bets in self.dual_bets.items():
        player = self.players[user_id]
        winnings = 0
        
        for dual_bet in dual_bets:
            # Проверяем, что выпало и число, и эмоция
            if dual_bet["number"] == self.wheel_result and dual_bet["emotion"] == emotion_result:
                # Для дуэльных ставок выигрыш только если выпадают оба условия
                multiplier = EMOTIONS[dual_bet["emotion"]]["multiplier"]
                winnings += (dual_bet["number_amount"] + dual_bet["emotion_amount"]) * multiplier * 2
                
        if winnings > 0:
            player["balance"] += winnings
            results[user_id] = {"type": "dual", "winnings": winnings, "number": dual_bet["number"], "emotion": dual_bet["emotion"]}
                
      return results, emotion_result
        
    def reset_bets(self):
        """Очистка всех ставок после завершения раунда"""
        self.bets.clear()
        self.emotion_bets.clear()
        self.dual_bets.clear()
        self.bet_count.clear()
        self.all_players_made_bets = False
        
    def check_all_players_bets(self):
        """Проверяет, сделали ли все игроки ставки"""
        if len(self.players) == 0:
            return False
            
        # Проверяем, что все активные игроки сделали хотя бы одну ставку
        for user_id, player in self.players.items():
            if player["is_active"] and self.bet_count[user_id] == 0:
                return False
        return True

# Bot commands
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "Добро пожаловать в рулетку с негативными эмоциями! 🎰\n\n"
        "Напишите /newgame чтобы создать новую игру.\n"
        "Правила:\n"
        "• Ставки на числа от 0 до 32\n"
        "• Ставки на негативные эмоции с различными множителями\n"
        "• Выигрыш: вы получаете множитель по вашей ставке\n"
        "• Проигрыш: вы теряете фишки и получаете негативную эмоцию\n"
        "• Количество игроков не ограниченно\n"
        "• Прочитать подробные правила - напишите /rules\n\n"
        "Используйте /help для подробной информации.")

@bot.message_handler(commands=['newgame'])
def create_game(message):
    chat_id = message.chat.id
    
    if chat_id in games:
        bot.reply_to(message, "В этом чате уже есть активная игра. Завершите её или используйте /endgame.")
        return
        
    game = RouletteGame(chat_id)
    games[chat_id] = game
    game_states[chat_id] = "waiting"
    
    # Add the creator as player
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    game.add_player(user_id, username)
    
    bot.reply_to(message, 
        f"Игра создана! 🎉\n\n"
        f"Игроки: {username}\n"
        f"Используйте /join чтобы присоединиться к игре.\n"
        f"Когда будет достаточно игроков, начните игру командой /begingame.")

@bot.message_handler(commands=['join'])
def join_game(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    if chat_id not in games:
        bot.reply_to(message, "Нет активной игры в этом чате. Создайте новую командой /newgame.")
        return
        
    game = games[chat_id]
    
    # Add player to the game
    game.add_player(user_id, username)
    
    # Update player list
    player_list = "\n".join([f"• @{player['username']}" for player in game.players.values()])
    
    bot.reply_to(message, 
        f"Вы присоединились к игре!\n\n"
        f"Текущие игроки:\n{player_list}\n\n"
        f"Когда будет достаточно игроков, начните игру командой /begingame.")

@bot.message_handler(commands=['begingame'])
def start_game(message):
    chat_id = message.chat.id
    
    if chat_id not in games:
        bot.reply_to(message, "Нет активной игры в этом чате. Создайте новую командой /newgame.")
        return
        
    game = games[chat_id]
    
    if len(game.players) < 1:
        bot.reply_to(message, "Для начала игры нужно как минимум 1 игрок. Используйте /join чтобы присоединиться.")
        return
        
    game_states[chat_id] = "active"
    game.is_active = True
    
    # Send welcome message to players
    player_list = "\n".join([f"• @{player['username']}" for player in game.players.values()])
    
    bot.send_message(chat_id, 
        f"Игра началась! 🎰\n\n"
        f"Игроки:\n{player_list}\n\n"
        f"Сделайте ставки с помощью команд:\n"
        f"/bet_number <количество> <номер>\n"
        f"/bet_emotion <количество> <эмоция>\n"
        f"/bet_dual <количество числа> <количество эмоции> <номер> <эмоция>\n\n"
        f"Примеры:\n"
        f"/bet_number 5 17\n"
        f"/bet_emotion 3 Стыд\n"
        f"/bet_dual 2 4 17 Стыд\n"
        f"Подсказка: чтобы дополнить команду bet зажмите её. На десктопной версии нажать Tab"
        )

@bot.message_handler(commands=['endgame'])
def end_game(message):
    chat_id = message.chat.id
    
    if chat_id not in games:
        bot.reply_to(message, "Нет активной игры в этом чате.")
        return
        
    del games[chat_id]
    game_states[chat_id] = "ended"
    
    bot.reply_to(message, "Игра завершена.")

@bot.message_handler(commands=['bet_number'])
def place_number_bet(message):
    chat_id = message.chat.id
    
    if chat_id not in games or game_states[chat_id] != "active":
        bot.reply_to(message, "Нет активной игры. Создайте новую командой /newgame.")
        return
        
    try:
        parts = message.text.split()
        amount = int(parts[1])
        number = int(parts[2])
        
        if number < 0 or number > 32:
            bot.reply_to(message, "Номер должен быть от 0 до 32.")
            return
            
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        
        game = games[chat_id]

        if amount < game.min_bet:
            bot.reply_to(message, f"Минимальная ставка: {game.min_bet} фишек")
            return
        
        if not game.place_bet(user_id, amount, number=number):
            bot.reply_to(message, "Недостаточно средств или вы не в игре.")
            return
            
        bot.reply_to(message, 
            f"Вы поставили {amount} фишек на число {number}!\n"
            f"Баланс: {game.players[user_id]['balance']}")

    except (ValueError, IndexError):
        bot.reply_to(message, "Неправильный формат. Используйте: /bet_number <количество> <номер>")

@bot.message_handler(commands=['bet_emotion'])
def place_emotion_bet(message):
    chat_id = message.chat.id
    
    if chat_id not in games or game_states[chat_id] != "active":
        bot.reply_to(message, "Нет активной игры. Создайте новую командой /newgame.")
        return
        
    try:
        parts = message.text.split()
        amount = int(parts[1])
        emotion = " ".join(parts[2:])
        
        if emotion not in EMOTIONS:
            bot.reply_to(message, 
                f"Неверная эмоция. Доступные эмоции:\n"
                + "\n".join([f"• {e}" for e in EMOTIONS.keys()]))
            return
            
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        
        game = games[chat_id]

        if amount < game.min_bet:
            bot.reply_to(message, f"Минимальная ставка: {game.min_bet} фишек")
            return
        
        if not game.place_bet(user_id, amount, emotion=emotion):
            bot.reply_to(message, "Недостаточно средств или вы не в игре.")
            return
            
        # Add emotion to player
        game.players[user_id]["emotions"][emotion] += amount
        
        bot.reply_to(message, 
            f"Вы поставили {amount} фишек на эмоцию '{emotion}'!\n"
            f"Баланс: {game.players[user_id]['balance']}")

    except (ValueError, IndexError):
        bot.reply_to(message, "Неправильный формат. Используйте: /bet_emotion <количество> <эмоция>")

@bot.message_handler(commands=['bet_dual'])
def place_dual_bet(message):
    chat_id = message.chat.id
    
    if chat_id not in games or game_states[chat_id] != "active":
        bot.reply_to(message, "Нет активной игры. Создайте новую командой /newgame.")
        return
        
    try:
        parts = message.text.split()
        number_amount = int(parts[1])
        emotion_amount = int(parts[2])
        number = int(parts[3])
        emotion = " ".join(parts[4:])
        
        if number < 0 or number > 32:
            bot.reply_to(message, "Номер должен быть от 0 до 32.")
            return
            
        if emotion not in EMOTIONS:
            bot.reply_to(message, 
                f"Неверная эмоция. Доступные эмоции:\n"
                + "\n".join([f"• {e}" for e in EMOTIONS.keys()]))
            return
            
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        
        game = games[chat_id]

        if number_amount < game.min_bet or emotion_amount < game.min_bet:
            bot.reply_to(message, f"Минимальная ставка: {game.min_bet} фишек")
            return
        
        if not game.place_dual_bet(user_id, number_amount, emotion_amount, number, emotion):
            bot.reply_to(message, "Недостаточно средств или вы не в игре.")
            return
            
        # Add emotion to player
        game.players[user_id]["emotions"][emotion] += emotion_amount
        
        bot.reply_to(message, 
            f"Вы поставили {number_amount} фишек на число {number} и {emotion_amount} фишек на эмоцию '{emotion}'!\n"
            f"Баланс: {game.players[user_id]['balance']}")

    except (ValueError, IndexError):
        bot.reply_to(message, "Неправильный формат. Используйте: /bet_dual <количество числа> <количество эмоции> <номер> <эмоция>")

@bot.message_handler(commands=['spin'])
def spin_wheel(message):
    chat_id = message.chat.id
    
    if chat_id not in games or game_states[chat_id] != "active":
        bot.reply_to(message, "Нет активной игры. Создайте новую командой /newgame.")
        return
        
    game = games[chat_id]
    
    # Проверяем, сделали ли все игроки ставки
    if not game.check_all_players_bets():
        bot.reply_to(message, "Не все игроки сделали ставки. Дождитесь всех ставок.")
        return
    
    # Spin the wheel
    result = game.spin_wheel()
    
    # Process results
    results, emotion_result = game.process_results()
    
    # Send results to players
    message_text = f"Колесо рулетки остановилось на числе {result}! 🎰\n"
    message_text += f"Второе колесо рулетки выпало: {emotion_result}!\n\n"
    
    # Track which players received the emotion
    emotion_winners = []
    
    if not results:
        message_text += "Никто не выиграл. Попробуйте снова!"
    else:
        for user_id, result_data in results.items():
            player = game.players[user_id]
            username = player["username"]
            
            if result_data["type"] == "number":
                message_text += f"@{username} выиграл {result_data['winnings']} фишек на ставке на число {result_data['bet']['number']}!\n"
            elif result_data["type"] == "emotion":
                # Проверяем, выиграл ли игрок на эмоцию
                if result_data["emotion"] == emotion_result:
                    message_text += f"@{username} выиграл {result_data['winnings']} фишек на эмоции '{result_data['emotion']}'!\n"
                    emotion_winners.append(username)
                else:
                    # Игрок проиграл на эмоцию
                    if result_data["emotion"] in player["emotions"]:
                        message_text += f"@{username} проиграл ставку на эмоцию '{result_data['emotion']}'!\n"
                        # Увеличиваем интенсивность эмоции в 2 раза
                        player["emotions"][result_data["emotion"]] *= 2
                    else:
                        message_text += f"@{username} проиграл ставку на эмоцию '{result_data['emotion']}' и получил её!\n"
                        player["emotions"][result_data["emotion"]] = result_data["winnings"]
            elif result_data["type"] == "dual":
                # Dual bet
                if result_data["emotion"] == emotion_result:
                    message_text += f"@{username} выиграл {result_data['winnings']} фишек на эмоции '{result_data['emotion']}'!\n"
                    emotion_winners.append(username)
                else:
                    if result_data["emotion"] in player["emotions"]:
                        message_text += f"@{username} проиграл ставку на эмоцию '{result_data['emotion']}'!\n"
                        player["emotions"][result_data["emotion"]] *= 2
                    else:
                        message_text += f"@{username} проиграл ставку на эмоцию '{result_data['emotion']}' и получил её!\n"
                        player["emotions"][result_data["emotion"]] = result_data["winnings"]
    
        
    message_text += "\nТекущие балансы:\n"
    for user_id, player in game.players.items():
        username = player["username"]
        balance = player["balance"]
        message_text += f"@{username}: {balance} фишек\n"
        
    bot.send_message(chat_id, message_text)
    
    # Очищаем ставки после завершения раунда
    game.reset_bets()


@bot.message_handler(commands=['balance'])
def show_balance(message):
    chat_id = message.chat.id
    
    if chat_id not in games or game_states[chat_id] != "active":
        bot.reply_to(message, "Нет активной игры. Создайте новую командой /newgame.")
        return
        
    user_id = message.from_user.id
    game = games[chat_id]
    
    if user_id not in game.players:
        bot.reply_to(message, "Вы не участвуете в этой игре.")
        return
        
    balance = game.players[user_id]["balance"]
    bot.reply_to(message, f"Ваш баланс: {balance} фишек")

# Добавим обработчик для отображения списка эмоций
@bot.message_handler(commands=['emotions'])
def show_emotions(message):
    text = "Доступные негативные эмоции:\n\n"
    for emotion, data in EMOTIONS.items():
        text += f"{emotion} - множитель {data['multiplier']}\n"
        text += f"  {data['description']}\n\n"
    bot.reply_to(message, text)

# Добавим обработчик для отображения информации о конкретной эмоции
@bot.message_handler(commands=['emotion_info'])
def show_emotion_info(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Используйте: /emotion_info <название эмоции>")
            return
            
        emotion_name = " ".join(parts[1:])
        
        if emotion_name in EMOTIONS:
            data = EMOTIONS[emotion_name]
            text = f"{emotion_name}\n"
            text += f"Множитель: {data['multiplier']}\n"
            text += f"Описание: {data['description']}\n"
            text += f"Вероятность выпадения: {data['probability'] * 100:.1f}%"
            bot.reply_to(message, text)
        else:
            bot.reply_to(message, "Эмоция не найдена. Используйте /emotions для просмотра всех доступных эмоций.")
            
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

# Добавим обработчик для отображения информации о правилах
@bot.message_handler(commands=['rules'])
def show_rules(message):
    rules = """
Правила игры в рулетку с негативными эмоциями:

1. Ставки на числа:
   - От 0 до 32
   - Выигрыш умножается на 2 от ставки

2. Ставки на эмоции:
   - Вместо черного и красного есть 10 негативных эмоций. см. по команде /emotions
   - Множитель выигрыша зависит от силы эмоции (от 3 до 20)
   - Вероятность выпадения эмоции обратно пропорциональна её множителю

3. Выигрыш:
   - Вы получаете в два раза большее количество фишек если ставили только на число или количество фишек умноженное на коэффициент эмоции, если ставили на негативную эмоцию. 
   - Если у вас уже была негатиная эмоция, то эффект ослабевает пропорционально вашей текущей ставке относительно той, когда вы проиграли
   - Двойная ставка (bet_dual) выигрывает только в случае, если выпали одновременно и число и эмоция. 

4. Проигрыш:
   - Вы теряете поставленные фишки.
   - Получаете негативную эмоцию.
   - Если у вас уже была негативная эмоция и вы проиграли на ней повторно, то эмоция усиливается.
   - Информацию о количестве фишек, которое надо отыграть, чтобы негативная эмоция пропала см. в профиле игрока по команде /player_info

5. Ограничения:
   - Начальная минимальная ставка - 5 фишек.
   - Каждые 5 вращений минимальная ставка удваивается.
   - За один раунд можно делать неограниченное количество ставок.
   - Минимальное количество игроков - 1.
   - Максимальное количество комнат для игры - 1.
   - Если начать новую игру, завершить текущую игру или покунуть её командой /leave ваш прогресс не сохранится.
   - Спустя 5 минут после отсутствия активности в боте (отправление команд) игра сбрасывается.


"""
    bot.reply_to(message, rules)

# Обработчик для отображения статуса игры
@bot.message_handler(commands=['status'])
def show_game_status(message):
    chat_id = message.chat.id
    
    if chat_id not in games:
        bot.reply_to(message, "Нет активной игры.")
        return
        
    game = games[chat_id]
    
    status_text = f"Статус игры:\n"
    status_text += f"Активна: {'Да' if game.is_active else 'Нет'}\n"
    status_text += f"Количество игроков: {len(game.players)}\n"
    status_text += f"Текущий результат: {game.wheel_result if game.wheel_result is not None else 'Не сыграно'}\n"
    
    bot.reply_to(message, status_text)

# Обработчик для отображения информации о игроке
@bot.message_handler(commands=['player_info'])
def show_player_info(message):
    chat_id = message.chat.id
    
    if chat_id not in games or game_states[chat_id] != "active":
        bot.reply_to(message, "Нет активной игры.")
        return
        
    user_id = message.from_user.id
    game = games[chat_id]
    
    if user_id not in game.players:
        bot.reply_to(message, "Вы не участвуете в этой игре.")
        return
        
    player = game.players[user_id]
    text = f"Информация о игроке:\n"
    text += f"Имя: @{message.from_user.username}\n"
    text += f"Баланс: {player['balance']} фишек\n"
    
    if player['emotions']:
        text += "Негативные эмоции:\n"
        for emotion, intensity in player['emotions'].items():
            text += f"  {emotion}: {intensity} фишек\n"
    else:
        text += "Негативных эмоций нет\n"
        
    bot.reply_to(message, text)

# Обработчик для отображения истории ставок
@bot.message_handler(commands=['history'])
def show_bet_history(message):
    chat_id = message.chat.id
    
    if chat_id not in games or game_states[chat_id] != "active":
        bot.reply_to(message, "Нет активной игры.")
        return
        
    user_id = message.from_user.id
    game = games[chat_id]
    
    if user_id not in game.players:
        bot.reply_to(message, "Вы не участвуете в этой игре.")
        return
        
    # Пока что просто показываем количество ставок
    bot.reply_to(message, "История ставок: пока не реализована")

# Обработчик для отображения информации о текущем состоянии игры
@bot.message_handler(commands=['game_info'])
def show_game_info(message):
    chat_id = message.chat.id
    
    if chat_id not in games:
        bot.reply_to(message, "Нет активной игры.")
        return
        
    game = games[chat_id]
    
    info_text = "Информация о текущей игре:\n\n"
    info_text += f"Чат ID: {chat_id}\n"
    info_text += f"Активна: {'Да' if game.is_active else 'Нет'}\n"
    info_text += f"Количество игроков: {len(game.players)}\n"
    info_text += f"Текущий результат: {game.wheel_result if game.wheel_result is not None else 'Не сыграно'}\n\n"
    
    info_text += "Игроки:\n"
    for player_id, player_data in game.players.items():
        info_text += f"- @{player_data['username']} (баланс: {player_data['balance']})\n"
        
    bot.reply_to(message, info_text)


# Добавим команду для выхода из игры
@bot.message_handler(commands=['leave'])
def leave_game(message):
    chat_id = message.chat.id
    
    if chat_id not in games or game_states[chat_id] != "active":
        bot.reply_to(message, "Нет активной игры или игра уже началась.")
        return
        
    user_id = message.from_user.id
    game = games[chat_id]
    
    if user_id not in game.players:
        bot.reply_to(message, "Вы не участвуете в этой игре.")
        return
        
    # Удаляем игрока из игры
    game.remove_player(user_id)
    game.players[user_id]["is_active"] = False
    
    bot.reply_to(message, "Вы успешно покинули игру.")

# Добавим команду для проверки, сделали ли все игроки ставки
@bot.message_handler(commands=['check_bets'])
def check_all_bets(message):
    chat_id = message.chat.id
    
    if chat_id not in games or game_states[chat_id] != "active":
        bot.reply_to(message, "Нет активной игры.")
        return
        
    game = games[chat_id]
    
    # Проверяем, сделали ли все игроки ставки
    all_bets_made = game.check_all_players_bets()
    
    if all_bets_made:
        bot.reply_to(message, "Все игроки уже сделали ставки.")
    else:
        not_bets_players = []
        for user_id, player in game.players.items():
            if player["is_active"] and game.bet_count[user_id] == 0:
                not_bets_players.append(player["username"])
        
        bot.reply_to(message, 
            f"Есть игроки, которые еще не сделали ставки:\n"
            + "\n".join([f"@{player}" for player in not_bets_players]))

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "🤖 Помощь по рулетке с негативными эмоциями\n\n"
        "Доступные команды:\n"
        "/start - Приветствие и правила игры\n"
        "/newgame - Создать новую игру\n"
        "/join - Присоединиться к существующей игре\n"
        "/begingame - Начать активную игру\n"
        "/endgame - Завершить текущую игру\n"
        "/bet_number <количество> <номер> - Ставка на число (0-32)\n"
        "/bet_emotion <количество> <эмоция> - Ставка на негативную эмоцию\n"
        "/bet_dual <количество числа> <количество эмоции> <номер> <эмоция> - Ставка на число и эмоцию одновременно\n"
        "/spin - Крутить колесо рулетки и показать результаты\n"
        "/history - Показать историю ставок в текущей игре\n"
        "/balance - Показать ваш баланс\n"
        "/leave - Покинуть игру (после начала)\n"
        "/emotions - Показать все доступные эмоции\n"
        "/emotion_info <эмоция> - Информация о конкретной эмоции\n"
        "/rules - Правила игры\n"
        "/status - Статус игры\n"
        "/player_info - Информация о вашем профиле\n"
        "/game_info - Информация о текущей игре\n"
        "/help - Показать эту справку\n\n"
       
    )
    
    bot.reply_to(message, help_text)

# Обработчик для неправильного формата команды
@bot.message_handler(func=lambda message: True)
def handle_unknown_command(message):
    if message.text.startswith('/'):
        bot.reply_to(message, "Неизвестная команда. Используйте /help для получения справки.")

if __name__ == "__main__":
    print("Бот запущен...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка: {e}")

       
