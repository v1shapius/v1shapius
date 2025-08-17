# Russian localization file

MATCH_CREATION = {
    "title": "🎮 Новый матч создан",
    "description": "Создан новый матч!",
    "player1": "Игрок 1",
    "player2": "Игрок 2",
    "format": "Формат",
    "status": "Статус",
    "created_at": "Создан в",
    "join_match": "Присоединиться к матчу",
    "waiting_players": "Ожидание присоединения игроков...",
    "both_players_joined": "Оба игрока присоединились!",
    "voice_channel_created": "Голосовой канал создан: {channel_name}"
}

MATCH_STAGES = {
    "waiting_readiness": "⏳ Ожидание подтверждения готовности игроков",
    "waiting_draft": "📋 Ожидание подтверждения драфта",
    "waiting_first_player": "🎯 Ожидание выбора первого игрока",
    "preparing_game": "🎮 Подготовка к игре",
    "game_in_progress": "🏃 Игра в процессе",
    "waiting_confirmation": "✅ Ожидание подтверждения результатов",
    "match_complete": "🏁 Матч завершен"
}

DRAFT_VERIFICATION = {
    "title": "📋 Подтверждение драфта",
    "description": "Пожалуйста, предоставьте ссылку на драфт",
    "placeholder": "Введите ссылку на драфт здесь",
    "submit": "Отправить драфт",
    "waiting_both": "Ожидание отправки ссылок на драфт от обоих игроков...",
    "links_match": "✅ Ссылки на драфт совпадают! Драфт подтвержден.",
    "links_dont_match": "❌ Ссылки на драфт не совпадают. Пожалуйста, согласуйте и попробуйте снова.",
    "draft_confirmed": "Драфт успешно подтвержден!"
}

FIRST_PLAYER_SELECTION = {
    "title": "🎯 Кто играет первым?",
    "description": "Пожалуйста, выберите, кто будет играть первым",
    "player1_first": "Игрок 1 играет первым",
    "player2_first": "Игрок 2 играет первым",
    "waiting_choices": "Ожидание выбора от обоих игроков...",
    "choices_match": "✅ Оба игрока выбрали одинаковый вариант!",
    "choices_dont_match": "❌ Игроки сделали разные выборы. Пожалуйста, согласуйте и попробуйте снова.",
    "first_player_selected": "Первый игрок выбран: {player_name}"
}

GAME_PREPARATION = {
    "title": "🎮 Подготовка к игре",
    "first_player_instructions": "Пожалуйста, выключите трансляцию и нажмите готов, когда будете готовы",
    "second_player_instructions": "Пожалуйста, подтвердите, что все соответствует драфту и вы наблюдаете за трансляцией",
    "ready_button": "Я готов",
    "confirm_draft_button": "Подтвердить драфт и трансляцию",
    "waiting_first_player": "Ожидание готовности первого игрока...",
    "waiting_second_player": "Ожидание подтверждения от второго игрока...",
    "both_ready": "✅ Оба игрока готовы! Игра может начаться.",
    "stream_check_failed": "❌ Трансляция все еще активна. Пожалуйста, выключите ее и попробуйте снова."
}

GAME_RESULTS = {
    "title": "⏱️ Результаты игры",
    "description": "Пожалуйста, введите время прохождения и количество рестартов",
    "time_label": "Время прохождения (ММ:СС)",
    "time_placeholder": "05:30",
    "restarts_label": "Количество рестартов",
    "restarts_placeholder": "2",
    "submit_results": "Отправить результаты",
    "waiting_confirmation": "Ожидание подтверждения результатов от соперника...",
    "results_confirmed": "✅ Результаты подтверждены обоими игроками!",
    "results_disputed": "❌ Результаты оспорены. Пожалуйста, решите проблему."
}

MATCH_COMPLETION = {
    "title": "🏁 Результаты матча",
    "description": "Финальные результаты матча",
    "game_results": "Результаты игр",
    "total_time": "Общее время",
    "restarts": "Рестарты",
    "penalties": "Штрафы",
    "final_time": "Финальное время",
    "winner": "Победитель",
    "confirm_results": "Подтвердить результаты",
    "results_confirmed": "✅ Результаты матча подтверждены!",
    "match_archived": "Матч успешно архивирован.",
    "voice_channel_deletion": "Голосовой канал будет удален через 5 минут."
}

RATING_SYSTEM = {
    "title": "📊 Обновление рейтинга",
    "description": "Изменения рейтинга после матча",
    "old_rating": "Старый рейтинг",
    "new_rating": "Новый рейтинг",
    "change": "Изменение",
    "rating_increased": "Рейтинг увеличен на {points}",
    "rating_decreased": "Рейтинг уменьшен на {points}",
    "rating_unchanged": "Рейтинг не изменился"
}

ERRORS = {
    "player_not_in_voice": "❌ Игрок {player_name} не находится в голосовом канале",
    "stream_active": "❌ Трансляция все еще активна. Пожалуйста, выключите ее сначала.",
    "invalid_time_format": "❌ Неверный формат времени. Используйте ММ:СС",
    "invalid_restart_count": "❌ Неверное количество рестартов. Должно быть положительным числом.",
    "match_not_found": "❌ Матч не найден",
    "insufficient_permissions": "❌ Недостаточно прав",
    "already_in_match": "❌ Вы уже участвуете в матче",
    "voice_channel_full": "❌ Голосовой канал переполнен"
}

SUCCESS = {
    "match_created": "✅ Матч успешно создан!",
    "player_joined": "✅ Игрок присоединился к матчу!",
    "readiness_confirmed": "✅ Готовность подтверждена!",
    "draft_confirmed": "✅ Драфт подтвержден!",
    "first_player_set": "✅ Первый игрок установлен!",
    "game_started": "✅ Игра началась!",
    "results_submitted": "✅ Результаты отправлены!",
    "match_completed": "✅ Матч успешно завершен!"
}

BUTTONS = {
    "confirm": "Подтвердить",
    "cancel": "Отмена",
    "ready": "Готов",
    "submit": "Отправить",
    "dispute": "Оспорить",
    "join": "Присоединиться",
    "leave": "Покинуть"
}

FORMATS = {
    "bo1": "Лучший из 1",
    "bo2": "Лучший из 2",
    "bo3": "Лучший из 3"
}

STATUSES = {
    "waiting": "Ожидание",
    "active": "Активен",
    "completed": "Завершен",
    "cancelled": "Отменен"
}